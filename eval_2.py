#!/usr/bin/env python3
"""
Refactored Evaluation Script for Agent Sandbox (Tau2 Compatible).
Supports:
1. Config-driven execution (resolves paths from yaml).
2. Robust Environment Hashing (CWD switching, file/dir hashing).
3. Hybrid Verification (Archive-based fast check & Re-execution).
"""

import argparse
import hashlib
import json
import os
import shutil
import glob
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

# Imports from project structure
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Utils.benchmark_utils import load_benchmark_tasks
from Utils.config_utils import read_config
from Utils.environment_utils import (
    build_task_objective,
    get_task_environment_resources,
    set_global_environment_context,
    normalize_environment_config,
)
from Utils.tool_utils import load_tools
# Import DataClean for log normalization
try:
    from Evaluation.DataClean import extract_memory_fields
except ImportError:
    # Fallback if running from a different root
    sys.path.append(os.path.join(os.path.dirname(__file__), "Evaluation"))
    from DataClean import extract_memory_fields

# =============================================================================
#  Hashing & File System Utilities
# =============================================================================

class HashCompute:
    @staticmethod
    def file_hash(file_path: Path) -> str:
        """Compute SHA256 of a single file."""
        if not file_path.exists() or not file_path.is_file():
            return ""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                hasher.update(f.read())
        except Exception as e:
            # Handle locking or permission issues gracefully
            return f"error:{str(e)}"
        return hasher.hexdigest()

    @staticmethod
    def directory_hash(dir_path: Path) -> str:
        """Compute SHA256 of a directory structure and contents."""
        hasher = hashlib.sha256()
        # Sort to ensure deterministic order
        for file_path in sorted(dir_path.rglob("*")):
            if file_path.is_file():
                # Hash relative path to track structural changes
                rel_path = str(file_path.relative_to(dir_path)).encode()
                hasher.update(rel_path)
                hasher.update(HashCompute.file_hash(file_path).encode())
        return hasher.hexdigest()

    @staticmethod
    def compute_active_env_hash(env_resources: List[Dict[str, Any]]) -> str:
        """Hash the ACTIVE environment state based on resource paths."""
        master_hasher = hashlib.sha256()
        for res in sorted(env_resources, key=lambda x: x.get("label", "")):
            path_str = res.get("path")
            if not path_str: continue
            
            p = Path(path_str)
            if p.exists():
                if p.is_file():
                    master_hasher.update(HashCompute.file_hash(p).encode())
                elif p.is_dir():
                    master_hasher.update(HashCompute.directory_hash(p).encode())
            else:
                master_hasher.update(f"missing:{path_str}".encode())
        return master_hasher.hexdigest()

    @staticmethod
    def compute_archive_hash(env_resources: List[Dict[str, Any]], archive_layout: Dict[str, Any]) -> str:
        """Hash using ARCHIVED files (Fast Path)."""
        master_hasher = hashlib.sha256()
        
        # Map label -> archive path
        label_map = {}
        for item in archive_layout.get("resources", []):
            if "label" in item and "archive_path" in item:
                label_map[item["label"]] = item["archive_path"]

        sorted_resources = sorted(env_resources, key=lambda x: x.get("label", ""))
        
        for res in sorted_resources:
            label = res.get("label")
            archive_path = label_map.get(label)
            
            # Fallback: filename match
            if not archive_path and res.get("path"):
                fname = Path(res["path"]).name
                for item in archive_layout.get("resources", []):
                    if Path(item.get("source_path", "")).name == fname:
                        archive_path = item.get("archive_path")
                        break
            
            if archive_path and os.path.exists(archive_path):
                p = Path(archive_path)
                if p.is_file():
                    master_hasher.update(HashCompute.file_hash(p).encode())
                elif p.is_dir():
                    master_hasher.update(HashCompute.directory_hash(p).encode())
            else:
                # If required resource missing in archive -> distinct hash state
                master_hasher.update(f"missing_archive:{label}".encode())
                
        return master_hasher.hexdigest()

# =============================================================================
#  Tool Execution Sandbox
# =============================================================================

