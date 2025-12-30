from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, List, Optional

from smolagents import Tool, WebSearchTool

TOOL_IMPORT_LOG = Path("tool_import_error_log.jsonl")


def load_tools(config: Dict[str, Any]) -> List[Tool]:
    """
    Load tool instances according to the Toolkit configuration.

    Priority:
        1. Custom loader script (Toolkit.loader).
        2. Dynamically scanned directories (Toolkit.scan_dirs / Toolkit.generated_dir).
        3. Default fallback tools.
    """
    toolkit_config = config.get("Toolkit", {})
    toolkit_path = Path(toolkit_config.get("path", "./Toolkit")).expanduser()

    collected_tools: List[Tool] = []

    collected_tools.extend(
        _load_tools_from_loader(
            toolkit_config.get("loader"),
            default_path=toolkit_path / "load_tools.py",
        )
    )
    collected_tools.extend(
        _load_tools_from_scan_targets(
            toolkit_config,
            toolkit_path,
        )
    )
    # Deduplicate by tool name to avoid duplicates when the same tool is loaded twice.
    unique_tools: Dict[str, Tool] = {}
    for tool in collected_tools:
        if not isinstance(tool, Tool):
            continue
        tool_name = getattr(tool, "name", tool.__class__.__name__)
        if tool_name not in unique_tools:
            unique_tools[tool_name] = tool

    if not unique_tools:
        print("Using default tools: WebSearchTool, BaseTool")
        return [WebSearchTool()]

    return list(unique_tools.values())


def load_grouped_tools(config: Dict[str, Any]) -> Dict[str, Dict[str, Tool]]:
    """
    Load tools grouped by subdirectory name (e.g., BFCL per-JSON folders).

    Looks under the directory specified by Toolkit.path (or generated_dir if set),
    and returns a mapping of {group_name: {tool_name: Tool}}.
    """
    toolkit_config = config.get("Toolkit", {})
    toolkit_path = Path(toolkit_config.get("path", "./Toolkit")).expanduser()
    base_dir = Path(toolkit_config.get("generated_dir") or toolkit_path)

    grouped: Dict[str, Dict[str, Tool]] = {}

    if base_dir.is_dir():
        for subdir in sorted(base_dir.iterdir()):
            if not subdir.is_dir() or subdir.name.startswith("__"):
                continue
            tool_map = scan_and_import_tools(subdir, error_log=TOOL_IMPORT_LOG)
            if tool_map:
                grouped[subdir.name] = tool_map
    # If no subfolders matched, but the base dir itself has tools, treat it as one group.
    if not grouped and base_dir.is_dir():
        tool_map = scan_and_import_tools(base_dir, error_log=TOOL_IMPORT_LOG)
        if tool_map:
            grouped[base_dir.name] = tool_map

    return grouped


def scan_and_import_tools(
    root_dir: str | Path,
    *,
    recursive: bool = True,
    error_log: Optional[Path] = None,
) -> Dict[str, Tool]:
    """
    Scan a directory for Python files, import them, and collect Tool instances.

    Args:
        root_dir: Directory containing tool implementation files.
        recursive: Whether to scan subdirectories recursively.
        error_log: Optional path to append import errors (defaults to TOOL_IMPORT_LOG).

    Returns:
        Mapping of tool identifier to Tool instances.
    """
    root_path = Path(root_dir).expanduser().resolve()
    if not root_path.is_dir():
        print(f"Warning: Tools directory not found: {root_path}")
        return {}

    python_files = (
        root_path.rglob("*.py") if recursive else root_path.glob("*.py")
    )

    log_path = (error_log or TOOL_IMPORT_LOG).expanduser()

    discovered: Dict[str, Tool] = {}
    for py_file in python_files:
        if py_file.name.startswith("__"):
            continue
        if any(part.startswith("__") for part in py_file.parts):
            continue

        module = _import_module_from_path(py_file, error_log=log_path)
        if module is None:
            continue

        module_tools = _collect_tool_instances(module)
        for identifier, tool in module_tools.items():
            discovered[identifier] = tool

    if not discovered:
        print(f"Warning: No tools discovered under {root_path}")

    return discovered


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_tools_from_loader(
    loader: Optional[str | Path], *, default_path: Path
) -> List[Tool]:
    loader_path = Path(loader).expanduser() if loader else default_path

    if not loader_path.exists():
        return []

    try:
        spec = importlib.util.spec_from_file_location("toolkit_loader", loader_path)
        if spec is None or spec.loader is None:
            print(f"Warning: Unable to load toolkit loader from {loader_path}")
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        load_func = getattr(module, "load_tools", None)
        if load_func is None:
            print(f"Warning: load_tools function not found in {loader_path}")
            return []

        return _normalize_tools_iterable(load_func())

    except Exception as exc:
        print(f"Warning: Error loading tools via loader {loader_path}: {exc}")
        _log_import_error(loader_path, exc, TOOL_IMPORT_LOG)
        return []


