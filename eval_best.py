#!/usr/bin/env python3
"""
Evaluation script for benchmark results.
Supports label-based (LLM judge) and action-based (environment hash comparison) evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
import yaml

# Import existing utilities
from Utils.benchmark_utils import load_benchmark_tasks
from Utils.config_utils import read_config
from Utils.environment_utils import (
    build_task_objective,
    normalize_environment_config,
    set_global_environment_context,
    set_task_environment_resources,
)
from Utils.tool_utils import load_tools, scan_and_import_tools


def extract_memory_fields(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    核心清洗函数：提取所有核心memory字段，适配LLM评测的5大任务
    必提字段全保留：outer_task_id、inner_task_id、actions、label、timestamp
    空值标准化清洗，无统计逻辑，纯字段提取
    """
    memory = {}
    # ========== 【必提字段 优先级最高 完整保留】 ==========
    memory["outer_task_id"] = log_data.get("task_id", "")
    memory["inner_task_id"] = log_data.get("task", {}).get("task_id", "")
    memory["actions"] = log_data.get("task", {}).get("actions", [])
    
    # 获取label的更健壮方法
    memory["label"] = log_data.get("label", []) or log_data.get("task", {}).get("label", [])
    memory["timestamp"] = log_data.get("timestamp", "")

    # ========== 任务完成情况TS  ==========
    memory["status"] = log_data.get("status", "")
    memory["result"] = log_data.get("result", "")

    # ========== Step/Token/耗时 纯原始数据 ==========
    memory["step_count"] = log_data.get("step_count", 0)
    
    # 安全处理elapsed_seconds，确保是浮点数
    elapsed = log_data.get("elapsed_seconds", 0.0)
    memory["elapsed_seconds"] = round(float(elapsed) if elapsed is not None else 0.0, 4)
    
    # 安全处理token计数，避免None值
    memory["total_input_tokens"] = log_data.get("total_input_tokens", 0) or 0
    memory["total_output_tokens"] = log_data.get("total_output_tokens", 0) or 0
    memory["total_tokens"] = log_data.get("total_tokens", 0) or 0

    # ========== 原场景 & Sandbox 环境对比 专用字段 ==========
    task_info = log_data.get("task", {})
    memory["benchmark_suite"] = task_info.get("benchmark_suite", "")
    memory["domain"] = task_info.get("domain", "")
    memory["environment_paths"] = task_info.get("environment_paths", [])
    memory["_source_file"] = task_info.get("_source_file", "")
    memory["_dataset"] = task_info.get("_dataset", "")
    
    # 安全处理archive_info
    archive_info = log_data.get("environment_archive", {})
    memory["environment_archive"] = archive_info
    memory["archive_task_dir"] = archive_info.get("task_dir", "")
    
    # 安全处理resources
    memory["archive_resource_paths"] = []
    if archive_info and "resources" in archive_info:
        memory["archive_resource_paths"] = [
            res.get("archive_path", "") for res in archive_info.get("resources", [])
            if isinstance(res, dict)
        ]

    # ========== 失败原因统计学分析 专用字段 ==========
    memory["error"] = log_data.get("error", "") if log_data.get("error") is not None else ""

    # ========== 安全评测 & ASR适配能力测试 专用字段 ==========
    instruction = task_info.get("instruction", "")
    memory["user_info"] = {
        "user_id": task_info.get("user_id", ""),
        "name": "",
        "email": ""
    }
    
    # 安全提取姓名和邮箱
    if "You name is " in instruction:
        try:
            memory["user_info"]["name"] = instruction.split("You name is ")[1].split(" and")[0]
        except (IndexError, AttributeError):
            pass
    
    if "email is " in instruction:
        try:
            email_part = instruction.split("email is ")[1].split(".com")[0] + ".com"
            memory["user_info"]["email"] = email_part
        except (IndexError, AttributeError):
            pass
    
    memory["instruction"] = instruction
    
    # 安全提取模型名称 - 修复核心问题
    memory["model_name"] = ""
    steps = log_data.get("steps", [])
    if steps and isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
                
            # 安全地获取model_output_message
            model_output_message = step.get("model_output_message")
            if not model_output_message or not isinstance(model_output_message, dict):
                continue
                
            # 安全地获取raw
            raw = model_output_message.get("raw")
            if not raw or not isinstance(raw, dict):
                continue
                
            # 获取模型名称
            model = raw.get("model")
            if model:
                memory["model_name"] = model
                break
    
    # 提取所有工具调用记录
    memory["tool_calls_all"] = []
    
    # Check if tool_calls_all already exists in log_data
    if "tool_calls_all" in log_data and isinstance(log_data["tool_calls_all"], list):
        memory["tool_calls_all"].extend(log_data["tool_calls_all"])
    
    # Also try to extract from steps if available (and deduplicate if needed, or just append)
    if not memory["tool_calls_all"] and steps:
        for step in steps:
            if isinstance(step, dict):
                tool_calls = step.get("tool_calls", [])
                if isinstance(tool_calls, list):
                    memory["tool_calls_all"].extend(tool_calls)

    # 空值标准化清洗
    for k, v in memory.items():
        if v is None:
            if k in ["actions", "label", "environment_paths", "archive_resource_paths", "tool_calls_all"]:
                memory[k] = []
            else:
                memory[k] = ""
    
    return memory