class EnvironmentExecutor:
    """Executes agent actions within the correct global/CWD context."""
    
    def __init__(self, tool_map: Dict[str, Any]):
        self.tool_map = tool_map
        self.exec_globals = self._prepare_globals()

    def _prepare_globals(self) -> Dict[str, Any]:
        """Injects standard libraries and tools into execution scope."""
        import math, re, json, random, datetime, sqlite3, os, traceback
        import pandas as pd
        
        g = {
            "math": math, "re": re, "json": json,
            "random": random, "datetime": datetime,
            "pd": pd, "pandas": pd, "sqlite3": sqlite3, "os": os,
            "traceback": traceback
        }
        
        # Inject tool instances
        for name, tool in self.tool_map.items():
            g[name] = tool
            # Support smolagents tool.name attribute
            if hasattr(tool, 'name') and tool.name:
                g[tool.name] = tool
        return g

    def execute(self, actions: List[str], env_resources: List[Dict[str, Any]]) -> Tuple[bool, str, str]:
        """
        Execute a sequence of Python actions.
        Returns: (success, state_hash, error_msg)
        """
        # Baseline state (no actions)
        if not actions:
            current_hash = HashCompute.compute_active_env_hash(env_resources)
            return True, current_hash, ""

        # Determine Context Directory
        original_cwd = os.getcwd()
        work_dir = original_cwd
        
        # Find directory containing resources (e.g. where the sqlite db is)
        for res in env_resources:
            p = Path(res.get("path", ""))
            if p.exists():
                work_dir = str(p.parent) if p.is_file() else str(p)
                break
        
        try:
            # Switch CWD so actions like `sqlite3.connect('db.sqlite')` work
            if work_dir != original_cwd:
                os.chdir(work_dir)
                
            for action in actions:
                code = self._clean_code(action)
                if not code: continue
                # Danger: executing code. Sandbox implied by environment.
                exec(code, self.exec_globals)
            
            # Compute final state
            final_hash = HashCompute.compute_active_env_hash(env_resources)
            return True, final_hash, ""
        except Exception as e:
            # Capture error details
            return False, "", f"{type(e).__name__}: {str(e)}"
        finally:
            if os.getcwd() != original_cwd:
                os.chdir(original_cwd)

    @staticmethod
    def _clean_code(text: str) -> str:
        text = text.strip()
        if text.startswith("```python"): text = text[9:]
        elif text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        return text.strip()

# =============================================================================
#  Evaluation Core
# =============================================================================

def manage_backups(resources: List[Dict[str, Any]], mode: str) -> Dict[str, str]:
    """Simple resource backup/restore logic."""
    backups = {}
    if mode == "backup":
        for res in resources:
            src = res.get("path")
            if src and os.path.exists(src):
                p = Path(src)
                bak = p.with_suffix(p.suffix + ".bak_eval")
                try:
                    if p.is_dir():
                        if bak.exists(): shutil.rmtree(bak)
                        shutil.copytree(p, bak)
                    else:
                        shutil.copy2(p, bak)
                    backups[str(p)] = str(bak)
                except Exception: pass
        return backups
    return {}

def restore_backups(backups: Dict[str, str]):
    for src, bak in backups.items():
        if os.path.exists(bak):
            try:
                if os.path.isdir(src):
                    if os.path.exists(src): shutil.rmtree(src)
                    shutil.copytree(bak, src)
                else:
                    if os.path.exists(src): os.remove(src)
                    shutil.copy2(bak, src)
            except Exception: pass

def cleanup_backups(backups: Dict[str, str]):
    for bak in backups.values():
        if os.path.exists(bak):
            try:
                if os.path.isdir(bak): shutil.rmtree(bak)
                else: os.remove(bak)
            except Exception: pass

def extract_actions_from_log(clean_log: Dict[str, Any]) -> List[str]:
    """Reconstruct executable python code from tool calls."""
    actions = []
    # 1. Prefer explicitly logged 'actions' if available (e.g. CodeAgent)
    # actions_field = clean_log.get("actions", [])
    # if actions_field: return actions_field
    
    # 2. Reconstruct from tool_calls
    tool_calls = clean_log.get("tool_calls_all", [])
    for tc in tool_calls:
        if isinstance(tc, str):
            actions.append(tc)
        elif isinstance(tc, dict):
            # Format: func(arg=val)
            func = tc.get("function", {})
            name = func.get("name")
            args = func.get("arguments", {})
            if isinstance(args, str):
                try: args = json.loads(args)
                except: pass
            
            if name:
                args_str = ", ".join([f"{k}={repr(v)}" for k, v in args.items()])
                actions.append(f"{name}({args_str})")
    return actions

def evaluate_single_task(
    task_def: Dict[str, Any],
    log_entry: Dict[str, Any],
    executor: EnvironmentExecutor,
    environment_context: Dict[str, Any]
) -> Dict[str, Any]:
    
    # Clean log data
    clean_log = extract_memory_fields(log_entry)
    
    # Setup environment
    # This sets _current_task_environment in utils
    build_task_objective(task_def, environment_context)
    current_resources = get_task_environment_resources()
    
    # Prepare comparison inputs
    gold_actions = task_def.get("actions", [])
    actual_actions = extract_actions_from_log(clean_log)
    
    # Check for archive mode availability
    log_archive = clean_log.get("environment_archive", {})
    has_archive = bool(log_archive.get("resources"))
    
    result = {
        "task_id": clean_log.get("outer_task_id", 0),
        "score": 0.0,
        "match": False,
        "gold_hash": "",
        "actual_hash": "",
        "error": "",
        "eval_method": "archive" if has_archive else "re-execute"
    }

    # Backup safe state
    backups = manage_backups(current_resources, "backup")
    
    try:
        # 1. Execute Gold Actions (to get Target Hash)
        g_ok, g_hash, g_err = executor.execute(gold_actions, current_resources)
        if not g_ok:
            result["error"] = f"Gold Action Error: {g_err}"
            return result
        result["gold_hash"] = g_hash
        
        # 2. Get Agent State Hash
        if has_archive:
            # Fast path: compute hash from archived files recorded in log
            a_hash = HashCompute.compute_archive_hash(current_resources, log_archive)
            result["actual_hash"] = a_hash
        else:
            # Slow path: Re-run agent actions
            # Must restore clean state first!
            restore_backups(backups)
            a_ok, a_hash, a_err = executor.execute(actual_actions, current_resources)
            if not a_ok:
                result["error"] += f" | Agent Re-exec Error: {a_err}"
            result["actual_hash"] = a_hash

        # 3. Compare
        # Handling Empty Hash: if environment has no files, hash might be empty sha256
        # We ensure direct string comparison
        result["match"] = (result["gold_hash"] == result["actual_hash"])
        result["score"] = 1.0 if result["match"] else 0.0

    except Exception as e:
        result["error"] += f" | Critical Eval Error: {str(e)}"
        traceback.print_exc()
    finally:
        # Always leave environment clean
        restore_backups(backups)
        cleanup_backups(backups)
        
    return result

