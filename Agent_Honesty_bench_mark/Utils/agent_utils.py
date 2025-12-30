from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Type

import yaml

from smolagents import CodeAgent, Tool
from smolagents.agents import MultiStepAgent, ToolCallingAgent

from Utils.tool_utils import load_tools


AGENT_CLASS_REGISTRY: Dict[str, Type[MultiStepAgent]] = {
    "toolcallingagent": ToolCallingAgent,
    "toolcalling": ToolCallingAgent,
    "react": ToolCallingAgent,
    "codeagent": CodeAgent,
    "code": CodeAgent,
}

AGENT_MODE_ALIASES = {
    "single-agent multi-round": "single-agent multi-round",
    "single_agent_multi_round": "single-agent multi-round",
    "single-agent single-round": "single-agent single-round",
    "single_agent_single_round": "single-agent single-round",
    "single-round": "single-agent single-round",
    "multi-agent": "multi-agent",
    "multi_agent": "multi-agent",
    "mas": "multi-agent",
}

COMMON_AGENT_KEYS = {
    "instructions",
    "max_steps",
    "add_base_tools",
    "verbosity_level",
    "managed_agents",
    "step_callbacks",
    "planning_interval",
    "name",
    "description",
    "provide_run_summary",
    "final_answer_checks",
    "return_full_result",
    "logger",
}

TOOLCALLING_AGENT_KEYS = COMMON_AGENT_KEYS | {
    "prompt_templates",
    "stream_outputs",
    "max_tool_threads",
}

CODE_AGENT_KEYS = COMMON_AGENT_KEYS | {
    "prompt_templates",
    "additional_authorized_imports",
    "planning_interval",
    "executor",
    "executor_type",
    "executor_kwargs",
    "max_print_outputs_length",
    "stream_outputs",
    "use_structured_outputs_internally",
    "code_block_tags",
}


@dataclass
class AgentBundle:
    mode: str
    primary: MultiStepAgent
    managed: List[MultiStepAgent]
    blueprints: List[Dict[str, Any]]
    agent_settings: Dict[str, Any]
    model: Any
    tool_map: Dict[str, Tool]


def create_agents(config: Dict[str, Any], model: Any) -> AgentBundle:
    """
    Create agent instances based on configuration and a pre-instantiated model.

    Args:
        config: Full configuration dictionary.
        model: Model instance supplied to each agent.

    Returns:
        AgentBundle containing the primary agent, optional managed agents, and metadata.
    """
    agent_settings = config.get("Agent", {})
    mode = normalize_agent_mode(agent_settings.get("type", "single-agent multi-round"))

    blueprints = load_agent_blueprints(agent_settings)
    if not blueprints:
        blueprints = [_default_blueprint(agent_settings)]
    entry_agent_name = _preferred_entry_agent(agent_settings)
    if entry_agent_name:
        blueprints = _prioritize_blueprints(blueprints, entry_agent_name)

    tools = load_tools(config)
    tool_map = _build_tool_map(tools)

    primary_agent, managed_agents = _build_agent_hierarchy(
        agent_settings=agent_settings,
        blueprints=blueprints,
        tool_map=tool_map,
        model=model,
        mode=mode,
    )

    return AgentBundle(
        mode=mode,
        primary=primary_agent,
        managed=managed_agents,
        blueprints=blueprints,
        agent_settings=agent_settings,
        model=model,
        tool_map=tool_map,
    )


def create_agents_with_tool_map(
    *,
    agent_settings: Dict[str, Any],
    blueprints: List[Dict[str, Any]],
    mode: str,
    model: Any,
    tool_map: Dict[str, Tool],
    force_all_tools: bool = False,
) -> AgentBundle:
    """
    Build agents using a provided tool map (skip global load_tools).
    Useful for per-task tool selection scenarios.
    """
    settings_copy = dict(agent_settings)
    if force_all_tools:
        settings_copy["fill_with_all_tools"] = True
    entry_agent_name = _preferred_entry_agent(settings_copy)
    if entry_agent_name:
        blueprints = _prioritize_blueprints(blueprints, entry_agent_name)
    primary_agent, managed_agents = _build_agent_hierarchy(
        agent_settings=settings_copy,
        blueprints=blueprints,
        tool_map=tool_map,
        model=model,
        mode=mode,
    )
    return AgentBundle(
        mode=mode,
        primary=primary_agent,
        managed=managed_agents,
        blueprints=blueprints,
        agent_settings=agent_settings,
        model=model,
        tool_map=tool_map,
    )