def load_result_logs(log_dir: str) -> List[Dict[str, Any]]:
    """Load all result logs from the specified directory."""
    log_dir_path = Path(log_dir).expanduser()
    if not log_dir_path.exists():
        print(f"Warning: Log directory {log_dir_path} does not exist")
        return []
    
    all_logs = []
    for log_file in log_dir_path.glob("*.jsonl"):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        log_entry = json.loads(line)
                        all_logs.append(log_entry)
        except Exception as exc:
            print(f"Warning: Error loading log file {log_file}: {exc}")
    
    return all_logs


def clean_logs(logs: List[Dict[str, Any]], output_dir: str) -> str:
    """Clean logs using DataClean logic and save to output directory."""
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cleaned_file = output_path / f"cleaned_logs_{timestamp}.jsonl"
    
    cleaned_count = 0
    with open(cleaned_file, "w", encoding="utf-8") as f:
        for log in logs:
            try:
                cleaned = extract_memory_fields(log)
                f.write(json.dumps(cleaned, ensure_ascii=False) + "\n")
                cleaned_count += 1
            except Exception as exc:
                print(f"Warning: Error cleaning log entry: {exc}")
    
    print(f"Cleaned {cleaned_count} log entries to: {cleaned_file}")
    return str(cleaned_file)


