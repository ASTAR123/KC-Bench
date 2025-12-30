"""Task Score evaluation utilities with LLM-based judging.

This module provides a configurable evaluator that estimates task completion
rates for agent outputs. It supports both tasks with explicit ground truth
labels and open-ended instructions that require qualitative judgement. A
separate judge model is used to avoid brittle string comparisons with the
ground truth labels.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import yaml
try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - openai optional in rule mode
    OpenAI = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

try:  # Optional progress bar support
    from tqdm.auto import tqdm as _tqdm
except ImportError:  # pragma: no cover - tqdm optional
    _tqdm = None


DEFAULT_SYSTEM_PROMPT = (
    "You are an impartial judge. Decide whether the assistant's output fully "
    "solves the user instruction. Always reply with strict JSON so it can be "
    "parsed programmatically."
)

DEFAULT_EVAL_PROMPT_WITH_LABEL = """
You will be given a task instruction, the assistant's output, and one or more reference answers.
Decide if the output matches at least one reference exactly in meaning and required detail.
Respond with JSON: {{"score": 1 or 0, "explanation": "short reason"}}. Only output score=1 when the answer is fully correct.

Instruction:
  {instruction}

Reference answers:
  {lable}

Assistant output:
  {response}
""".strip()

DEFAULT_EVAL_PROMPT_WITHOUT_LABEL = """
You will be given a task instruction and the assistant's output.
Decide if the response satisfies the instruction without introducing unsupported claims.
Respond with JSON: {{"score": 1 or 0, "explanation": "short reason"}}. Use score=1 only when the answer is complete and correct.

Instruction:
  {instruction}

Assistant output:
  {response}
""".strip()

DEFAULT_PROMPT_TEMPLATE_DIR = Path("Evaluation/prompt_templates")


def _coerce_to_text(value: Any) -> str:
    """Best-effort conversion of any result/label into human-readable text."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _escape_braces(text: str) -> str:
    """Escape braces for safe usage in str.format templates."""

    return text.replace("{", "{{").replace("}", "}}")


def _extract_assistant_content(response: Any) -> Optional[str]:
    """Extract assistant message content from various client responses."""

    if response is None:
        return None

    if isinstance(response, str):
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError:
            return response
        return _extract_assistant_content(parsed)

    if isinstance(response, dict):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if not choices and isinstance(response, dict):
        # Some servers may respond with {'message': {...}}
        message = response.get("message")
        if isinstance(message, dict):
            return message.get("content")
        if isinstance(message, str):
            return message
        return None

    if isinstance(choices, dict):  # Occasionally a mapping keyed by index
        choices = list(choices.values())

    if not isinstance(choices, Sequence) or not choices:
        return None

    first_choice = choices[0]

    if isinstance(first_choice, dict):
        message = first_choice.get("message")
        if isinstance(message, dict):
            return message.get("content") or message.get("text")
        if isinstance(message, str):
            return message
        text = first_choice.get("text")
        if isinstance(text, str):
            return text
        return None

    message_obj = getattr(first_choice, "message", None)
    if message_obj is not None:
        content = getattr(message_obj, "content", None)
        if content is not None:
            return content
        if isinstance(message_obj, dict):
            return message_obj.get("content")

    text_attr = getattr(first_choice, "text", None)
    if isinstance(text_attr, str):
        return text_attr

    return None