def _load_tools_from_scan_targets(
    toolkit_config: Dict[str, Any], toolkit_path: Path
) -> List[Tool]:
    scan_targets: List[Path] = []

    configured_scan_dirs = toolkit_config.get("scan_dirs")
    if isinstance(configured_scan_dirs, str):
        scan_targets.append(Path(configured_scan_dirs))
    elif isinstance(configured_scan_dirs, Iterable):
        scan_targets.extend(Path(p) for p in configured_scan_dirs if isinstance(p, str))

    generated_dir = toolkit_config.get("generated_dir")
    if isinstance(generated_dir, str):
        scan_targets.append(Path(generated_dir))

    # Always include the toolkit root (recursively import every .py file).
    scan_targets.append(toolkit_path)

    # Add common defaults if they exist
    default_candidates = [
        toolkit_path / "generated_tools",
        toolkit_path / "generated",
        Path("generated_tools_poinsed"),
    ]
    for candidate in default_candidates:
        if candidate.is_dir():
            scan_targets.append(candidate)

    collected: List[Tool] = []
    seen_directories: set[Path] = set()
    for directory in scan_targets:
        directory_path = Path(directory).expanduser()
        if directory_path in seen_directories:
            continue
        seen_directories.add(directory_path)

        tool_map = scan_and_import_tools(directory_path, error_log=TOOL_IMPORT_LOG)
        collected.extend(tool_map.values())

    return collected


def _normalize_tools_iterable(candidate: Any) -> List[Tool]:
    if candidate is None:
        return []
    if isinstance(candidate, Tool):
        return [candidate]
    if isinstance(candidate, dict):
        return [tool for tool in candidate.values() if isinstance(tool, Tool)]
    if isinstance(candidate, Iterable):
        return [tool for tool in candidate if isinstance(tool, Tool)]

    print("Warning: Unsupported tool collection format from loader")
    return []


def _import_module_from_path(py_file: Path, *, error_log: Path) -> Optional[ModuleType]:
    try:
        module_name = _derive_module_name(py_file)
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            print(f"Warning: Unable to create spec for {py_file}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module

    except Exception as exc:
        print(f"[ERROR] Import failed for {py_file}: {exc}")
        _log_import_error(py_file, exc, error_log)
        return None


def _collect_tool_instances(module: ModuleType) -> Dict[str, Tool]:
    tools: Dict[str, Tool] = {}
    for attr_name, obj in inspect.getmembers(module):
        if isinstance(obj, Tool):
            identifier = getattr(obj, "name", attr_name)
            tools[identifier] = obj
    return tools


def _derive_module_name(py_file: Path) -> str:
    try:
        relative_path = py_file.resolve().relative_to(Path.cwd())
    except ValueError:
        relative_path = py_file.resolve()

    parts = relative_path.with_suffix("").parts
    sanitized_parts = [
        part.replace("-", "_")
        for part in parts
        if part not in ("", os.sep)
    ]
    hashed_suffix = hex(abs(hash(py_file)) & 0xFFFF)[2:]
    return ".".join(["dynamic_tools", *sanitized_parts, hashed_suffix])


def _log_import_error(file_path: Path, exc: Exception, log_path: Path) -> None:
    error_record = {"file": str(file_path), "error": str(exc)}
    try:
        with open(log_path.expanduser(), "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(error_record, ensure_ascii=False) + "\n")
    except Exception as log_exc:
        print(f"Warning: Failed to write tool import log: {log_exc}")
