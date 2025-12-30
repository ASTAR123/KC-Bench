"""
Generate smolagents tools for BFCL benchmark using LLM (one file per tool).

Workflow:
- Load question files under Benchmark/BFCL/data/unused_datasets/question.
- Deduplicate functions by name, gather parameter schema and sample questions.
- Call an LLM to emit @tool functions that RETURN SIMULATED RESULTS (no real API calls).
- For each question JSON, a same-named subfolder is created under Toolkit/BFCL/generated_tools,
  and tools from that file are saved inside it.
- __init__.py files are generated per subfolder and at the top level to import all tools.

Notes:
- MAX_TOOLS can limit generation for quick tests.
- Generated tools should be added to agent tool list as needed.
"""

from __future__ import annotations

import json
import concurrent.futures
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List

from openai import OpenAI
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
QUESTION_DIR = REPO_ROOT / "Benchmark/BFCL/data"
OUTPUT_DIR = REPO_ROOT / "Toolkit/BFCL/generated_tools"

# LLM config (adjust if needed)
MODEL_ID = "gpt-4.1"
API_BASE = "http://35.220.164.252:3888/v1"
API_KEY = "sk-YYRlEk1h5USYiUmwfIsiG6sRfAMwOl0yW1ASSFKwIZbCabip"

# Limit for quick runs; set to None to process all tools
MAX_TOOLS = None  # e.g., None for all

# Few-shot example for the model
FEW_SHOT = """
You are generating Python smolagents tools (@tool) for BFCL benchmark.
Rules:
- DO NOT make real network or file calls; simulate outputs deterministically.
- Use type hints; simple primitives only.
- Return a JSON string (via json.dumps) with fields: status, tool, args, result (mock).
- Keep the code concise and self-contained.

Example input:
TOOL_NAME: calculate_triangle_area
TOOL_SCHEMA: {"name": "calculate_triangle_area", "description": "Compute triangle area", "parameters": {"type": "object", "properties": {"base": {"type": "number"}, "height": {"type": "number"}}}}
SAMPLE_QUESTIONS: ["Compute area for base=3, height=4"]

Desired output (structure):
from smolagents import tool
import json

@tool
def calculate_triangle_area(base: float, height: float) -> str:
    \"\"\"Compute triangle area from base and height.\"\"\"
    area = 0.5 * base * height
    payload = {"status": "ok", "tool": "calculate_triangle_area", "args": {"base": base, "height": height}, "result": {"area": area}}
    return json.dumps(payload, ensure_ascii=False)
""".strip()


