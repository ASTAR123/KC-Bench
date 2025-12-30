from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from Utils.environment_utils import (
    archive_environment_resources,
    build_task_objective,
    get_global_environment_context,
    set_task_environment_resources,
)
from Utils.result_utils import extract_agent_steps, summarize_steps
from Utils.agent_utils import (
    AgentBundle,
    create_agents_with_tool_map,
)
from smolagents import Tool


def _is_multi_turn_task(task: Dict[str, Any], multi_turn_flag: bool) -> bool:
    if multi_turn_flag:
        return True
    turns = task.get("question")
    if isinstance(turns, list) and turns:
        return True
    instructions = task.get("instruction")
    if isinstance(instructions, list) and len(instructions) > 1:
        return True
    return False


def _stringify_messages(messages: Any) -> str:
    """Render a list of role/content dicts (or raw strings) into a user prompt."""
    if not isinstance(messages, list):
        return str(messages)
    parts = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        else:
            parts.append(str(msg))
    return "\n".join(parts).strip()


def _extract_turn_prompts(task: Dict[str, Any]) -> List[str]:
    turns_raw = task.get("instruction") or task.get("question") or []
    prompts: List[str] = []
    for turn in turns_raw:
        prompts.append(_stringify_messages(turn))
    return prompts


def run_interactive_mode(agent, environment_context: Dict[str, Any]) -> None:
    """Run the agent in interactive mode."""
    print("\nEntering interactive mode, type 'quit' or 'exit' to exit")
    while True:
        try:
            user_input = input("\nPlease enter a task: ").strip()
            if user_input.lower() in ["quit", "exit"]:
                break
            if not user_input:
                continue

            print(f"\nExecuting task: {user_input}")
            interactive_task = {"description": user_input}
            _, resources = build_task_objective(interactive_task, environment_context)
            set_task_environment_resources(resources or _default_global_resources())
            result = agent.run(user_input)
            print(f"\nResult: {result}")

        except KeyboardInterrupt:
            print("\n\nProgram interrupted by user")
            break
        except Exception as exc:
            print(f"\nError executing task: {exc}")

def run_specific_task(
    agent, task_description: str, environment_context: Dict[str, Any]
) -> Tuple[Any, List[Dict[str, str]], List[Dict[str, Any]], Dict[str, Any]]:
    """Run a single task specified via command line."""
    print(f"Running specific task: {task_description}")
    single_task = {"description": task_description}
    _, env_resources = build_task_objective(single_task, environment_context)
    set_task_environment_resources(env_resources or _default_global_resources())
    result = agent.run(task_description)
    print(f"Result: {result}")
    steps = extract_agent_steps(agent)
    summary = summarize_steps(steps)
    return result, env_resources, steps, summary