# ---------------------------------------------------------------------------
# Agent creation helpers
# ---------------------------------------------------------------------------


def create_agent_instance(
    *,
    agent_settings: Dict[str, Any],
    blueprint: Dict[str, Any],
    tool_map: Dict[str, Tool],
    mode: str,
    model: Any,
    managed_agents: Optional[Sequence[MultiStepAgent]] = None,
) -> MultiStepAgent:
    """Create an agent based on a blueprint and available tools."""
    agent_class = _resolve_agent_class(
        blueprint.get("agent_type") or agent_settings.get("agent_type") or "ToolCallingAgent"
    )

    fallback_to_all = bool(agent_settings.get("fill_with_all_tools", True))
    selected_tools = _select_tools(tool_map, blueprint.get("tools"), fallback_to_all=fallback_to_all)

    agent_kwargs = _collect_agent_kwargs(agent_class, agent_settings, blueprint, mode)

    if managed_agents and agent_class is ToolCallingAgent:
        agent_kwargs["managed_agents"] = list(managed_agents)
    elif managed_agents:
        print("Warning: managed agents are only supported for ToolCallingAgent; ignoring managed_agents.")

    return agent_class(
        tools=list(selected_tools),
        model=model,
        **agent_kwargs,
    )


def load_agent_blueprints(agent_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load agent blueprint definitions from the configured directory or file."""
    agent_dir = agent_settings.get("agent_dir")
    if not agent_dir:
        return []

    path = Path(agent_dir).expanduser()
    if not path.exists():
        print(f"Warning: Agent configuration path {path} does not exist. Falling back to default agent settings.")
        return []

    if path.is_dir():
        blueprints: List[Dict[str, Any]] = []
        for file_path in sorted(path.iterdir()):
            if file_path.suffix.lower() not in {".json", ".jsonl", ".yaml", ".yml"}:
                continue
            blueprints.extend(_load_blueprints_from_file(file_path))
        return blueprints

    return _load_blueprints_from_file(path)


def normalize_agent_mode(mode: str) -> str:
    if not mode:
        return "single-agent multi-round"
    return AGENT_MODE_ALIASES.get(mode.strip().lower(), mode.strip().lower())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_agent_class(agent_type: str) -> Type[MultiStepAgent]:
    normalized = agent_type.strip().lower()
    cls = AGENT_CLASS_REGISTRY.get(normalized)
    if cls is None:
        raise ValueError(
            f"Unsupported agent_type '{agent_type}'. Supported types: {sorted(AGENT_CLASS_REGISTRY.keys())}"
        )
    return cls


def _build_tool_map(tools: List[Tool]) -> Dict[str, Tool]:
    tool_map = {}
    for tool in tools:
        tool_name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
        if not tool_name:
            tool_name = tool.__class__.__name__
        tool_map[tool_name] = tool
    return tool_map


def _build_agent_hierarchy(
    *,
    agent_settings: Dict[str, Any],
    blueprints: List[Dict[str, Any]],
    tool_map: Dict[str, Tool],
    model: Any,
    mode: str,
) -> tuple[MultiStepAgent, List[MultiStepAgent]]:
    managed_agents: List[MultiStepAgent] = []

    if mode == "multi-agent" and _has_node_structure(blueprints):
        primary_agent, managed_agents = _instantiate_multi_agent_hierarchy(
            agent_settings=agent_settings,
            blueprints=blueprints,
            tool_map=tool_map,
            model=model,
            mode=mode,
        )
        return primary_agent, managed_agents

    if mode == "multi-agent":
        for blueprint in blueprints[1:]:
            managed_agent = create_agent_instance(
                agent_settings=agent_settings,
                blueprint=blueprint,
                tool_map=tool_map,
                mode=mode,
                model=model,
            )
            managed_agents.append(managed_agent)

    primary_blueprint = blueprints[0]
    primary_agent = create_agent_instance(
        agent_settings=agent_settings,
        blueprint=primary_blueprint,
        tool_map=tool_map,
        mode=mode,
        model=model,
        managed_agents=managed_agents if managed_agents else None,
    )

    return primary_agent, managed_agents


def _select_tools(tool_map: Dict[str, Tool], requested_tools: Optional[List[str]], fallback_to_all: bool) -> List[Tool]:
    if not requested_tools:
        return list(tool_map.values()) if fallback_to_all else []

    selected: List[Tool] = []
    for tool_name in requested_tools:
        tool = tool_map.get(tool_name)
        if tool:
            selected.append(tool)
        else:
            print(f"Warning: Tool '{tool_name}' not found among loaded tools; skipping.")

    if not selected and fallback_to_all:
        print("Warning: No requested tools available. Falling back to all loaded tools.")
        return list(tool_map.values())

    return selected


def _collect_agent_kwargs(
    agent_class: Type[MultiStepAgent],
    agent_settings: Dict[str, Any],
    blueprint: Dict[str, Any],
    mode: str,
) -> Dict[str, Any]:
    allowed_keys = _allowed_keys_for_agent(agent_class)
    kwargs: Dict[str, Any] = {}

    def assign(source: Dict[str, Any], key: str) -> None:
        if key in source and source[key] is not None:
            kwargs[key] = source[key]

    for key in allowed_keys:
        assign(agent_settings, key)
        assign(blueprint, key)

    resolved_instructions = _resolve_instructions(
        existing=kwargs.get("instructions"),
        blueprint=blueprint,
        agent_settings=agent_settings,
    )
    if resolved_instructions is not None:
        kwargs["instructions"] = resolved_instructions

    if "description" not in kwargs and blueprint.get("description"):
        kwargs["description"] = blueprint["description"]

    if "instructions" not in kwargs and blueprint.get("description"):
        kwargs["instructions"] = blueprint["description"]

    if "prompt_templates" in kwargs:
        kwargs["prompt_templates"] = _resolve_prompt_templates(kwargs["prompt_templates"])
    elif agent_settings.get("prompt_templates") and "prompt_templates" in allowed_keys:
        kwargs["prompt_templates"] = _resolve_prompt_templates(agent_settings["prompt_templates"])

    planning_interval = kwargs.get("planning_interval")
    if isinstance(planning_interval, (int, float)) and planning_interval < 0:
        kwargs["planning_interval"] = None
    if mode == "single-agent single-round":
        kwargs["max_steps"] = 1
    elif "max_steps" not in kwargs:
        kwargs["max_steps"] = 20

    if "name" not in kwargs:
        kwargs["name"] = blueprint.get("name") or agent_settings.get("name") or agent_class.__name__

    return {key: value for key, value in kwargs.items() if key in allowed_keys and value is not None}


def _resolve_prompt_templates(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, Path):
        path = value
    else:
        path = Path(value).expanduser()

    if not path.exists():
        print(f"Warning: Prompt templates file {path} not found. Using default templates.")
        return None

    with open(path, "r", encoding="utf-8") as file:
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(file)
        if path.suffix.lower() == ".json":
            return json.load(file)

    print(f"Warning: Unsupported prompt templates format for {path}. Expected YAML or JSON.")
    return None


def _resolve_instructions(
    *,
    existing: Optional[str],
    blueprint: Dict[str, Any],
    agent_settings: Dict[str, Any],
) -> Optional[str]:
    """Determine the instructions/system prompt for an agent."""
    if existing:
        return existing

    system_prompt = blueprint.get("system_prompt")
    if system_prompt:
        coerced = _coerce_prompt_value(system_prompt, label="agent system_prompt")
        if coerced is not None:
            return coerced

    legacy_prompt_path = blueprint.get("system_prompt_path") or blueprint.get("instructions_path")
    if legacy_prompt_path:
        print("Warning: 'system_prompt_path' is deprecated; use 'system_prompt' (path or string) in agent config.")
        instructions_text = _load_text_file(legacy_prompt_path)
        if instructions_text:
            return instructions_text

    fallback_prompt = agent_settings.get("system_prompt")
    if fallback_prompt:
        print(
            "Warning: Define 'system_prompt' inside the agent config file; support in the global Agent section is deprecated."
        )
        coerced = _coerce_prompt_value(fallback_prompt, label="global system_prompt")
        if coerced is not None:
            return coerced

    fallback_path = agent_settings.get("system_prompt_path") or agent_settings.get("instructions_path")
    if fallback_path:
        print(
            "Warning: 'system_prompt_path' should be moved into the agent config file; falling back to global setting."
        )
        instructions_text = _load_text_file(fallback_path)
        if instructions_text:
            return instructions_text

    return None


def _coerce_prompt_value(value: Any, *, label: str) -> Optional[str]:
    """Treat a value as either a direct prompt string or a file path."""
    if value is None:
        return None
    if isinstance(value, str):
        candidate = Path(value).expanduser()
        if candidate.exists():
            content = _load_text_file(candidate)
            if content:
                return content
        return value
    print(f"Warning: Unexpected {label} type {type(value).__name__}; expected string path or prompt text.")
    return None


def _load_text_file(path: str | Path) -> Optional[str]:
    try:
        resolved = Path(path).expanduser()
        with open(resolved, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as exc:
        print(f"Warning: Failed to load text from {path}: {exc}")
        return None


def _load_blueprints_from_file(path: Path) -> List[Dict[str, Any]]:
    try:
        if path.suffix.lower() == ".jsonl":
            with open(path, "r", encoding="utf-8") as file:
                content = file.read().strip()
            if not content:
                return []
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                blueprints: List[Dict[str, Any]] = []
                with open(path, "r", encoding="utf-8") as file:
                    for line in file:
                        line = line.strip()
                        if not line:
                            continue
                        blueprints.append(json.loads(line))
                return blueprints
        else:
            with open(path, "r", encoding="utf-8") as file:
                if path.suffix.lower() in {".yaml", ".yml"}:
                    data = yaml.safe_load(file)
                else:
                    data = json.load(file)

        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]

        print(f"Warning: Unexpected data format in agent config file {path}, expected dict or list.")
        return []
    except Exception as exc:
        print(f"Warning: Failed to load agent blueprint from {path}: {exc}")
        return []


def _default_blueprint(agent_settings: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": agent_settings.get("name", "Agent"),
        "description": agent_settings.get("description"),
        "tools": agent_settings.get("tools"),
        "agent_type": agent_settings.get("agent_type"),
    }


def _allowed_keys_for_agent(agent_class: Type[MultiStepAgent]) -> set[str]:
    if agent_class is ToolCallingAgent:
        return TOOLCALLING_AGENT_KEYS
    if agent_class is CodeAgent:
        return CODE_AGENT_KEYS
    return COMMON_AGENT_KEYS


def _preferred_entry_agent(agent_settings: Dict[str, Any]) -> Optional[str]:
    entry_agent = agent_settings.get("entry_agent_name") or agent_settings.get("entry_agent")
    if isinstance(entry_agent, str):
        stripped = entry_agent.strip()
        return stripped or None
    return None


def _prioritize_blueprints(blueprints: List[Dict[str, Any]], entry_agent_name: str) -> List[Dict[str, Any]]:
    """Move the preferred entry agent (if present) to the front of the list."""
    if not entry_agent_name:
        return blueprints
    reordered: List[Dict[str, Any]] = []
    remaining: List[Dict[str, Any]] = []
    for blueprint in blueprints:
        if isinstance(blueprint, dict) and blueprint.get("name") == entry_agent_name:
            reordered.append(blueprint)
        else:
            remaining.append(blueprint)
    if not reordered:
        return blueprints
    reordered.extend(remaining)
    return reordered


def _has_node_structure(blueprints: Sequence[Dict[str, Any]]) -> bool:
    for blueprint in blueprints:
        if isinstance(blueprint, dict) and "node" in blueprint:
            return True
    return False


def _instantiate_multi_agent_hierarchy(
    *,
    agent_settings: Dict[str, Any],
    blueprints: Sequence[Dict[str, Any]],
    tool_map: Dict[str, Tool],
    model: Any,
    mode: str,
) -> tuple[MultiStepAgent, List[MultiStepAgent]]:
    blueprint_map: Dict[str, Dict[str, Any]] = {}
    order_map: Dict[str, int] = {}

    for idx, blueprint in enumerate(blueprints):
        if not isinstance(blueprint, dict):
            continue
        name = blueprint.get("name") or f"Agent_{idx + 1}"
        blueprint_copy = dict(blueprint)
        blueprint_copy["name"] = name
        nodes = blueprint_copy.get("node")
        if nodes is None:
            blueprint_copy["node"] = []
        elif isinstance(nodes, (list, tuple, set)):
            blueprint_copy["node"] = [str(node) for node in nodes]
        else:
            blueprint_copy["node"] = [str(nodes)]
        blueprint_map[name] = blueprint_copy
        order_map[name] = idx

    if not blueprint_map:
        raise ValueError("No agent blueprints available to instantiate multi-agent hierarchy.")

    referenced: set[str] = set()
    for blueprint in blueprint_map.values():
        for child in blueprint.get("node", []):
            if child:
                referenced.add(child)

    root_candidates = [name for name in blueprint_map if name not in referenced]
    if not root_candidates:
        root_candidates = list(blueprint_map.keys())

    preferred_root = _preferred_entry_agent(agent_settings)
    root_name = preferred_root if preferred_root in blueprint_map else None
    if preferred_root and root_name is None:
        print(f"Warning: Configured entry agent '{preferred_root}' not found; falling back to inferred root.")
    if preferred_root and preferred_root in referenced:
        print(
            f"Warning: Configured entry agent '{preferred_root}' is referenced as a child; continuing but hierarchy may be imbalanced."
        )
    if root_name is None:
        root_name = min(root_candidates, key=lambda name: order_map.get(name, float("inf")))

    agent_cache: Dict[str, MultiStepAgent] = {}
    managed_registry: List[MultiStepAgent] = []

    def build_agent(name: str, stack: List[str]) -> Optional[MultiStepAgent]:
        if name in agent_cache:
            return agent_cache[name]

        blueprint = blueprint_map.get(name)
        if blueprint is None:
            print(f"Warning: Blueprint for agent '{name}' not found; skipping instantiation.")
            return None

        if name in stack:
            cycle = " -> ".join(stack + [name])
            print(f"Warning: Cycle detected in agent hierarchy ({cycle}); skipping recursive attachment.")
            return None

        child_instances: List[MultiStepAgent] = []
        child_names = blueprint.get("node") or []
        for child_name in child_names:
            if child_name not in blueprint_map:
                print(f"Warning: Child agent '{child_name}' referenced by '{name}' is not defined.")
                continue
            child_agent = build_agent(child_name, stack + [name])
            if child_agent is not None:
                child_instances.append(child_agent)

        agent = create_agent_instance(
            agent_settings=agent_settings,
            blueprint=blueprint,
            tool_map=tool_map,
            mode=mode,
            model=model,
            managed_agents=child_instances if child_instances else None,
        )
        agent_cache[name] = agent
        if name != root_name and agent not in managed_registry:
            managed_registry.append(agent)
        return agent

    primary_agent = build_agent(root_name, [])
    if primary_agent is None:
        raise ValueError(f"Failed to instantiate root multi-agent '{root_name}'.")

    for name in blueprint_map:
        build_agent(name, [])

    _print_multi_agent_structure(root_name, blueprint_map)

    remaining_managed = [agent_cache[name] for name in blueprint_map if name != root_name and name in agent_cache]
    ordered_managed: List[MultiStepAgent] = []
    for agent in managed_registry:
        if agent not in ordered_managed:
            ordered_managed.append(agent)
    for agent in remaining_managed:
        if agent not in ordered_managed:
            ordered_managed.append(agent)

    return primary_agent, ordered_managed


def _print_multi_agent_structure(root_name: str, blueprint_map: Dict[str, Dict[str, Any]]) -> None:
    print("Multi-agent hierarchy:")

    def render(name: str, prefix: str, is_last: bool, is_root: bool, visited: set[str]) -> None:
        if name in visited:
            connector = "└─ " if not is_root and is_last else "├─ "
            line = f"{name} (cycle)"
            if is_root:
                print(line)
            else:
                print(f"{prefix}{connector}{line}")
            return

        visited.add(name)
        blueprint = blueprint_map.get(name, {})
        label = name
        description = blueprint.get("description")
        if description:
            label = f"{label} - {description}"

        if is_root:
            print(label)
            child_prefix = ""
        else:
            connector = "└─ " if is_last else "├─ "
            print(f"{prefix}{connector}{label}")
            child_prefix = prefix + ("   " if is_last else "│  ")

        raw_children = blueprint.get("node") or []
        children_entries: List[tuple[str, str]] = []
        for child in raw_children:
            child_name = str(child)
            if child_name in blueprint_map:
                children_entries.append(("existing", child_name))
            else:
                children_entries.append(("missing", child_name))

        for idx, (kind, child_name) in enumerate(children_entries):
            last_child = idx == len(children_entries) - 1
            if kind == "missing":
                connector = "└─ " if last_child else "├─ "
                prefix_to_use = child_prefix if not is_root else ""
                print(f"{prefix_to_use}{connector}[missing] {child_name}")
            else:
                next_prefix = child_prefix if not is_root else ""
                render(child_name, next_prefix, last_child, False, visited)

    render(root_name, "", True, True, set())