# =============================================================================
#  Main CLI & Orchestration
# =============================================================================

def find_latest_log_file(log_dir: str) -> Optional[Path]:
    """Find the most specific recent jsonl log file in directory."""
    p = Path(log_dir)
    if not p.exists(): return None
    
    files = list(p.glob("*.jsonl"))
    # Filter out result files to avoid circular dependency
    candidates = [f for f in files if "result" not in f.name.lower()]
    if not candidates: return None
    
    # Sort by modification time
    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return candidates[0]

def main():
    parser = argparse.ArgumentParser(description="Evaluate Agent Sandbox Results")
    parser.add_argument("--config", default="eval_config.yaml", help="Path to config file")
    parser.add_argument("--logs", required=False, help="Path to logs jsonl. Optional if in config.")
    parser.add_argument("--output", help="Output path. Defaults to Evaluation dir in config.")
    args = parser.parse_args()

    # 1. Load Config
    print(f"Loading config from {args.config}...")
    config = read_config(args.config)
    
    # 2. Resolve Logs Path
    log_path = None
    if args.logs:
        log_path = Path(args.logs)
    else:
        # Try finding in Result.log_dir
        res_cfg = config.get("Result", {})
        log_dir = res_cfg.get("log_dir")
        if log_dir:
            found = find_latest_log_file(log_dir)
            if found:
                print(f"Auto-detected latest log file: {found}")
                log_path = found
    
    if not log_path or not log_path.exists():
        print("Error: Could not resolve log file path. Provide --logs or check Result.log_dir in config.")
        sys.exit(1)

    # 3. Resolve Output Path
    out_path = Path(args.output) if args.output else None
    if not out_path:
        eval_cfg = config.get("Evaluation", {})
        save_dir = eval_cfg.get("save_dir", ".")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"eval_results_{timestamp}.jsonl"
        
        os.makedirs(save_dir, exist_ok=True)
        out_path = Path(save_dir) / out_name

    # 4. Initialize Components
    print("Initializing Environment...")
    env_config = normalize_environment_config(config, Path(".").resolve())
    set_global_environment_context(env_config)
    
    print("Loading Tools...")
    tools = load_tools(config)
    tool_map = {t.name: t for t in tools}
    executor = EnvironmentExecutor(tool_map)
    
    print("Loading Benchmarks...")
    tasks = load_benchmark_tasks(config)
    # Map by ID (stringified)
    task_map = {str(t.get("task_id") or t.get("id", "")): t for t in tasks}

    # 5. Execution Loop
    results = []
    print(f"Processing {log_path}...")
    
    with open(log_path, "r", encoding="utf-8") as f:
        total = 0
        matches = 0
        for line in f:
            if not line.strip(): continue
            try:
                log_item = json.loads(line)
                
                # Extract task ID safely
                # Could be nested or direct
                tid = str(log_item.get("task_id") or log_item.get("outer_task_id", ""))
                # If DataClean hasn't run, might need extraction
                if not tid and "task" in log_item:
                    tid = str(log_item.get("task", {}).get("task_id", ""))
                
                task_def = task_map.get(tid)
                if not task_def:
                    # Try heuristic integer match
                    try:
                        tid_int = str(int(float(tid)))
                        task_def = task_map.get(tid_int)
                    except: pass
                
                if not task_def:
                    print(f"Skipping Task ID {tid}: Not found in benchmark definitions.")
                    continue
                
                print(f"Evaluating Task {tid}...", end="\r")
                res = evaluate_single_task(task_def, log_item, executor, env_config)
                results.append(res)
                total += 1
                if res["match"]: matches += 1
                
            except Exception as e:
                print(f"\nError processing line: {e}")

    # 6. Save & Summary
    print(f"\nWriting results to {out_path}...")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            
    accuracy = (matches / total * 100) if total > 0 else 0
    print("-" * 40)
    print(f"Evaluation Complete.")
    print(f"Total Tasks: {total}")
    print(f"Exact Matches: {matches}")
    print(f"Accuracy: {accuracy:.2f}%")
    print("-" * 40)

if __name__ == "__main__":
    main()