def load_questions_by_file() -> Dict[str, List[Dict[str, Any]]]:
    """Load questions keyed by their source JSON filename (stem)."""
    file_map: Dict[str, List[Dict[str, Any]]] = {}
    for path in sorted(QUESTION_DIR.glob("*.json")):
        items: List[Dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    items.append(json.loads(line))
                except Exception:
                    continue
        file_map[path.stem] = items
    return file_map


def collect_tools(raw_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    acc: Dict[str, Dict[str, Any]] = {}
    for obj in raw_items:
        questions = obj.get("question")
        questions = questions if isinstance(questions, list) else [questions]

        def add_tool(fn_obj: Any):
            name = None
            schema = None
            if isinstance(fn_obj, dict):
                name = fn_obj.get("name")
                schema = fn_obj
            else:
                name = str(fn_obj)
                schema = {"name": name}
            if not name:
                return
            bucket = acc.setdefault(name, {"schemas": [], "examples": []})
            bucket["schemas"].append(schema)
            if questions:
                bucket["examples"].extend(
                    [q if isinstance(q, str) else str(q) for q in questions]
                )

        if "function" in obj:
            fn_field = obj["function"]
            if isinstance(fn_field, list):
                for fn in fn_field:
                    add_tool(fn)
            else:
                add_tool(fn_field)
        if "missed_function" in obj:
            mf = obj["missed_function"]
            if isinstance(mf, list):
                for fn in mf:
                    add_tool(fn)
            else:
                add_tool(mf)
    return acc


def build_prompt(name: str, info: Dict[str, Any]) -> List[Dict[str, str]]:
    schema = info["schemas"][0] if info["schemas"] else {"name": name}
    examples_raw = info.get("examples", [])
    # Deduplicate while preserving order so all questions for this tool are surfaced.
    seen = set()
    examples: List[str] = []
    for ex in examples_raw:
        if ex not in seen:
            examples.append(ex)
            seen.add(ex)

    description = schema.get("description") or f"{name} tool."
    params = schema.get("parameters", {}) if isinstance(schema, dict) else {}
    props = params.get("properties", {}) if isinstance(params, dict) else {}
    arg_docs = []
    for param_name, param_info in props.items():
        p_desc = ""
        if isinstance(param_info, dict):
            p_desc = param_info.get("description", "")
        arg_docs.append(f"    {param_name}: {p_desc}".rstrip())
    arg_docs_text = "\n".join(arg_docs) if arg_docs else "    (none)"

    docstring_guide = f"""
Docstring format:
\"\"\"
{description}

Args:
{arg_docs_text}
Returns:
    str: JSON string with fields status, tool, args, result (simulated).
\"\"\"
""".strip()

    prompt = f"""
TOOL_NAME: {name}
TOOL_SCHEMA: {json.dumps(schema, ensure_ascii=False)}
SAMPLE_QUESTIONS: {json.dumps(examples, ensure_ascii=False)}
DOCSTRING_GUIDE: {docstring_guide}

Follow the few-shot pattern. No real API calls. Return json.dumps payload with status/tool/args/result. Use the docstring guide (summary + Args/Returns) derived from the BFCL schema.
"""
    return [
        {"role": "system", "content": "You generate python tools for smolagents. Produce only code."},
        {"role": "user", "content": FEW_SHOT},
        {"role": "user", "content": prompt},
    ]


def sanitize_name(name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)
    return safe or "tool"


def main() -> None:
    raw_items_by_file = load_questions_by_file()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = OpenAI(base_url=API_BASE, api_key=API_KEY)

    # Prepare tasks across all datasets honoring MAX_TOOLS globally.
    tasks: List[tuple[str, str, Dict[str, Any]]] = []
    for dataset_name, raw_items in raw_items_by_file.items():
        tool_map = collect_tools(raw_items)
        names = sorted(tool_map.keys())
        if MAX_TOOLS is not None:
            remaining = MAX_TOOLS - len(tasks)
            if remaining <= 0:
                break
            names = names[:remaining]
        dataset_dir = OUTPUT_DIR / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        for name in names:
            tasks.append((dataset_name, name, tool_map[name]))

    dataset_imports: DefaultDict[str, List[str]] = defaultdict(list)
    top_level_init: List[str] = []
    lock = threading.Lock()

    def generate(task: tuple[str, str, Dict[str, Any]]) -> None:
        dataset_name, name, info = task
        msgs = build_prompt(name, info)
        resp = client.chat.completions.create(
            model=MODEL_ID,
            messages=msgs,
            temperature=0,
            max_tokens=20480,
        )
        snippet = resp.choices[0].message.content or ""
        safe_name = sanitize_name(name)
        file_path = (OUTPUT_DIR / dataset_name) / f"{safe_name}.py"
        file_path.write_text(snippet.strip() + "\n", encoding="utf-8")
        with lock:
            dataset_imports[dataset_name].append(f"from .{safe_name} import {name}")
            top_level_init.append(f"from .{dataset_name}.{safe_name} import {name}")

    if tasks:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            with tqdm(total=len(tasks), desc="Generating tools", unit="tool") as pbar:
                futures = [executor.submit(generate, task) for task in tasks]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        print(f"Generation failed: {exc}")
                    finally:
                        pbar.update(1)

    for dataset_name, imports in dataset_imports.items():
        if imports:
            (OUTPUT_DIR / dataset_name / "__init__.py").write_text(
                "\n".join(sorted(imports)) + "\n", encoding="utf-8"
            )

    if top_level_init:
        (OUTPUT_DIR / "__init__.py").write_text(
            "\n".join(sorted(top_level_init)) + "\n", encoding="utf-8"
        )
    print(f"Saved tools under subfolders in {OUTPUT_DIR}, init files generated.")


if __name__ == "__main__":
    main()
