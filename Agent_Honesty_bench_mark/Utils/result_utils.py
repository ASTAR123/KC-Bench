from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Sequence


def extract_agent_steps(agent: Any) -> List[Dict[str, Any]]:
    """Extract full step history from an agent if available."""
    if agent is None:
        return []

    def _best_effort_memory_steps(memory_obj: Any) -> List[Dict[str, Any]]:
        """Fallback serializer that does not rely on get_full_steps."""
        raw_steps = getattr(memory_obj, "steps", None)
        if not raw_steps:
            return []

        serialized: List[Dict[str, Any]] = []
        for entry in raw_steps:
            if hasattr(entry, "dict") and callable(getattr(entry, "dict")):
                try:
                    serialized.append(entry.dict())
                    continue
                except Exception as exc:  # pragma: no cover - defensive
                    serialized.append({"error": "serialize_failed", "detail": str(exc), "repr": repr(entry)})
                    continue
            if isinstance(entry, dict):
                serialized.append(entry)
            else:
                serialized.append({"value": repr(entry)})
        return serialized

    candidate = None
    errors: List[str] = []
    if hasattr(agent, "get_full_steps") and callable(getattr(agent, "get_full_steps")):  # type: ignore[attr-defined]
        try:
            candidate = agent.get_full_steps()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(f"agent.get_full_steps failed: {exc}")
            candidate = None
    if candidate is None and getattr(agent, "memory", None) is not None:
        memory = getattr(agent, "memory")
        if hasattr(memory, "get_full_steps") and callable(memory.get_full_steps):
            try:
                candidate = memory.get_full_steps()
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(f"memory.get_full_steps failed: {exc}")
                candidate = None
        if candidate is None:
            candidate = _best_effort_memory_steps(memory)

    if candidate is None:
        if errors:
            print(f"Warning: unable to extract agent steps ({' | '.join(errors)})")
        return []
    if isinstance(candidate, list):
        return candidate
    if isinstance(candidate, Sequence):
        return list(candidate)
    return []


def summarize_steps(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate statistics from a list of agent steps."""
    step_count = len(steps)

    total_input_tokens = None
    total_output_tokens = None

    for step in steps:
        usage = step.get("token_usage") if isinstance(step, dict) else None
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            if isinstance(input_tokens, (int, float)):
                total_input_tokens = (total_input_tokens or 0) + int(input_tokens)
            if isinstance(output_tokens, (int, float)):
                total_output_tokens = (total_output_tokens or 0) + int(output_tokens)

    total_tokens = None
    if total_input_tokens is not None or total_output_tokens is not None:
        total_tokens = (total_input_tokens or 0) + (total_output_tokens or 0)

    min_start = None
    max_end = None
    for step in steps:
        timing = step.get("timing") if isinstance(step, dict) else None
        if isinstance(timing, dict):
            start = timing.get("start_time")
            end = timing.get("end_time")
            if isinstance(start, (int, float)):
                min_start = start if min_start is None else min(min_start, start)
            if isinstance(end, (int, float)):
                max_end = end if max_end is None else max(max_end, end)

    elapsed_seconds = None
    if min_start is not None and max_end is not None:
        elapsed_seconds = float(max_end - min_start)
        if elapsed_seconds < 0:
            elapsed_seconds = None

    return {
        "step_count": step_count,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_tokens": total_tokens,
        "elapsed_seconds": elapsed_seconds,
    }


def _normalize_records(records: Any) -> List[Dict[str, Any]]:
    if records is None:
        return []
    if isinstance(records, list):
        normalized = []
        for entry in records:
            if isinstance(entry, dict):
                normalized.append(entry)
            else:
                normalized.append({"value": entry})
        return normalized
    if isinstance(records, dict):
        return [records]
    return [{"value": records}]


def save_results(config: Dict[str, Any], results: Any) -> str:
    """Save results to the specified directory in JSONL format."""
    output_config = config.get("Output", {})
    save_dir = output_config.get("save_dir", "./results/outputs")

    # Create output directories
    os.makedirs(save_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(save_dir, f"results_{timestamp}.jsonl")
    saved_at = datetime.now().isoformat()

    items = _normalize_records(results)
    with open(results_file, "w", encoding="utf-8") as file:
        for item in items:
            record = dict(item)
            record.setdefault("saved_at", saved_at)
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Results saved to: {results_file}")
    return results_file

def _slugify_label(label: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z._-]+", "_", label).strip("._-")
    return slug or "log"


def save_logs(
    config: Dict[str, Any],
    logs: Any | None = None,
    agent: Any | None = None,
    label: str | None = None,
) -> str:
    """
    Persist agent execution logs to disk.

    Args:
        config: Global configuration dictionary.
        logs: Preformatted log payload that includes agent steps (list/dict). If omitted,
            the function attempts to extract steps from the provided agent.
        agent: Agent instance used to extract steps when `logs` is None.
        label: Optional label appended to the log filename for easier identification.
    """
    output_config = config.get("Output", {})
    log_dir = output_config.get("log_dir", "./results/logs")
    os.makedirs(log_dir, exist_ok=True)

    if logs is None and agent is not None:
        steps = extract_agent_steps(agent)
        summary = summarize_steps(steps)
        entry = {"steps": steps, **summary, "timestamp": datetime.now().isoformat()}
        logs = [entry]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_parts = ["logs", timestamp]
    if label:
        filename_parts.append(_slugify_label(label))
    log_file = os.path.join(log_dir, "_".join(filename_parts) + ".jsonl")

    items = _normalize_records(logs)
    saved_at = datetime.now().isoformat()
    agent_steps_cache: List[Dict[str, Any]] = extract_agent_steps(agent) if agent is not None else []
    agent_summary_cache: Dict[str, Any] = summarize_steps(agent_steps_cache) if agent_steps_cache else {}

    with open(log_file, "w", encoding="utf-8") as file:
        for item in items:
            record = dict(item)
            record.setdefault("saved_at", saved_at)
            if label and "label" not in record:
                record["label"] = label
            # Backfill steps/summary when the caller did not include them
            if not record.get("steps") and agent_steps_cache and len(items) == 1:
                record["steps"] = agent_steps_cache
                for key, value in agent_summary_cache.items():
                    record.setdefault(key, value)
            elif not record.get("steps") and agent is not None and not agent_steps_cache:
                record.setdefault("log_warning", "agent memory contained no steps during save_logs")
            file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    print(f"Logs saved to: {log_file}")
    return log_file