def run_all_tasks(
    agent_bundle: AgentBundle,
    tasks: List[Dict[str, Any]],
    benchmark_type: str,
    environment_context: Dict[str, Any],
    *,
    include_environment: bool = False,
    archive_enabled: bool = False,
    archive_dir: Optional[str] = None,
    start_idx: Optional[int] = None,
    end_idx: Optional[int] = None,
    per_task_tools: bool = False,
    grouped_tools: Optional[Dict[str, Dict[str, Tool]]] = None,
    retry_attempts: int = 1,
    multi_turn: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Run benchmark tasks, optionally within a specific index range."""
    if not tasks:
        print("No tasks found, please check Benchmark directory or use --interactive mode")
        return [], []


    benchmark_name = environment_context.get("benchmark_name", "")
    total_tasks = len(tasks)
    resolved_start = 1 if not start_idx or start_idx < 1 else start_idx
    resolved_end = total_tasks if not end_idx or end_idx > total_tasks else end_idx

    if resolved_start > resolved_end:
        print(
            f"Invalid task range: start index ({resolved_start}) "
            f"is greater than end index ({resolved_end})."
        )
        return [], []

    indexed_tasks = [
        (index, task) for index, task in enumerate(tasks, 1) if resolved_start <= index <= resolved_end
    ]

    if not indexed_tasks:
        print(f"No tasks found in the range {resolved_start}-{resolved_end}.")
        return [], []

    if resolved_start != 1 or resolved_end != total_tasks:
        print(
            f"Found {total_tasks} tasks in total; executing range {resolved_start}-{resolved_end} "
            f"({len(indexed_tasks)} tasks)."
        )
    else:
        print(f"Found {total_tasks} tasks, starting execution...")

    all_results: List[Dict[str, Any]] = []
    all_logs: List[Dict[str, Any]] = []

    # Cache agents per tool signature to avoid rebuilding unnecessarily.
    agent_cache: Dict[str, Any] = {}

    for position, (index, task) in enumerate(indexed_tasks, 1):
        env_resources: List[Dict[str, str]] = []
        # Extract the task description based on the benchmark name
        task_description = task.get("description") or task.get("task") or task.get("instruction") or str(task)
        agent = agent_bundle.primary
        managed_agents = agent_bundle.managed
        tool_source = ""
        selected_tool_names: List[str] = []
        # Build a task-specific agent when requested.
        if per_task_tools:
            tool_map, tool_source = _select_tools_for_task(task, grouped_tools or {})
            cache_key = _cache_key_for_tools(tool_map)
            if cache_key in agent_cache:
                agent = agent_cache[cache_key]["primary"]
                managed_agents = agent_cache[cache_key]["managed"]
                selected_tool_names = agent_cache[cache_key]["tool_names"]
            else:
                task_bundle = create_agents_with_tool_map(
                    agent_settings=agent_bundle.agent_settings,
                    blueprints=agent_bundle.blueprints,
                    mode=agent_bundle.mode,
                    model=agent_bundle.model,
                    tool_map=tool_map if tool_map else agent_bundle.tool_map,
                    force_all_tools=True,
                )
                agent_cache[cache_key] = {
                    "primary": task_bundle.primary,
                    "managed": task_bundle.managed,
                    "tool_names": sorted(tool_map.keys()),
                }
                agent = task_bundle.primary
                managed_agents = task_bundle.managed
                selected_tool_names = agent_cache[cache_key]["tool_names"]
        if per_task_tools:
            display_source = tool_source or "default"
            display_tools = ", ".join(selected_tool_names) if selected_tool_names else "none"
            print(f"  Tool selection [{display_source}]: {display_tools}")
        last_error: Exception | None = None
        attempts = max(1, int(retry_attempts or 1))
        for attempt in range(1, attempts + 1):
            turn_logs: List[Dict[str, Any]] = []
            try:
                objective, env_resources = build_task_objective(task, environment_context)
                set_task_environment_resources(env_resources or _default_global_resources())

                task_is_multi_turn = _is_multi_turn_task(task, multi_turn)
                if task_is_multi_turn:
                    turn_prompts = _extract_turn_prompts(task)
                    preview = turn_prompts[0] if turn_prompts else task_description
                    print(
                        f"\n[{position}/{len(indexed_tasks)}] Executing task #{index} (attempt {attempt}/{attempts}) [multi-turn]: {preview}"
                    )
                else:
                    print(
                        f"\n[{position}/{len(indexed_tasks)}] Executing task #{index} (attempt {attempt}/{attempts}): {task_description}"
                    )
                if environment_context.get("type") == "per-task":
                    if env_resources:
                        print("  Resolved environment resources:")
                        for resource in env_resources:
                            print(f"    - {resource['label']}: {resource['path']}")
                    else:
                        print("  Warning: No environment resources resolved for this task.")

                request_prompt = objective or task_description
                if task_is_multi_turn:
                    result = None
                    turn_prompts = turn_prompts if "turn_prompts" in locals() else _extract_turn_prompts(task)
                    if not turn_prompts:
                        turn_prompts = [request_prompt]
                    for turn_idx, prompt in enumerate(turn_prompts, start=1):
                        print(f"  Turn {turn_idx}/{len(turn_prompts)}")
                        result = agent.run(prompt, reset=(turn_idx == 1))
                        turn_logs.append({"turn": turn_idx, "prompt": prompt, "result": str(result)})
                    print(f"Result (final turn): {result}")
                else:
                    result = agent.run(request_prompt)
                    print(f"Result: {result}")
                steps = extract_agent_steps(agent)
                summary = summarize_steps(steps)

                archive_metadata = None
                if archive_enabled and archive_dir:
                    archive_metadata = archive_environment_resources(
                        env_resources,
                        archive_dir,
                        task_identifier=index,
                    )

                task_result = {
                    "task_id": index,
                    "task": task,
                    "result": str(result),
                    "timestamp": datetime.now().isoformat(),
                    "benchmark_type": benchmark_type,
                    "environment_type": environment_context.get("type"),
                }
                if task_is_multi_turn:
                    task_result["turns"] = turn_logs
                if include_environment:
                    task_result["environment_resources"] = env_resources
                if archive_metadata:
                    task_result["environment_archive"] = archive_metadata
                task_result.update(summary)
                all_results.append(task_result)
                log_entry = {
                    "task_id": index,
                    "task": task,
                    "timestamp": task_result["timestamp"],
                    "status": "success",
                    "result": str(result),
                    "steps": steps,
                }
                if task_is_multi_turn:
                    log_entry["turns"] = turn_logs
                if include_environment:
                    log_entry["environment_resources"] = env_resources
                if archive_metadata:
                    log_entry["environment_archive"] = archive_metadata
                log_entry.update(summary)
                all_logs.append(log_entry)
                last_error = None
                break

            except Exception as exc:
                last_error = exc
                if attempt < attempts:
                    print(f"Task {index} attempt {attempt} failed: {exc}. Retrying...")
                    continue

                print(f"Task {index} execution failed after {attempts} attempt(s): {exc}")
                steps = extract_agent_steps(agent)
                summary = summarize_steps(steps)
                archive_metadata = None
                if archive_enabled and archive_dir:
                    archive_metadata = archive_environment_resources(
                        env_resources,
                        archive_dir,
                        task_identifier=f"{index}_error",
                    )
                task_result = {
                    "task_id": index,
                    "task": task,
                    "error": str(exc),
                    "timestamp": datetime.now().isoformat(),
                    "benchmark_type": benchmark_type,
                    "environment_type": environment_context.get("type"),
                }
                if turn_logs:
                    task_result["turns"] = turn_logs
                if include_environment:
                    task_result["environment_resources"] = env_resources
                if archive_metadata:
                    task_result["environment_archive"] = archive_metadata
                task_result.update(summary)
                all_results.append(task_result)
                log_entry = {
                    "task_id": index,
                    "task": task,
                    "timestamp": task_result["timestamp"],
                    "status": "error",
                    "error": str(exc),
                    "steps": steps,
                }
                if turn_logs:
                    log_entry["turns"] = turn_logs
                if include_environment:
                    log_entry["environment_resources"] = env_resources
                if archive_metadata:
                    log_entry["environment_archive"] = archive_metadata
                log_entry.update(summary)
                all_logs.append(log_entry)

    successful = len([record for record in all_results if "error" not in record])
    failed = len(all_results) - successful
    print(f"\nExecution completed: {successful} successful, {failed} failed")
    return all_results, all_logs


def _default_global_resources() -> List[Dict[str, str]]:
    """Fallback resources built from the global environment context."""
    global_context = get_global_environment_context()
    base_path = global_context.get("base_path")
    if base_path:
        return [{"label": "global_environment_root", "path": str(base_path)}]
    return []


def _select_tools_for_task(task: Dict[str, Any], grouped_tools: Dict[str, Dict[str, Tool]]) -> tuple[Dict[str, Tool], str]:
    """Pick tools for a task based on its source dataset and requested tool names."""
    dataset = task.get("_dataset") or task.get("_source_file")
    tool_pool = grouped_tools.get(dataset, {})
    source_label = str(dataset) if dataset else ""
    if not tool_pool and isinstance(dataset, str):
        # If dataset was a path, try stem.
        from pathlib import Path

        dataset_stem = Path(dataset).stem
        tool_pool = grouped_tools.get(dataset_stem, {})
        if tool_pool:
            source_label = dataset_stem

    requested = _extract_requested_tool_names(task)
    if tool_pool:
        if not requested:
            return dict(tool_pool), source_label
        selected: Dict[str, Tool] = {}
        for name in requested:
            tool = tool_pool.get(name)
            if tool:
                selected[name] = tool
        return selected or dict(tool_pool), source_label

    # Fallback: if no dataset match, pick the group covering most requested tools.
    if requested and grouped_tools:
        best_group = None
        best_hits = 0
        for group_name, pool in grouped_tools.items():
            hits = sum(1 for name in requested if name in pool)
            if hits > best_hits:
                best_hits = hits
                best_group = group_name
        if best_group and best_hits > 0:
            pool = grouped_tools[best_group]
            selected = {name: pool[name] for name in requested if name in pool}
            return selected or dict(pool), best_group

    return {}, source_label


def _extract_requested_tool_names(task: Dict[str, Any]) -> List[str]:
    """Extract tool names from task metadata (label or explicit tools)."""
    names: List[str] = []
    if isinstance(task.get("tools"), list):
        names.extend(str(item) for item in task["tools"] if item)

    labels = task.get("label") or task.get("labels")
    if labels:
        import re

        label_list = labels if isinstance(labels, list) else [labels]
        for label in label_list:
            if not isinstance(label, str):
                continue
            func_match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(", label)
            if func_match:
                names.append(func_match.group(1))

    seen = set()
    deduped: List[str] = []
    for name in names:
        if name not in seen:
            deduped.append(name)
            seen.add(name)
    return deduped


def _cache_key_for_tools(tool_map: Dict[str, Tool]) -> str:
    if not tool_map:
        return "default"
    return "|".join(sorted(tool_map.keys()))