def call_llm_judge(
    instruction: str,
    response: str,
    labels: List[str],
    log_summary: str,
    llm_config: Dict[str, Any],
) -> Tuple[int, str]:
    """
    Call LLM judge to evaluate if the response is correct.
    
    Returns:
        (score, explanation) where score is 0 or 1
    """
    system_prompt = llm_config.get("system", "You are an impartial judge.")
    evaluate_template = llm_config.get("evaluate", "")
    
    # Format the evaluation prompt
    label_text = "\n".join(f"- {label}" for label in labels)
    evaluate_prompt = evaluate_template.format(
        instruction=instruction,
        lable=label_text,
        response=response,
        log=log_summary,
    )
    
    # Prepare API request
    api_base = llm_config.get("api_base", "").rstrip("/")
    api_key = llm_config.get("api_key", "")
    model_id = llm_config.get("model_id", "gpt-4")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": evaluate_prompt},
        ],
        "temperature": 0.0,
    }
    
    try:
        response_obj = requests.post(
            f"{api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response_obj.raise_for_status()
        result = response_obj.json()
        
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse JSON response
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
        
        parsed = json.loads(content)
        score = int(parsed.get("score", 0))
        explanation = parsed.get("explanation", "")
        
        return score, explanation
        
    except Exception as exc:
        print(f"Error calling LLM judge: {exc}")
        return 0, f"LLM judge error: {str(exc)}"


def compute_environment_hash(env_resources: List[Dict[str, Any]]) -> str:
    """Compute hash of environment state based on resources."""
    hasher = hashlib.sha256()
    
    for resource in sorted(env_resources, key=lambda x: x.get("label", "")):
        path = resource.get("path")
        if path and Path(path).exists():
            path_obj = Path(path)
            if path_obj.is_file():
                with open(path_obj, "rb") as f:
                    hasher.update(f.read())
            elif path_obj.is_dir():
                # Hash directory structure and file contents
                for file_path in sorted(path_obj.rglob("*")):
                    if file_path.is_file():
                        hasher.update(str(file_path.relative_to(path_obj)).encode())
                        with open(file_path, "rb") as f:
                            hasher.update(f.read())
    
    return hasher.hexdigest()


def execute_actions_in_environment(
    actions: List[str],
    tool_map: Dict[str, Any],
    environment_context: Dict[str, Any],
) -> Tuple[bool, str, str]:
    """
    Execute a list of actions in the environment and return the final hash.
    
    Returns:
        (success, final_hash, error_message)
    """
    # Create execution context with common libraries and tools
    exec_globals = {}
    
    # Add common libraries
    import math
    import re
    import json
    import random
    import datetime
    import pandas as pd
    import sqlite3
    import traceback
    
    exec_globals.update({
        "math": math,
        "re": re,
        "json": json,
        "random": random,
        "datetime": datetime,
        "pd": pd,
        "sqlite3": sqlite3,
        "os": os,
    })
    
    # Add tools to context
    for name, tool in tool_map.items():
        exec_globals[name] = tool
        # Also try to add tool by its class name or 'name' attribute if available
        if hasattr(tool, 'name'):
             exec_globals[tool.name] = tool

    # DYNAMIC CWD SWITCH: Find the directory where resources live
    from Utils.environment_utils import get_task_environment_resources
    env_resources = get_task_environment_resources()
    
    original_cwd = os.getcwd()
    work_dir = original_cwd
    
    # Heuristic: find the directory containing the first valid resource file
    if env_resources:
        for res in env_resources:
            p = res.get("path")
            if p:
                p_obj = Path(p)
                if p_obj.exists():
                    if p_obj.is_file():
                        work_dir = str(p_obj.parent)
                    else:
                        work_dir = str(p_obj)
                    break
    
    try:
        # Change CWD so tools running relative paths (e.g. 'database.db') find the right file
        if work_dir != original_cwd:
             os.chdir(work_dir)
             # print(f"DEBUG: Switched CWD to {work_dir}") 
        else:
             print(f"DEBUG: CWD not switched, staying in {original_cwd}. Work dir identified as {work_dir}")

        # Execute each action
        for action in actions:
            if not isinstance(action, str) or not action.strip():
                continue
            
            # Remove markdown code blocks if present
            clean_action = action.strip()
            if clean_action.startswith("```python"):
                clean_action = clean_action[9:]
            if clean_action.startswith("```"):
                clean_action = clean_action[3:]
            if clean_action.endswith("```"):
                clean_action = clean_action[:-3]
            
            # Execute the action code
            try:
                # We use exec to run the action (which is typically Python code)
                exec(clean_action, exec_globals)
            except Exception:
                tb = traceback.format_exc()
                # Restore CWD before returning
                if os.getcwd() != original_cwd:
                    os.chdir(original_cwd)
                # Try to extract the last line of the action for a shorter error summary
                summary = clean_action.split('\n')[-1] if clean_action else "Empty action"
                return False, "", f"Action failed: {summary}\nTraceback: {tb}"
        
        # Get environment resources and compute hash
        # Resources usually stay in the same place, so we just re-read them
        # Note: If tools created new files that are NOT in env_resources lookup, they won't be hashed.
        # But usually we track specific modified files.
        final_hash = compute_environment_hash(env_resources)
        
        return True, final_hash, ""
        
    except Exception as exc:
        return False, "", f"Execution Error: {str(exc)}"
    finally:
        # Always restore CWD
        if os.getcwd() != original_cwd:
            os.chdir(original_cwd)


def evaluate_label(
    task: Dict[str, Any],
    log: Dict[str, Any],
    llm_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate using LLM judge."""
    instruction = task.get("instruction") or task.get("description") or task.get("task", "")
    labels = task.get("label", [])
    if isinstance(labels, str):
        labels = [labels]
    
    # Get response from log
    response = log.get("result", "")
    
    # Create log summary
    steps = log.get("steps", [])
    log_summary = f"Steps: {len(steps)}\n"
    log_summary += f"Total tokens: {log.get('total_tokens', 0)}\n"
    
    # Extract tool calls from steps
    tool_calls = []
    for step in steps:
        if isinstance(step, dict):
            step_tools = step.get("tool_calls", [])
            tool_calls.extend(step_tools)
    
    if tool_calls:
        log_summary += f"Tool calls: {len(tool_calls)}\n"
        for i, tool_call in enumerate(tool_calls[:5], 1):  # Show first 5
            log_summary += f"  {i}. {tool_call}\n"
    
    score, explanation = call_llm_judge(
        instruction=instruction,
        response=response,
        labels=labels,
        log_summary=log_summary,
        llm_config=llm_config,
    )
    
    return {
        "type": "label",
        "score": score,
        "explanation": explanation,
        "llm_input": {
            "instruction": instruction,
            "response": response,
            "labels": labels,
            "log_summary": log_summary,
        },
    }


import shutil

def backup_resources(env_resources: List[Dict[str, Any]]) -> Dict[str, str]:
    """Backup environment resources to temporary locations."""
    backups = {}
    import tempfile
    
    for res in env_resources:
        path_str = res.get("path")
        if not path_str:
            continue
            
        path = Path(path_str)
        if not path.exists():
            continue
            
        # Create a temp backup
        if path.is_file():
            # Backup file
            fd, temp_path = tempfile.mkstemp(suffix=path.suffix)
            os.close(fd)
            shutil.copy2(path, temp_path)
            backups[str(path)] = temp_path
        elif path.is_dir():
            # Backup dir
            temp_dir = tempfile.mkdtemp(suffix="_bak")
            # Clear temp dir if exists (though mkdtemp creates a new one)
            # shutil.rmtree(temp_dir) 
            # We need to copy contents, mkdtemp creates an empty dir
            os.rmdir(temp_dir)
            shutil.copytree(path, temp_dir)
            backups[str(path)] = temp_dir
            
    return backups

def restore_resources(backups: Dict[str, str], keep_backup: bool = False):
    """Restore environment resources from backups."""
    for original_path_str, backup_path_str in backups.items():
        original_path = Path(original_path_str)
        backup_path = Path(backup_path_str)
        
        try:
            if backup_path.is_file():
                if original_path.exists():
                    os.remove(original_path)
                shutil.copy2(backup_path, original_path)
                if not keep_backup:
                    os.remove(backup_path) 
            elif backup_path.is_dir():
                if original_path.exists():
                    shutil.rmtree(original_path)
                shutil.copytree(backup_path, original_path)
                if not keep_backup:
                    shutil.rmtree(backup_path)
        except Exception as e:
            print(f"Error restoring {original_path}: {e}")

def format_tool_call(tool_call: Any) -> str:
    """Convert a tool call dictionary/object to a Python function call string."""
    try:
        # Handle dict (from JSON log)
        if isinstance(tool_call, dict):
            # Check for OpenAI format: {'type': 'function', 'function': {'name': ..., 'arguments': ...}}
            if "function" in tool_call and isinstance(tool_call["function"], dict):
                 info = tool_call["function"]
                 func_name = info.get("name")
                 args = info.get("arguments")
            else:
                 func_name = tool_call.get("name") or tool_call.get("tool_name")
                 args = tool_call.get("arguments") or tool_call.get("args")
        # Handle object (if passed directly from agent memory)
        elif hasattr(tool_call, "name") and hasattr(tool_call, "arguments"):
            func_name = tool_call.name
            args = tool_call.arguments
        else:
            return str(tool_call)

        if not func_name:
            return ""

        # Handle arguments
        args_str = ""
        if isinstance(args, dict):
            parts = []
            for k, v in args.items():
                parts.append(f"{k}={repr(v)}")
            args_str = ", ".join(parts)
        elif isinstance(args, str):
            # Try to treat as single argument if it doesn't look like kwargs
            if args.strip().startswith("{") and args.strip().endswith("}"):
                 try:
                     json_args = json.loads(args)
                     if isinstance(json_args, dict):
                         parts = [f"{k}={repr(v)}" for k, v in json_args.items()]
                         args_str = ", ".join(parts)
                     else:
                         args_str = repr(args)
                 except:
                     args_str = repr(args)
            else:
                args_str = repr(args)
        else:
             args_str = repr(args) if args is not None else ""

        return f"{func_name}({args_str})"
    except Exception as e:
        return f"# Error formatting tool call: {e}"

def compute_archived_hash(env_resources: List[Dict[str, Any]], log_archive_info: Dict[str, Any]) -> str:
    """Compute hash of environment state based on archived resources."""
    hasher = hashlib.sha256()
    
    # Map label -> archive_path from the log metadata
    label_to_archive = {}
    archived_resources = log_archive_info.get("resources", [])
    
    for item in archived_resources:
        if "label" in item and "archive_path" in item:
            label_to_archive[item["label"]] = item["archive_path"]

    # Iterate over the EXPECTED task resources (from task definition)
    for resource in sorted(env_resources, key=lambda x: x.get("label", "")):
        label = resource.get("label")
        if not label:
            continue
            
        archive_path = label_to_archive.get(label)
        
        # Fallback: match by filename
        if not archive_path:
             path = resource.get("path")
             if path:
                 fname = Path(path).name
                 for ar in archived_resources:
                     if Path(ar.get("source_path", "")).name == fname:
                         archive_path = ar.get("archive_path")
                         break
        
        if archive_path and os.path.exists(archive_path):
            archive_path_obj = Path(archive_path)
            try:
                if archive_path_obj.is_file():
                    with open(archive_path_obj, "rb") as f:
                        hasher.update(f.read())
                elif archive_path_obj.is_dir():
                    for file_path in sorted(archive_path_obj.rglob("*")):
                        if file_path.is_file():
                            hasher.update(str(file_path.relative_to(archive_path_obj)).encode())
                            with open(file_path, "rb") as f:
                                hasher.update(f.read())
            except Exception as e:
                print(f"Error hashing archive {archive_path}: {e}")
                hasher.update(f"error:{label}".encode())
        else:
             # Missing resource in archive -> affects hash
             hasher.update(f"missing:{label}".encode())
    
    return hasher.hexdigest()

def evaluate_actions(
    task: Dict[str, Any],
    log: Dict[str, Any],
    tool_map: Dict[str, Any],
    environment_context: Dict[str, Any],
    archive_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate by comparing environment states after executing gold vs actual actions."""
    gold_actions = task.get("actions", [])
    
    # Determine Archive Mode
    use_archive = False
    archive_task_path = ""
    
    if archive_dir and os.path.exists(archive_dir):
        env_paths = task.get('environment_paths', [])
        # Default fallback
        task_id_str = str(task.get("task_id") or task.get("id", ""))
        task_folder = f"task_{task_id_str}"
        
        # Look for explicit task folder in environment paths
        if isinstance(env_paths, list):
            for path_str in env_paths:
                parts = path_str.split('/')
                for p in parts:
                    if p.startswith('task_') and p != 'task_':
                        task_folder = p
                        break
                if task_folder.startswith('task_') and task_folder != 'task_':
                    break
                    
        potential_path = os.path.join(archive_dir, task_folder)
        if os.path.exists(potential_path):
            use_archive = True
            archive_task_path = potential_path

    # Extract actual actions from log using DataClean logic
    cleaned_memory = extract_memory_fields(log)
    tool_calls_all = cleaned_memory.get("tool_calls_all", [])
    
    actual_actions = []
    for tc in tool_calls_all:
        if isinstance(tc, str):
            actual_actions.append(tc)
        else:
            code = format_tool_call(tc)
            if code and not code.startswith("#"):
                actual_actions.append(code)
    
    # Setup environment initial config
    # Override build_task_objective logic to strictly use environment_paths from task
    env_paths = task.get("environment_paths", [])
    env_resources_config = []
    
    # Resolve repo root (assuming script is in repo_root or one level down)
    # We use formatting of the path to handle relative paths correctly
    repo_root = Path(os.getcwd()) 
    
    if isinstance(env_paths, list):
        for ep in env_paths:
            full_ep = repo_root / ep
            if full_ep.exists():
                if full_ep.is_file():
                    env_resources_config.append({
                        "path": str(full_ep),
                        "label": full_ep.name
                    })
                elif full_ep.is_dir():
                    # scan directory for files
                    for f in full_ep.glob("*"):
                        if f.is_file():
                             env_resources_config.append({
                                "path": str(f),
                                "label": f.name
                            })
    
    # Fallback to build_task_objective if explicit paths failed/empty (though user insists on using it)
    if not env_resources_config:
         _, env_resources_config = build_task_objective(task, environment_context)

    set_task_environment_resources(env_resources_config or [])
    
    from Utils.environment_utils import get_task_environment_resources
    current_resources = get_task_environment_resources()
    
    # BACKUP environment
    backups = backup_resources(current_resources)
    
    # Initialize variables to avoid unbound errors
    gold_success, gold_hash, gold_error = False, "", ""
    actual_success, actual_hash, actual_error = False, "", ""
    
    try:
        # 1. Execute gold actions
        # We start clean (current state is clean)
        gold_success, gold_hash, gold_error = execute_actions_in_environment(
            gold_actions, tool_map, environment_context
        )
        
        if use_archive:
            # In Archive Mode, we compare Gold Hash vs Archive Hash
            if gold_success:
                 # Calculate hash from the archive files referenced in the log
                 # Accessing raw log since extract_memory_fields might filter fields
                 log_archive = log.get("environment_archive", {})
                 actual_hash = compute_archived_hash(current_resources, log_archive)
                 
                 if not actual_hash or actual_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
                     print(f"DEBUG: Empty actual hash for task {task.get('task_id')}")
                     print(f"DEBUG: Env Resources: {[r.get('label') for r in current_resources]}")
                     print(f"DEBUG: Log Archive Keys: {log_archive.keys()}")
                     if 'resources' in log_archive:
                         print(f"DEBUG: Log Archive Resources: {[r.get('label') for r in log_archive['resources']]}")
                 
                 # Fallback: if log doesn't have info, try scanning the detected archive path
                 if actual_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" and archive_task_path:
                      # Re-implement simple scanning if needed, or just warn
                      # Trying simple scan hashing using the previous logic style inline?
                      # Better to just stick with log info for now, as that's arguably more correct for "Archived" state
                      pass
                      
                 actual_success = True
                 actual_actions = ["(From Archive)"]
                 if not actual_hash:
                     actual_error = "Warning: Empty archive hash."
            else:
                 actual_success = False
                 actual_error = "Gold execution failed, cannot compare to archive"
        else:
            # 2. RESTORE environment for actual actions
            # Using keep_backup=True to ensure backup exists until the end
            restore_resources(backups, keep_backup=True)
            
            # 3. Execute actual actions
            actual_success, actual_hash, actual_error = execute_actions_in_environment(
                actual_actions, tool_map, environment_context
            )
        
    except Exception as e:
        print(f"Critical error during action evaluation: {e}")
        # Mark as failed if critical error occurred
    finally:
        # Cleanup backups
        for orig, bak in backups.items():
            if os.path.exists(bak):
                if os.path.isdir(bak):
                    shutil.rmtree(bak, ignore_errors=True)
                else:
                    try: os.remove(bak) 
                    except: pass

    # Compare hashes
    match = gold_hash == actual_hash if gold_success and actual_success else False
    
    return {
        "type": "actions",
        "score": 1 if match else 0,
        "match": match,
        "gold_actions": gold_actions,
        "actual_actions": actual_actions,
        "gold_hash": gold_hash,
        "actual_hash": actual_hash,
        "gold_error": gold_error,
        "actual_error": actual_error,
        "archive_mode": use_archive
    }


def evaluate_single_task(
    task: Dict[str, Any],
    log: Dict[str, Any],
    eval_type: str,
    llm_config: Optional[Dict[str, Any]],
    tool_map: Dict[str, Any],
    environment_context: Dict[str, Any],
    archive_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate a single task based on evaluation type."""
    task_id = task.get("task_id") or task.get("id") or log.get("inner_task_id", "")
    description = task.get("instruction") or task.get("description") or task.get("task", "")
    
    result = {
        "task_id": task_id,
        "description": description,
        "timestamp": datetime.now().isoformat(),
    }
    
    if eval_type in ["label", "both"]:
        label_result = evaluate_label(task, log, llm_config or {})
        result["label_evaluation"] = label_result
        result["label_score"] = label_result["score"]
    
    if eval_type in ["actions", "both"]:
        actions_result = evaluate_actions(task, log, tool_map, environment_context, archive_dir)
        result["actions_evaluation"] = actions_result
        result["actions_score"] = actions_result["score"]
    
    # Determine final score
    if eval_type == "label":
        result["final_score"] = result.get("label_score", 0)
    elif eval_type == "actions":
        result["final_score"] = result.get("actions_score", 0)
    else:  # both
        # Both must be correct
        label_ok = result.get("label_score", 0) == 1
        actions_ok = result.get("actions_score", 0) == 1
        result["final_score"] = 1 if (label_ok and actions_ok) else 0
    
    return result


def run_evaluation(config: Dict[str, Any]) -> None:
    """Main evaluation function."""
    print("Starting evaluation...")
    
    # Load configuration
    repo_root = Path.cwd()
    environment_context = normalize_environment_config(config, repo_root)
    benchmark_path = config.get("Benchmark", {}).get("path", "")
    benchmark_name = Path(benchmark_path).stem if benchmark_path else ""
    environment_context["benchmark_path"] = benchmark_path
    environment_context["benchmark_name"] = benchmark_name
    set_global_environment_context(environment_context)
    
    # Load tasks
    tasks = load_benchmark_tasks(config)
    print(f"Loaded {len(tasks)} benchmark tasks")
    
    # Load result logs
    result_config = config.get("Result", {})
    log_dir = result_config.get("log_dir", "./Results/logs")
    archive_dir = result_config.get("environment_archive_dir")
    logs = load_result_logs(log_dir)
    print(f"Loaded {len(logs)} result logs")
    
    # Get evaluation config
    eval_config = config.get("Evaluation", {})
    eval_type = eval_config.get("type", "label").lower()
    save_dir = eval_config.get("save_dir", "./Evaluation")
    
    # Get task range
    benchmark_config = config.get("Benchmark", {})
    start_idx = benchmark_config.get("start_idx")
    end_idx = benchmark_config.get("end_idx")
    
    # Filter tasks by index
    total_tasks = len(tasks)
    resolved_start = 1 if not start_idx or start_idx < 1 else start_idx
    resolved_end = total_tasks if not end_idx or end_idx > total_tasks else end_idx
    tasks = [t for i, t in enumerate(tasks, 1) if resolved_start <= i <= resolved_end]
    print(f"Evaluating tasks {resolved_start}-{resolved_end} ({len(tasks)} tasks)")
    
    # Clean logs if actions evaluation is needed
    cleaned_log_file = None
    if eval_type in ["actions", "both"]:
        print("Cleaning logs for actions evaluation...")
        cleaned_log_file = clean_logs(logs, save_dir)
    
    # Load tools if actions evaluation is needed
    tool_map = {}
    if eval_type in ["actions", "both"]:
        print("Loading tools...")
        try:
            tools_list = load_tools(config)
            tool_map = {getattr(t, "name", t.__class__.__name__): t for t in tools_list}
            print(f"Loaded {len(tool_map)} tools via load_tools")
        except Exception as e:
            print(f"Error checking load_tools: {e}")
            print("Falling back to scan_and_import_tools")
            toolkit_path = Path(config.get("Toolkit", {}).get("path", "./Toolkit")).expanduser()
            tool_map = scan_and_import_tools(toolkit_path, recursive=True)
            print(f"Loaded {len(tool_map)} tools")
    
    # Get LLM config if label evaluation is needed
    llm_config = None
    if eval_type in ["label", "both"]:
        llm_config = config.get("Evaluation", {}).get("server", {})
        if not llm_config:
            print("Warning: No LLM configuration found for label evaluation")
    
    # Match logs to tasks
    task_log_map = {}
    for log in logs:
        # Try to match by task_id
        log_task_id = log.get("task", {}).get("task_id") or log.get("inner_task_id", "")
        if log_task_id:
            task_log_map[log_task_id] = log
    
    # Evaluate each task
    evaluation_results = []
    success_count = 0
    
    for idx, task in enumerate(tasks, 1):
        task_id = task.get("task_id") or task.get("id", "")
        print(f"\n[{idx}/{len(tasks)}] Evaluating task: {task_id}")
        
        # Find corresponding log
        log = task_log_map.get(task_id)
        if not log:
            print(f"  Warning: No log found for task {task_id}, skipping")
            continue
        
        try:
            result = evaluate_single_task(
                task=task,
                log=log,
                eval_type=eval_type,
                llm_config=llm_config,
                tool_map=tool_map,
                environment_context=environment_context,
                archive_dir=archive_dir,
            )
            
            evaluation_results.append(result)
            
            if result.get("final_score", 0) == 1:
                success_count += 1
                print(f"  ✓ Success (score: 1)")
            else:
                print(f"  ✗ Failed (score: 0)")
                # Print failure reason for actions evaluation
                if "actions_evaluation" in result:
                    ae = result["actions_evaluation"]
                    if ae.get("gold_error"):
                        print(f"    Gold Action Error: {ae['gold_error']}")
                    if ae.get("actual_error"):
                        print(f"    Actual Action Error: {ae['actual_error']}")
                    if not ae.get("match") and not ae.get("gold_error") and not ae.get("actual_error"):
                         print(f"    Hash Mismatch: Gold({ae.get('gold_hash')[:8]}...) != Actual({ae.get('actual_hash')[:8]}...)")
            
        except Exception as exc:
            print(f"  Error evaluating task {task_id}: {exc}")
            evaluation_results.append({
                "task_id": task_id,
                "error": str(exc),
                "final_score": 0,
            })
    
    # Compute summary statistics
    total_evaluated = len(evaluation_results)
    success_rate = success_count / total_evaluated if total_evaluated > 0 else 0.0
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "evaluation_type": eval_type,
        "total_tasks": total_evaluated,
        "successful_tasks": success_count,
        "failed_tasks": total_evaluated - success_count,
        "success_rate": round(success_rate, 4),
        "benchmark_path": benchmark_path,
        "log_dir": log_dir,
    }
    
    # Save results
    output_dir = Path(save_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"evaluation_results_{timestamp}.jsonl"
    
    with open(output_file, "w", encoding="utf-8") as f:
        # Write summary first
        f.write(json.dumps({"summary": summary}, ensure_ascii=False) + "\n")
        
        # Write individual results
        for result in evaluation_results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    print(f"\n{'='*60}")
    print("Evaluation completed!")
    print(f"{'='*60}")
    print(f"Total tasks evaluated: {total_evaluated}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_evaluated - success_count}")
    print(f"Success rate: {success_rate:.2%}")
    print(f"\nResults saved to: {output_file}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate benchmark results")
    parser.add_argument(
        "--config",
        type=str,
        default="eval_config.yaml",
        help="Path to evaluation configuration file",
    )
    args = parser.parse_args()
    
    try:
        config_path = Path(args.config).expanduser().resolve()
        config = read_config(config_path)
        print(f"Configuration loaded: {config_path}")
        
        run_evaluation(config)
        
    except Exception as exc:
        print(f"Evaluation error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
