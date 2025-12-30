from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import atexit
import shutil
import tempfile

_global_environment_context: Dict[str, Any] = {}
_current_task_environment: Dict[str, Any] = {"resources": []}
_tracked_temp_dirs: set[str] = set()
_RESOURCE_LABEL_PRIORITY = (
    "database_path_abs",
    "database_path",
    "environment_path",
    "env_path",
)
_GENERIC_LABEL_PREFIXES = (
    "environment_path",
    "env_path",
    "environment_paths",
    "env_paths",
    "environment",
    "environments",
    "database_path",
    "database_paths",
    "database",
    "databases",
)

_FILENAME_LABEL_MAP = {
    "database.sqlite": "database",
    "database.db": "database",
    "init.sql": "init_sql",
    "ops_log.jsonl": "ops_log",
    "db_metrics.jsonl": "db_metrics",
    "trace_log.jsonl": "trace_log",
    "execution_summary.json": "execution_summary",
}


        
def _derive_label_from_path(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path_obj = Path(path_value)
    parts = [part.lower() for part in path_obj.parts]
    for idx, part in enumerate(parts):
        if part.endswith("bench"):
            prefix = part[:-5] or part
            if idx + 1 < len(parts):
                domain = parts[idx + 1]
                suffix = parts[-1]
                return f"{prefix}_{domain}_{suffix}"
    return None


def _maybe_relabeled_resource(entry: Dict[str, str]) -> Dict[str, str]:
    """If the entry label is generic, derive one from the filename."""
    path_value = entry.get("path")
    original_path = entry.get("original_path") or path_value
    if not path_value and not original_path:
        return entry

    name = Path(original_path or path_value).name.lower()
    label = _FILENAME_LABEL_MAP.get(name)
    if not label and name.endswith((".db", ".sqlite", ".sqlite3")):
        label = "database"

    current_label = entry.get("label")
    is_generic = not current_label or any(current_label.lower().startswith(prefix) for prefix in _GENERIC_LABEL_PREFIXES)

    if label and is_generic:
        entry["label"] = label
        return entry

    derived = _derive_label_from_path(original_path)
    if derived and is_generic:
        entry["label"] = derived

    return entry


def _cleanup_temp_directories() -> None:
    while _tracked_temp_dirs:
        temp_dir = _tracked_temp_dirs.pop()
        shutil.rmtree(temp_dir, ignore_errors=True)


atexit.register(_cleanup_temp_directories)


def normalize_environment_config(config: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Normalize environment configuration."""
    env_config = config.get("Environment") or {}
    if not env_config:
        return {
            "type": "none",
            "raw_type": None,
            "path_raw": None,
            "base_path": None,
            "repo_root": repo_root.resolve(),
        }
    raw_type = env_config.get("type", "global")
    normalized_type = (
        str(raw_type).strip().lower().replace("_", "-") if raw_type is not None else "global"
    )

    type_aliases = {
        "global": "global",
        "all": "global",
        "full": "global",
        "per-task": "per-task",
        "per task": "per-task",
        "pertask": "per-task",
        "per-benchmark": "per-task",
        "perbenchmark": "per-task",
        "benchmark": "per-task",
        "by-benchmark": "per-task",
        "none": "none",
        "null": "none",
    }
    
    env_type = type_aliases.get(normalized_type, "global")
    if env_type != normalized_type and normalized_type not in type_aliases:
        print(f"Warning: Unknown Environment.type '{raw_type}', defaulting to 'global'.")
    # Get the path of the environment
    path_raw = env_config.get("path", "./Environment")
    path_candidate: Path | None
    if env_type == "none":
        path_candidate = None
    else:
        path_candidate = Path(path_raw)
        if not path_candidate.is_absolute():
            path_candidate = (repo_root / path_candidate).resolve()
        else:
            path_candidate = path_candidate.resolve()

        if not path_candidate.exists() and path_raw is not None:
            print(f"Warning: Environment path {path_candidate} does not exist.")

    return {
        "type": env_type,
        "raw_type": raw_type,
        "path_raw": path_raw,
        "base_path": path_candidate,
        "repo_root": repo_root.resolve(),
    }


def set_global_environment_context(context: Dict[str, Any]) -> None:
    """Store normalized environment context for global access."""
    _global_environment_context.clear()
    _global_environment_context.update(context)


def get_global_environment_context() -> Dict[str, Any]:
    """Retrieve the normalized global environment context."""
    return dict(_global_environment_context)


def set_task_environment_resources(resources: List[Dict[str, str]]) -> None:
    """Register the resources associated with the current task."""
    _cleanup_previous_task_resources()
    working_resources = _prepare_resource_copies(resources)
    _current_task_environment["resources"] = working_resources


def _cleanup_previous_task_resources() -> None:
    temp_dir = _current_task_environment.get("temp_dir")
    if temp_dir:
        shutil.rmtree(temp_dir, ignore_errors=True)
        _tracked_temp_dirs.discard(temp_dir)
    _current_task_environment["resources"] = []
    _current_task_environment.pop("temp_dir", None)


def _prepare_resource_copies(resources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if not resources:
        return []

    temp_dir = Path(tempfile.mkdtemp(prefix="env_resources_"))
    _tracked_temp_dirs.add(str(temp_dir))
    prepared_resources: List[Dict[str, str]] = []

    for idx, entry in enumerate(resources, start=1):
        if not isinstance(entry, dict):
            continue

        path_value = entry.get("path")
        if not path_value:
            prepared_resources.append(_maybe_relabeled_resource(dict(entry)))
            continue

        source_path = Path(path_value)
        if not source_path.exists():
            prepared_resources.append(_maybe_relabeled_resource(dict(entry)))
            continue

        destination_name = f"{idx}_{source_path.name}"
        destination_path = temp_dir / destination_name

        try:
            if source_path.is_file():
                shutil.copy2(source_path, destination_path)
            elif source_path.is_dir():
                shutil.copytree(source_path, destination_path)
            else:
                prepared_resources.append(_maybe_relabeled_resource(dict(entry)))
                continue
        except Exception:
            prepared_resources.append(_maybe_relabeled_resource(dict(entry)))
            continue

        cloned_entry = dict(entry)
        cloned_entry["path"] = str(destination_path.resolve())
        cloned_entry["original_path"] = str(source_path.resolve())
        prepared_resources.append(_maybe_relabeled_resource(cloned_entry))

    _current_task_environment["temp_dir"] = str(temp_dir)
    return prepared_resources


def get_task_environment_resources() -> List[Dict[str, str]]:
    """Return the resources registered for the current task."""
    return list(_current_task_environment.get("resources", []))


def find_environment_resource(
    *,
    label: Optional[str] = None,
    suffix: Optional[str] = None,
) -> Optional[str]:
    """
    Locate a registered environment resource by label or suffix.

    Args:
        label: Exact label to match (case-sensitive).
        suffix: File suffix that the resource path should end with.
    """
    resources = get_task_environment_resources()

    for resource in resources:
        path = resource.get("path")
        resource_label = resource.get("label")
        if not path:
            continue

        if label is not None and resource_label == label:
            return path
        if suffix is not None and path.endswith(suffix):
            return path

    return None


def _slugify_value(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("._-")
    return slug or "resource"


def archive_environment_resources(
    resources: List[Dict[str, str]],
    base_dir: str | Path,
    *,
    task_identifier: Any,
) -> Optional[Dict[str, Any]]:
    """
    Persist copies of environment resources and optionally produce an archive snapshot.

    Args:
        resources: List of resource dictionaries with at least a 'path' field.
        base_dir: Destination directory where task subdirectories will be created.
        task_identifier: String/number used to separate task archives.
        snapshot_mode: 'path' to reference archive file path, 'inline' to embed base64 data.
    """
    if not resources or not base_dir:
        return None

    base_path = Path(base_dir).expanduser().resolve()
    base_path.mkdir(parents=True, exist_ok=True)

    task_slug = _slugify_value(str(task_identifier))
    task_dir = base_path / f"task_{task_slug}"
    task_dir.mkdir(parents=True, exist_ok=True)

    archived_entries: List[Dict[str, str]] = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        source_str = resource.get("path")
        if not source_str:
            continue
        source_path = Path(source_str)
        if not source_path.exists():
            continue

        label = resource.get("label") or source_path.name
        filename_hint = _slugify_value(label) or source_path.name
        destination_path = task_dir / filename_hint
        suffix = 1
        while destination_path.exists():
            destination_path = task_dir / f"{filename_hint}_{suffix}"
            suffix += 1

        try:
            if source_path.is_file():
                shutil.copy2(source_path, destination_path)
            elif source_path.is_dir():
                shutil.copytree(source_path, destination_path)
            else:
                continue
        except Exception as exc:  # pragma: no cover - best effort archival
            print(f"Warning: Failed to archive environment resource {source_path}: {exc}")
            continue

        archived_entries.append(
            {
                "label": label,
                "source_path": str(source_path.resolve()),
                "archive_path": str(destination_path.resolve()),
            }
        )

    if not archived_entries:
        return None

    return {
        "task_dir": str(task_dir),
        "resources": archived_entries,
    }


def get_primary_database_path() -> Optional[str]:
    """
    Determine the primary database path for the current task based on registered resources.
    Preference order:
        1. Resources whose label matches a known database label.
        2. The first resource whose path ends with '.db'.
    """
    resources = get_task_environment_resources()

    for preferred_label in _RESOURCE_LABEL_PRIORITY:
        for resource in resources:
            path = resource.get("path")
            if not path:
                continue
            if resource.get("label") == preferred_label and path.endswith(".db"):
                return path

    for resource in resources:
        path = resource.get("path")
        if path and path.endswith(".db"):
            return path

    return None


def _resolve_path_string(path_str: str, environment_context: Dict[str, Any]) -> str:
    """Resolve a possibly-relative path to an absolute path."""
    path_str = path_str.strip()
    if not path_str:
        return ""

    if os.path.isabs(path_str):
        return os.path.abspath(path_str)

    repo_root = environment_context.get("repo_root")
    base_path = environment_context.get("base_path")

    candidates = []
    if repo_root:
        candidates.append(repo_root / path_str)
    if base_path and base_path not in candidates:
        candidates.append(base_path / path_str)

    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate.exists():
            return str(candidate)

    # Fall back to first candidate even if it doesn't exist
    if candidates:
        return str(candidates[0].resolve())

    return os.path.abspath(path_str)


def _resolve_path_from_value(value: Any, environment_context: Dict[str, Any]) -> str:
    """Extract and resolve a path from various value formats."""
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("path", "location", "file"):
            if key in value and isinstance(value[key], str):
                return _resolve_path_string(value[key], environment_context)
        return ""
    if isinstance(value, str):
        return _resolve_path_string(value, environment_context)
    return ""


def _deduplicate_resources(resources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped = []
    for entry in resources:
        path_value = entry.get("path")
        if not path_value:
            continue
        if path_value in seen:
            continue
        seen.add(path_value)
        deduped.append(entry)
    return deduped


def _load_global_environment_resources(environment_context: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Load all environment resources in global mode.
    Scans the environment base path for database files and other resources.
    """
    base_path = environment_context.get("base_path")
    if not base_path:
        return []
    
    base_path = Path(base_path)
    if not base_path.exists() or not base_path.is_dir():
        return []
    
    resources: List[Dict[str, str]] = []
    
    # Add the root directory as a resource
    resources.append({"label": "global_environment_root", "path": str(base_path)})
    
    # Scan for database files (.db, .sqlite, .sqlite3)
    db_extensions = [".db", ".sqlite", ".sqlite3"]
    for ext in db_extensions:
        for db_file in base_path.glob(f"*{ext}"):
            if db_file.is_file():
                # Use the filename (without extension) as the label
                label = f"database_{db_file.stem}"
                resources.append({"label": label, "path": str(db_file.resolve())})
    
    # Scan for other common resource files
    resource_extensions = [".json", ".yaml", ".yml", ".csv", ".txt"]
    for ext in resource_extensions:
        for resource_file in base_path.glob(f"*{ext}"):
            if resource_file.is_file():
                label = f"resource_{resource_file.stem}"
                resources.append({"label": label, "path": str(resource_file.resolve())})
    
    return _deduplicate_resources(resources)


def extract_task_environment_resources(
    task: Dict[str, Any], environment_context: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Extract environment resources for a single task when running in per-task mode."""
    if environment_context.get("type") != "per-task":
        return []
    benchmark_name = environment_context.get("benchmark_name", "")
    if benchmark_name.lower() == "tau2-bench":
        # Import Tau2Bench adapter
        try:
            from Utils.tau2_bench_adapter import get_tau2_environment_resources
            tau2_resources = get_tau2_environment_resources(task)
            # Resolve relative paths
            resolved_resources = []
            for resource in tau2_resources:
                path_str = resource.get("path", "")
                if path_str:
                    resolved_path = _resolve_path_string(path_str, environment_context)
                    resolved_resources.append({
                        "label": resource.get("label", ""),
                        "path": resolved_path
                    })
            return _deduplicate_resources(resolved_resources)
        except ImportError:
            pass

    candidate_keys = [
        "environment_path",
        "env_path",
        "environment_paths",
        "env_paths",
        "environment",
        "environments",
        "database_path",
        "database_paths",
        "database_path_abs",
        "database",
        "databases",
    ]

    resources: List[Dict[str, str]] = []

    for key in candidate_keys:
        if key not in task:
            continue

        value = task[key]
        if isinstance(value, list):
            for idx, item in enumerate(value, start=1):
                resolved = _resolve_path_from_value(item, environment_context)
                if resolved:
                    entry = {"label": f"{key}[{idx}]", "path": resolved}
                    resources.append(_maybe_relabeled_resource(entry))
        else:
            resolved = _resolve_path_from_value(value, environment_context)
            if resolved:
                entry = {"label": key, "path": resolved}
                resources.append(_maybe_relabeled_resource(entry))

    return _deduplicate_resources(resources)


def build_task_objective(
    task: Dict[str, Any], environment_context: Dict[str, Any]
) -> Tuple[str, List[Dict[str, str]]]:
    """Compose the objective string for the agent, enriched with environment information."""
    description_raw = task.get("description") or task.get("task") or task.get("instruction") or str(task)
    if isinstance(description_raw, list):
        description = "\n".join([str(item) for item in description_raw])
    else:
        description = str(description_raw)
    resources: List[Dict[str, str]] = []

    if environment_context.get("type") == "global":
        resources = _load_global_environment_resources(environment_context)
    else:
        resources = extract_task_environment_resources(task, environment_context)

    return description, resources