def _format_reference(label: Any) -> str:
    """Format label(s) into a readable bullet list string."""

    if label is None:
        return ""
    if isinstance(label, (list, tuple, set)):
        items = [_coerce_to_text(item).strip() for item in label if item is not None]
        items = [item for item in items if item]
        if not items:
            return ""
        return "\n".join(f"- {item}" for item in items)
    text = _coerce_to_text(label).strip()
    if not text:
        return ""
    return f"- {text}"


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object found in the text."""

    text = text.strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    extracted = match.group(0)
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        return None


def _normalize_score(value: Any) -> float:
    """Convert judge output score into a float within [0, 1]."""

    if isinstance(value, (int, float)):
        if value <= 0:
            return 0.0
        if value >= 1:
            return 1.0
        return float(value)

    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "pass", "correct", "yes", "y"}:
            return 1.0
        if lowered in {"0", "false", "fail", "incorrect", "no", "n"}:
            return 0.0
        try:
            numeric = float(lowered)
        except ValueError:
            return 0.0
        if numeric <= 0:
            return 0.0
        if numeric >= 1:
            return 1.0
        return numeric

    return 0.0


def _task_id_to_key(task_id: Any) -> Optional[str]:
    """Normalize task identifiers to string keys."""

    if task_id is None:
        return None
    return str(task_id)


SQL_PREFIXES = ("select", "insert", "update", "delete", "with", "create", "drop", "alter")


def _is_sql_statement(text: str) -> bool:
    """Heuristic check whether a label looks like a SQL statement."""

    if not text:
        return False
    stripped = text.strip().lower()
    return any(stripped.startswith(prefix) for prefix in SQL_PREFIXES)


_NUMERIC_LITERAL_RE = re.compile(r"(['\"])(\d[\d,._]*)\1")
_TEXTUAL_DATE_RE = re.compile(
    r"'([a-zA-Z]+(?:\s+[0-9]{1,2})(?:,\s*|\s+)[0-9]{4})'"
)
_MONTH_TO_NUM = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def _normalize_sql_query(query: Optional[str]) -> Optional[str]:
    """Normalize SQL by collapsing whitespace and handling trivial formatting differences."""

    if not query:
        return None

    text = query.strip().lower()
    if not text:
        return None

    text = text.rstrip(";")
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.replace("`", "")

    def _numeric_repl(match: re.Match[str]) -> str:
        digits = match.group(2).replace(",", "")
        return digits

    text = _NUMERIC_LITERAL_RE.sub(_numeric_repl, text)
    text = re.sub(r"(\d),(?=\d{3})", r"\1", text)

    def _date_repl(match: re.Match[str]) -> str:
        raw = match.group(1).replace(",", " ")
        parts = raw.split()
        if len(parts) != 3:
            return f"'{raw.strip()}'"
        month_name, day_str, year_str = parts
        month_num = _MONTH_TO_NUM.get(month_name.lower())
        if not month_num:
            return f"'{raw.strip()}'"
        try:
            day = int(day_str)
            year = int(year_str)
        except ValueError:
            return f"'{raw.strip()}'"
        normalized = f"{year:04d}-{int(month_num):02d}-{day:02d}"
        return f"'{normalized}'"

    text = _TEXTUAL_DATE_RE.sub(_date_repl, text)

    text = re.sub(r"\s*,\s*", ",", text)
    text = re.sub(r"\s*\(\s*", "(", text)
    text = re.sub(r"\s*\)\s*", ")", text)
    text = re.sub(r"\s*=\s*", "=", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("( ", "(").replace(" )", ")")
    text = text.replace(" ,", ",")

    return text.strip()


def _coerce_prompt_dict(data: Any) -> Dict[str, str]:
    """Convert any mapping into a flat prompt dictionary."""

    if not isinstance(data, dict):
        return {}

    prompts: Dict[str, str] = {}
    for key, value in data.items():
        if value is None:
            continue
        prompts[str(key)] = str(value)
    return prompts


def _load_prompt_template_file(path: Path) -> Dict[str, str]:
    """Load a YAML/JSON template file that defines prompt segments."""

    path = path.expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path

    if not path.exists():
        raise FileNotFoundError(f"Prompt template file not found: {path}")

    with path.open("r", encoding="utf-8") as template_file:
        data = yaml.safe_load(template_file) or {}

    prompts = _coerce_prompt_dict(data)
    if not prompts:
        raise ValueError(f"Prompt template file {path} did not contain any prompts.")

    system_prompt = prompts.get("system")
    evaluate_prompt = prompts.get("evaluate") or prompts.get("prompt") or prompts.get("user")

    if system_prompt is None and evaluate_prompt is None:
        raise ValueError(
            f"Prompt template file {path} must define at least 'system' or 'evaluate' fields."
        )

    result: Dict[str, str] = {}
    if system_prompt is not None:
        result["system"] = system_prompt
    if evaluate_prompt is not None:
        result["evaluate"] = evaluate_prompt
    return result


def _ensure_template_path(reference: str, template_dir: Path) -> Path:
    """Resolve a template reference to an absolute path."""

    candidate = Path(reference).expanduser()
    if candidate.is_absolute():
        return candidate

    reference_str = str(reference)
    has_directory_hint = any(sep in reference_str for sep in ("/", "\\"))

    if has_directory_hint:
        # Treat as repo-relative path instead of template_dir-relative.
        return (Path.cwd() / candidate).resolve()

    if candidate.suffix:
        return (template_dir / candidate).resolve()

    return (template_dir / f"{reference_str}.yaml").resolve()


def _apply_prompt_spec(base: "PromptTemplate", spec: Any, template_dir: Path) -> "PromptTemplate":
    """Create a new prompt template by applying a specification on top of a base template."""

    if spec is None:
        return base

    template_data: Dict[str, str] = {}

    if isinstance(spec, str):
        template_data = _load_prompt_template_file(_ensure_template_path(spec, template_dir))
    elif isinstance(spec, dict):
        reference = spec.get("template_path") or spec.get("path") or spec.get("file")
        name = spec.get("template_name") or spec.get("template")
        if name and not reference:
            reference = name
        if reference:
            template_data.update(_load_prompt_template_file(_ensure_template_path(str(reference), template_dir)))

        for key in ("system", "evaluate", "prompt", "user"):
            value = spec.get(key)
            if value is None:
                continue
            mapped_key = "evaluate" if key in {"prompt", "user"} else key
            template_data[mapped_key] = str(value)
    else:
        raise ValueError("Prompt specification must be a string or mapping.")

    if not template_data:
        return base

    system_value = template_data.get("system")
    evaluate_value = template_data.get("evaluate")
    return base.replace(system=system_value, evaluate=evaluate_value)


def _extract_general_prompt_spec(prompts_block: Dict[str, Any]) -> Optional[Any]:
    """Extract a shared prompt spec applied before mode-specific overrides."""

    general_keys = ("template_path", "path", "file", "system", "evaluate", "prompt", "user")
    collected: Dict[str, Any] = {}
    for key in general_keys:
        value = prompts_block.get(key)
        if value is not None:
            collected[key] = value
    return collected or None


def _apply_legacy_prompt_block(
    prompt_sets: Dict[str, "PromptTemplate"],
    block: Any,
) -> Dict[str, "PromptTemplate"]:
    """Translate legacy judge_prompt/eval_prompt formats into the new template schema."""

    if isinstance(block, str):
        for key, template in prompt_sets.items():
            prompt_sets[key] = template.replace(evaluate=block)
        return prompt_sets

    if not isinstance(block, dict):
        return prompt_sets

    system_override = block.get("system")
    if system_override:
        for key, template in prompt_sets.items():
            prompt_sets[key] = template.replace(system=system_override)

    with_label_override = block.get("with_label") or block.get("evaluate_with_label")
    without_label_override = block.get("without_label") or block.get("evaluate_without_label")
    evaluate_override = block.get("evaluate") or block.get("prompt") or block.get("user")

    if with_label_override:
        prompt_sets["with_label"] = prompt_sets["with_label"].replace(evaluate=with_label_override)
    if without_label_override:
        prompt_sets["without_label"] = prompt_sets["without_label"].replace(evaluate=without_label_override)

    if evaluate_override and not (with_label_override or without_label_override):
        for key, template in prompt_sets.items():
            prompt_sets[key] = template.replace(evaluate=evaluate_override)

    return prompt_sets


def _normalize_aggregation_mode(value: Optional[str]) -> str:
    """Normalize configuration values for task score aggregation."""

    if not value:
        return "average"

    normalized = str(value).strip().lower()
    if normalized in {"average", "avg", "mean"}:
        return "average"
    if normalized in {"sum", "total", "score", "points"}:
        return "sum"
    raise ValueError(
        f"Unsupported score aggregation mode '{value}'. "
        "Use 'average' or 'sum'."
    )


def _normalize_evaluation_mode(value: Optional[str]) -> str:
    """Normalize evaluation mode selection."""

    if not value:
        return "model"

    normalized = str(value).strip().lower()
    if normalized in {"model", "llm", "judge", "ai"}:
        return "model"
    if normalized in {"rule", "rules", "matching", "exact"}:
        return "rule"
    raise ValueError("Evaluation.mode must be either 'model' or 'rule'.")


def _coerce_label_list(label: Any) -> List[str]:
    """Convert a raw label field into a flat list of unique string labels."""

    def _flatten(value: Any) -> Iterable[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        if isinstance(value, (list, tuple, set)):
            items: List[str] = []
            for item in value:
                items.extend(_flatten(item))
            return items
        coerced = _coerce_to_text(value).strip()
        return [coerced] if coerced else []

    seen = set()
    ordered: List[str] = []
    for candidate in _flatten(label):
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(candidate)
    return ordered


def _load_named_prompt_pair(
    template_name: str,
    template_dir: Path,
) -> Dict[str, Dict[str, str]]:
    """Load two prompt files following the with_label/without_label naming convention."""

    template_name = template_name.strip()
    if not template_name:
        raise ValueError("Template name cannot be empty when specified.")

    results: Dict[str, Dict[str, str]] = {}
    for mode in ("with_label", "without_label"):
        filename = f"{mode}_{template_name}.yaml"
        template_path = (template_dir / filename).resolve()
        if not template_path.exists():
            raise FileNotFoundError(f"Prompt template file not found for mode '{mode}': {template_path}")
        results[mode] = _load_prompt_template_file(template_path)

    return results


def _resolve_prompts_from_config(evaluation_config: Dict[str, Any]) -> Dict[str, "PromptTemplate"]:
    """Resolve prompt configuration into concrete templates for each evaluation mode."""

    prompt_sets = {
        "with_label": PromptTemplate(DEFAULT_SYSTEM_PROMPT, DEFAULT_EVAL_PROMPT_WITH_LABEL),
        "without_label": PromptTemplate(DEFAULT_SYSTEM_PROMPT, DEFAULT_EVAL_PROMPT_WITHOUT_LABEL),
    }

    legacy_block = evaluation_config.get("judge_prompt") or evaluation_config.get("eval_prompt")
    if legacy_block:
        prompt_sets = _apply_legacy_prompt_block(prompt_sets, legacy_block)

    prompts_block = evaluation_config.get("prompts")
    if prompts_block is None:
        return prompt_sets

    if isinstance(prompts_block, str):
        stripped = prompts_block.strip()
        if stripped.endswith((".yaml", ".yml")) or "/" in stripped or "\\" in stripped:
            prompts_block = {"template_path": stripped}
        else:
            prompts_block = {"template_name": stripped}
    if not isinstance(prompts_block, dict):
        raise ValueError("Evaluation.prompts must be a mapping or string (template name).")

    template_dir = Path(prompts_block.get("template_dir") or DEFAULT_PROMPT_TEMPLATE_DIR).expanduser()

    template_name = prompts_block.get("template_name") or prompts_block.get("template")
    if template_name:
        named_templates = _load_named_prompt_pair(str(template_name), template_dir)
        for mode, template_data in named_templates.items():
            prompt_sets[mode] = prompt_sets[mode].replace(
                system=template_data.get("system"),
                evaluate=template_data.get("evaluate"),
            )

    general_spec = _extract_general_prompt_spec(prompts_block)
    if general_spec:
        for key in prompt_sets:
            prompt_sets[key] = _apply_prompt_spec(prompt_sets[key], general_spec, template_dir)

    if "with_label" in prompts_block:
        prompt_sets["with_label"] = _apply_prompt_spec(
            prompt_sets["with_label"],
            prompts_block["with_label"],
            template_dir,
        )
    if "without_label" in prompts_block:
        prompt_sets["without_label"] = _apply_prompt_spec(
            prompt_sets["without_label"],
            prompts_block["without_label"],
            template_dir,
        )

    return prompt_sets


@dataclass
class PromptTemplate:
    """Pair of system and user prompts used for judging."""

    system: str
    evaluate: str

    def replace(
        self,
        *,
        system: Optional[str] = None,
        evaluate: Optional[str] = None,
    ) -> "PromptTemplate":
        return PromptTemplate(
            system=system if system is not None else self.system,
            evaluate=evaluate if evaluate is not None else self.evaluate,
        )


@dataclass
class TaskLogEntry:
    """Parsed representation of a single task log."""

    summary: str
    executed_sql: List[str]
    final_answer: Optional[str]
    raw: Dict[str, Any]


@dataclass
class JudgeModelConfig:
    """Configuration for the LLM judge used during evaluation."""

    model_id: str
    api_key: str
    api_base: Optional[str] = None
    organization: Optional[str] = None
    project: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 512

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JudgeModelConfig":
        if not data:
            raise ValueError("Judge model configuration is missing.")

        model_id = data.get("model_id")
        if not model_id:
            raise ValueError("Judge model configuration must include 'model_id'.")

        api_key = data.get("api_key")
        if not api_key:
            env_var = data.get("api_key_env")
            if env_var:
                api_key = os.getenv(env_var)
            if not api_key:
                api_key = os.getenv("EVAL_JUDGE_API_KEY")
        if not api_key:
            raise ValueError("Judge model API key is missing. Provide 'api_key' or set EVAL_JUDGE_API_KEY.")

        api_base = data.get("api_base") or data.get("base_url")
        organization = data.get("organization")
        project = data.get("project")
        temperature = float(data.get("temperature", 0.0))
        max_tokens = int(data.get("max_tokens") or data.get("max_output_tokens") or 512)

        return cls(
            model_id=model_id,
            api_key=api_key,
            api_base=api_base,
            organization=organization,
            project=project,
            temperature=temperature,
            max_tokens=max_tokens,
        )


class TaskScoreEvaluator:
    """Judge-based evaluator that computes task completion rates."""

    def __init__(
        self,
        judge_config: Optional[JudgeModelConfig],
        *,
        prompts: Optional[Dict[str, PromptTemplate]] = None,
        success_threshold: float = 0.5,
        max_retries: int = 3,
        score_aggregation: str = "average",
        evaluation_mode: str = "model",
        task_logs: Optional[Dict[Any, TaskLogEntry]] = None,
    ) -> None:
        self.judge_config = judge_config
        self.success_threshold = success_threshold
        self.max_retries = max_retries
        self.score_aggregation = score_aggregation
        self.evaluation_mode = evaluation_mode
        self._judge_temperature = 0.0  # enforce deterministic evaluation
        self._client: Optional[OpenAI] = None
        self.task_logs: Dict[Optional[str], TaskLogEntry] = {}
        if task_logs:
            for key, entry in task_logs.items():
                normalized_key = _task_id_to_key(key)
                self.task_logs[normalized_key] = entry

        prompt_sets = prompts or {}
        self.prompts_with_label = prompt_sets.get("with_label") or PromptTemplate(
            DEFAULT_SYSTEM_PROMPT,
            DEFAULT_EVAL_PROMPT_WITH_LABEL,
        )
        self.prompts_without_label = prompt_sets.get("without_label") or PromptTemplate(
            DEFAULT_SYSTEM_PROMPT,
            DEFAULT_EVAL_PROMPT_WITHOUT_LABEL,
        )

        if self.evaluation_mode == "model":
            if self.judge_config is None:
                raise ValueError("Judge model configuration is required when evaluation.mode='model'.")
            if OpenAI is None:
                raise ImportError("openai package is required for evaluation.mode='model'.")
            self.judge_config.temperature = 0.0

            client_kwargs: Dict[str, Any] = {"api_key": self.judge_config.api_key}
            if self.judge_config.api_base:
                client_kwargs["base_url"] = self.judge_config.api_base
            if self.judge_config.organization:
                client_kwargs["organization"] = self.judge_config.organization
            if self.judge_config.project:
                client_kwargs["project"] = self.judge_config.project

            self._client = OpenAI(**client_kwargs)

    @classmethod
    def from_config(
        cls,
        evaluation_config: Dict[str, Any],
        *,
        task_logs: Optional[Dict[Any, TaskLogEntry]] = None,
    ) -> "TaskScoreEvaluator":
        if not evaluation_config:
            raise ValueError("Evaluation configuration is missing.")

        evaluation_mode = _normalize_evaluation_mode(
            evaluation_config.get("mode")
            or evaluation_config.get("evaluator")
            or evaluation_config.get("judge_type")
        )

        judge_config: Optional[JudgeModelConfig] = None
        prompts: Optional[Dict[str, PromptTemplate]] = None

        if evaluation_mode == "model":
            judge_config_block = (
                evaluation_config.get("judge_model")
                or evaluation_config.get("eval_model")
            )
            judge_config = JudgeModelConfig.from_dict(judge_config_block)
            prompts = _resolve_prompts_from_config(evaluation_config)

        success_threshold = float(evaluation_config.get("success_threshold", 0.5))
        max_retries = int(evaluation_config.get("max_retries", 3))
        score_aggregation = _normalize_aggregation_mode(
            evaluation_config.get("score_aggregation")
            or evaluation_config.get("score_mode")
            or evaluation_config.get("aggregation")
        )

        return cls(
            judge_config,
            prompts=prompts,
            success_threshold=success_threshold,
            max_retries=max_retries,
            score_aggregation=score_aggregation,
            evaluation_mode=evaluation_mode,
            task_logs=task_logs,
        )

    def _build_messages(
        self,
        task_id: Any,
        instruction: str,
        output: str,
        reference: Optional[str],
    ) -> List[Dict[str, str]]:
        prompt_template = self.prompts_with_label if reference else self.prompts_without_label
        reference_text = (reference or "N/A").strip()
        output_text = output.strip() or "[empty output]"
        instruction_text = instruction.strip()
        log_summary = self._get_log_summary(task_id)

        format_values = {
            "instruction": _escape_braces(instruction_text),
            "lable": _escape_braces(reference_text),
            "label": _escape_braces(reference_text),
            "reference": _escape_braces(reference_text),
            "response": _escape_braces(output_text),
            "output": _escape_braces(output_text),
            "assistant_output": _escape_braces(output_text),
            "log": _escape_braces(log_summary or "N/A"),
        }

        user_content = prompt_template.evaluate.format(**format_values)

        return [
            {"role": "system", "content": prompt_template.system},
            {"role": "user", "content": user_content},
        ]

    def _get_log_entry(self, task_id: Any) -> Optional[TaskLogEntry]:
        key = _task_id_to_key(task_id)
        if key is None:
            return None
        return self.task_logs.get(key)

    def _get_log_summary(self, task_id: Any) -> str:
        entry = self._get_log_entry(task_id)
        if not entry:
            return ""
        return entry.summary

    def _evaluate_with_model(
        self,
        task_id: Any,
        instruction: str,
        output_text: str,
        reference_text: str,
    ) -> Dict[str, Any]:
        messages = self._build_messages(task_id, instruction, output_text, reference_text)
        judge_payload, raw_content = self._call_judge(messages)

        if judge_payload is None:
            explanation = "Judge model could not provide a valid evaluation."
            return {
                "task_id": task_id,
                "score": 0.0,
                "passed": False,
                "explanation": explanation,
                "raw_judge": raw_content or None,
            }

        score_value = _normalize_score(judge_payload.get("score"))
        explanation = _coerce_to_text(
            judge_payload.get("explanation")
            or judge_payload.get("reason")
            or judge_payload.get("analysis")
        ).strip()

        passed = score_value >= self.success_threshold

        return {
            "task_id": task_id,
            "score": score_value,
            "passed": passed,
            "explanation": explanation or None,
            "raw_judge": raw_content or None,
        }

    def _evaluate_with_rules(
        self,
        task_id: Any,
        output_text: str,
        labels: List[str],
        log_entry: Optional[TaskLogEntry],
    ) -> Dict[str, Any]:
        if not labels:
            explanation = "No reference labels; rule-based evaluation skipped."
            return {
                "task_id": task_id,
                "score": 0.0,
                "passed": False,
                "explanation": explanation,
                "matched_labels": [],
                "missing_labels": [],
            }

        sql_labels = [label for label in labels if _is_sql_statement(label)]
        if sql_labels:
            return self._evaluate_sql_labels(task_id, sql_labels, log_entry)

        normalized_output = output_text.lower()
        matched: List[str] = []
        missing: List[str] = []
        for label in labels:
            if label.lower() in normalized_output:
                matched.append(label)
            else:
                missing.append(label)

        score_value = len(matched) / len(labels)
        passed = score_value >= self.success_threshold
        explanation = f"Matched {len(matched)}/{len(labels)} labels."

        return {
            "task_id": task_id,
            "score": score_value,
            "passed": passed,
            "explanation": explanation,
            "matched_labels": matched,
            "missing_labels": missing,
        }

    def _evaluate_sql_labels(
        self,
        task_id: Any,
        sql_labels: List[str],
        log_entry: Optional[TaskLogEntry],
    ) -> Dict[str, Any]:
        if log_entry is None:
            explanation = "SQL labels present but no logs available for verification."
            return {
                "task_id": task_id,
                "score": 0.0,
                "passed": False,
                "explanation": explanation,
                "matched_labels": [],
                "missing_labels": sql_labels,
            }

        executed_sql = log_entry.executed_sql or []
        normalized_exec = {
            normalized
            for normalized in (_normalize_sql_query(sql) for sql in executed_sql)
            if normalized
        }

        matched: List[str] = []
        missing: List[str] = []
        for label in sql_labels:
            normalized_label = _normalize_sql_query(label)
            if normalized_label and normalized_label in normalized_exec:
                matched.append(label)
            else:
                missing.append(label)

        total_labels = len(sql_labels) or 1
        score_value = len(matched) / total_labels
        passed = score_value >= self.success_threshold
        explanation = f"SQL matched {len(matched)}/{total_labels} statements."

        return {
            "task_id": task_id,
            "score": score_value,
            "passed": passed,
            "explanation": explanation,
            "matched_labels": matched,
            "missing_labels": missing,
            "executed_sql": executed_sql,
        }

    def _call_judge(self, messages: List[Dict[str, str]]) -> Tuple[Optional[Dict[str, Any]], str]:
        if self._client is None:
            raise RuntimeError("Judge client is not initialized for model-based evaluation.")
        last_exception: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.judge_config.model_id,
                    messages=messages,
                    temperature=self._judge_temperature,
                    max_tokens=self.judge_config.max_tokens,
                )
                content = _extract_assistant_content(response)
                if content is None:
                    logger.warning(
                        "Judge model response missing content on attempt %s: %s",
                        attempt,
                        response,
                    )
                    continue
                content = content.strip()
                parsed = _extract_json_object(content)
                if parsed is not None and "score" in parsed:
                    return parsed, content

                logger.warning(
                    "Judge model returned unparsable content on attempt %s: %s",
                    attempt,
                    content,
                )
            except Exception as exc:  # noqa: BLE001 - propagate information in logs
                last_exception = exc
                logger.warning("Judge model call failed on attempt %s: %s", attempt, exc)

        if last_exception:
            logger.error("Judge model failed after %s attempts: %s", self.max_retries, last_exception)
        return None, ""

    def evaluate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        task_block = record.get("task", {}) if isinstance(record, dict) else {}
        instruction = _coerce_to_text(
            record.get("instruction") or task_block.get("instruction")
        ).strip()
        output_text = _coerce_to_text(record.get("result")).strip()
        label_source = record.get("label") if "label" in record else task_block.get("label")
        reference_text = _format_reference(label_source)
        label_list = _coerce_label_list(label_source)

        task_id = record.get("task_id") or task_block.get("task_id")
        log_entry = self._get_log_entry(task_id)

        if not instruction:
            explanation = "Missing instruction; cannot evaluate."
            return {
                "task_id": task_id,
                "score": 0.0,
                "passed": False,
                "explanation": explanation,
                "raw_judge": None,
            }

        if not output_text:
            explanation = "Assistant produced no output."
            return {
                "task_id": task_id,
                "score": 0.0,
                "passed": False,
                "explanation": explanation,
                "raw_judge": None,
            }

        if self.evaluation_mode == "rule":
            return self._evaluate_with_rules(
                task_id=task_id,
                output_text=output_text,
                labels=label_list,
                log_entry=log_entry,
            )

        return self._evaluate_with_model(
            task_id=task_id,
            instruction=instruction,
            output_text=output_text,
            reference_text=reference_text,
        )

    def evaluate_records(
        self,
        records: Sequence[Dict[str, Any]] | Iterable[Dict[str, Any]],
        *,
        show_progress: bool = False,
        progress_desc: str | None = None,
    ) -> Dict[str, Any]:
        details: List[Dict[str, Any]] = []
        success_count = 0
        total_score = 0.0

        iterable: Iterable[Dict[str, Any]]
        total = len(records) if isinstance(records, Sequence) else None
        if show_progress and _tqdm is not None:
            iterable = _tqdm(records, desc=progress_desc or "Evaluating", unit="task", total=total)
        else:
            iterable = records

        for record in iterable:
            evaluation = self.evaluate_record(record)
            details.append(evaluation)
            if evaluation.get("passed"):
                success_count += 1
            try:
                total_score += float(evaluation.get("score") or 0.0)
            except (TypeError, ValueError):
                pass

        total = len(details)
        average_score = (total_score / total) if total else 0.0
        if self.score_aggregation == "sum":
            task_score_value = total_score
        else:
            task_score_value = average_score

        return {
            "metric": "Task Score",
            "aggregation": self.score_aggregation,
            "evaluation_mode": self.evaluation_mode,
            "success_count": success_count,
            "total_count": total,
            "task_score": task_score_value,
            "details": details,
        }


def _resolve_path_relative(path_value: str, base_dir: Path) -> Path:
    """Resolve a possibly-relative path against the config directory."""

    candidate = Path(path_value).expanduser()
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    return candidate


def _infer_run_identifier(results_path: Path) -> Optional[str]:
    """Extract run timestamp from the results filename."""

    match = re.search(r"results_(\d{8}_\d{6})", results_path.name)
    return match.group(1) if match else None


def _coerce_log_paths(
    logs_config: Any,
    *,
    results_path: Path,
    config_dir: Path,
) -> List[Path]:
    """Normalize log configuration into a list of absolute paths."""

    if not logs_config:
        return []

    collected: List[Path] = []

    def _add_path(path_value: str) -> None:
        if not path_value:
            return
        collected.append(_resolve_path_relative(path_value, config_dir))

    if isinstance(logs_config, str):
        _add_path(logs_config)
    elif isinstance(logs_config, Sequence) and not isinstance(logs_config, (bytes, str)):
        for item in logs_config:
            _add_path(str(item))
    elif isinstance(logs_config, dict):
        _add_path(logs_config.get("path") or logs_config.get("file"))
        for item in logs_config.get("paths") or []:
            _add_path(str(item))

        dir_value = logs_config.get("dir") or logs_config.get("directory")
        if dir_value:
            dir_path = _resolve_path_relative(dir_value, config_dir)
            if dir_path.is_dir():
                match_hint = logs_config.get("match") or logs_config.get("contains")
                if match_hint is None:
                    match_hint = _infer_run_identifier(results_path)
                glob_pattern = logs_config.get("glob")
                iterator = dir_path.glob(glob_pattern) if glob_pattern else dir_path.iterdir()
                for candidate in iterator:
                    if not candidate.is_file():
                        continue
                    if match_hint and match_hint not in candidate.name:
                        continue
                    collected.append(candidate.resolve())
            else:
                logger.warning("Configured log directory not found: %s", dir_path)
    else:
        raise ValueError("Evaluation.logs must be a string, list, or mapping.")

    # Remove duplicates while preserving order
    seen: Dict[Path, None] = {}
    for path in collected:
        try:
            resolved = path.resolve()
        except FileNotFoundError:
            resolved = path
        if resolved not in seen:
            seen[resolved] = None
    return list(seen.keys())


def _extract_sql_calls(steps: Sequence[Dict[str, Any]] | None) -> List[str]:
    """Collect all SQL strings from execute_sql tool calls."""

    if not steps:
        return []
    statements: List[str] = []
    for step in steps:
        for call in step.get("tool_calls") or []:
            function_block = call.get("function") or {}
            if function_block.get("name") != "execute_sql":
                continue
            arguments = function_block.get("arguments") or {}
            sql_text = arguments.get("sql")
            if sql_text:
                statements.append(sql_text)
    return statements


def _extract_final_answer_from_steps(steps: Sequence[Dict[str, Any]] | None) -> Optional[str]:
    """Grab the first final_answer tool call output, if any."""

    if not steps:
        return None
    for step in steps:
        for call in step.get("tool_calls") or []:
            function_block = call.get("function") or {}
            if function_block.get("name") != "final_answer":
                continue
            arguments = function_block.get("arguments")
            if isinstance(arguments, dict):
                answer_value = arguments.get("answer")
            else:
                answer_value = arguments
            if answer_value is not None:
                text = _coerce_to_text(answer_value).strip()
                if text:
                    return text
    return None


def _build_log_summary(sql_statements: Sequence[str], final_answer: Optional[str]) -> str:
    """Create a short textual summary of tool usage for prompts."""

    parts: List[str] = []
    for idx, sql in enumerate(sql_statements, start=1):
        parts.append(f"SQL#{idx}: {sql}")
        if idx >= 5:
            remaining = len(sql_statements) - idx
            if remaining > 0:
                parts.append(f"... ({remaining} more SQL calls omitted)")
            break

    if final_answer:
        parts.append(f"Final answer: {final_answer}")

    return "\n".join(parts)


def _parse_task_log_entry(raw: Dict[str, Any]) -> TaskLogEntry:
    """Convert a raw log JSON entry into a TaskLogEntry."""

    steps = raw.get("steps")
    sql_statements = _extract_sql_calls(steps)
    final_answer = _extract_final_answer_from_steps(steps)
    summary = _build_log_summary(sql_statements, final_answer)
    return TaskLogEntry(
        summary=summary,
        executed_sql=sql_statements,
        final_answer=final_answer,
        raw=raw,
    )


def _load_task_logs_from_paths(paths: Sequence[Path]) -> Dict[str, TaskLogEntry]:
    """Load log files and index them by task id."""

    task_logs: Dict[str, TaskLogEntry] = {}
    for path in paths:
        if not path.exists():
            logger.warning("Log file not found: %s", path)
            continue
        try:
            with path.open("r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, start=1):
                    stripped = line.strip()
                    if not stripped or not stripped.startswith("{"):
                        continue
                    try:
                        record = json.loads(stripped)
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed log line %s:%s", path, line_num)
                        continue
                    task_id = record.get("task_id")
                    key = _task_id_to_key(task_id)
                    if key is None:
                        continue
                    task_logs[key] = _parse_task_log_entry(record)
        except OSError as exc:
            logger.warning("Failed to read log file %s: %s", path, exc)
    return task_logs


def _load_task_logs_for_evaluation(
    evaluation_config: Dict[str, Any],
    *,
    results_path: Path,
    config_dir: Path,
    override_paths: Optional[Sequence[Path]] = None,
) -> Dict[str, TaskLogEntry]:
    """Load task logs according to Evaluation.logs config or explicit overrides."""

    if override_paths:
        return _load_task_logs_from_paths(override_paths)

    logs_config = evaluation_config.get("logs")
    if not logs_config:
        return {}

    log_paths = _coerce_log_paths(
        logs_config,
        results_path=results_path,
        config_dir=config_dir,
    )
    if not log_paths:
        logger.warning("Evaluation.logs configured but no log files were found.")
        return {}
    return _load_task_logs_from_paths(log_paths)


def load_results_file(results_path: Path) -> List[Dict[str, Any]]:
    """Load agent outputs from a JSONL results file."""

    records: List[Dict[str, Any]] = []

    with results_path.open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or not stripped.startswith("{"):
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSON line in %s", results_path)

    return records


def evaluate_task_score(
    results_path: Path,
    config_path: Path,
    *,
    show_progress: Optional[bool] = None,
    progress_desc: Optional[str] = None,
    log_paths_override: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Convenience wrapper to evaluate a results file based on a config file."""

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    evaluation_config = (config or {}).get("Evaluation", {})
    enabled = evaluation_config.get("enabled", True)
    if not enabled:
        print("Evaluation disabled via config; skipping Task Score computation.")
        return {
            "metric": "Task Score",
            "status": "disabled",
            "success_count": None,
            "total_count": None,
            "task_score": None,
            "details": [],
        }
    override_paths: Optional[List[Path]] = None
    if log_paths_override:
        override_paths = [
            _resolve_path_relative(path_str, config_path.parent)
            for path_str in log_paths_override
        ]

    task_logs = _load_task_logs_for_evaluation(
        evaluation_config,
        results_path=results_path,
        config_dir=config_path.parent,
        override_paths=override_paths,
    )

    evaluator = TaskScoreEvaluator.from_config(
        evaluation_config,
        task_logs=task_logs,
    )
    records = load_results_file(results_path)

    config_show_progress = bool(evaluation_config.get("show_progress", False))
    final_show_progress = config_show_progress if show_progress is None else show_progress
    final_progress_desc = progress_desc or evaluation_config.get("progress_desc")

    return evaluator.evaluate_records(
        records,
        show_progress=final_show_progress,
        progress_desc=final_progress_desc,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Task Score for agent results.")
    parser.add_argument(
        "--results",
        required=True,
        help="Path to the JSONL results file produced by the agent run.",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Configuration file that contains the Evaluation section.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to save the evaluation metrics as JSON.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging verbosity for the evaluator.",
    )
    parser.add_argument(
        "--progress",
        dest="progress",
        action="store_true",
        default=None,
        help="Display a progress bar while evaluating tasks.",
    )
    parser.add_argument(
        "--no-progress",
        dest="progress",
        action="store_false",
        help="Disable progress bar even if enabled in config.",
    )
    parser.add_argument(
        "--progress-desc",
        help="Custom description to show alongside the progress bar.",
    )
    parser.add_argument(
        "--logs",
        action="append",
        help="Specify log JSONL files to load (repeat this flag to add multiple). "
        "Overrides Evaluation.logs in the config.",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper()))

    results_path = Path(args.results).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()

    metrics = evaluate_task_score(
        results_path,
        config_path,
        show_progress=args.progress,
        progress_desc=args.progress_desc,
        log_paths_override=args.logs,
    )

    print(json.dumps(metrics, ensure_ascii=False, indent=2))

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(metrics, file, ensure_ascii=False, indent=2)
        print(f"Evaluation metrics saved to: {output_path}")
    else:
        #存在根目录下的Results/evaluations/TS.json
        output_path = Path("Results/evaluations/TS.json").expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(metrics, file, ensure_ascii=False, indent=2)
        print(f"Evaluation metrics saved to: {output_path}")

def task_score(instruction: str, result: Any, label: Any, evaluator: TaskScoreEvaluator) -> Dict[str, Any]:
    """Evaluate a single task triple using an existing evaluator instance."""

    record = {
        "task": {"instruction": instruction, "label": label},
        "result": result,
    }
    return evaluator.evaluate_record(record)


# Backward compatibility alias for legacy code expecting task_success_rate.
task_success_rate = task_score


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
