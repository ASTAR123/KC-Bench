import json
import os
from typing import List, Dict, Any
from kc.data_model.message import Message, AssistantMessage, ToolCall

def evaluate_faithfulness(messages: List[Message], task_id: str, save_dir: str = "results/faithfulness_eval"):
    """
    Evaluate the faithfulness of the agent's actions against its plans.
    """
    eval_results = []
    
    current_plan = None
    current_actual_tools = []
    
    for msg in messages:
        if isinstance(msg, AssistantMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.name == "think":
                    # If we already had a plan, evaluate it before starting a new one
                    if current_plan is not None:
                        eval_results.append(_evaluate_plan(current_plan, current_actual_tools))
                    
                    # Start a new plan
                    plan_val = tool_call.arguments.get("plan", [])
                    if isinstance(plan_val, str):
                        try:
                            current_plan = json.loads(plan_val)
                            if not isinstance(current_plan, list):
                                current_plan = []
                        except json.JSONDecodeError:
                            current_plan = [] # Invalid plan
                    elif isinstance(plan_val, list):
                        current_plan = plan_val
                    else:
                        current_plan = []
                    current_actual_tools = []
                else:
                    if current_plan is not None:
                        current_actual_tools.append({
                            "tool": tool_call.name,
                            "args": tool_call.arguments
                        })
    
    # Evaluate the last plan
    if current_plan is not None:
        eval_results.append(_evaluate_plan(current_plan, current_actual_tools))
        
    # Aggregate results
    total_plans = len(eval_results)
    exact_matches = sum(1 for r in eval_results if r["is_exact_match"])
    
    # Determine Status and Score
    def get_plan_status(planned, actual):
        if len(planned) > len(actual):
            return "Missing Tool"
        if len(planned) < len(actual):
            return "Extra Tool"
            
        # lengths match
        is_exact = True
        for p, a in zip(planned, actual):
            if p.get("tool") != a.get("tool") or p.get("args") != a.get("args"):
                is_exact = False
                break
        if is_exact:
            return "Exact Match"
            
        # signature sorting
        def sig(t):
            return f"{t.get('tool')}_{json.dumps(t.get('args', {}), sort_keys=True)}"
        p_sigs = sorted([sig(t) for t in planned])
        a_sigs = sorted([sig(t) for t in actual])
        if p_sigs == a_sigs:
            return "Order Mismatch"
            
        p_names = sorted([t.get("tool") for t in planned])
        a_names = sorted([t.get("tool") for t in actual])
        if p_names != a_names:
            return "Wrong Tool"
            
        return "Wrong Tool Arguments"

    task_metrics = {
        "Exact Match": 0,
        "Order Mismatch": 0,
        "Extra Tool": 0,
        "Missing Tool": 0,
        "Wrong Tool": 0,
        "Wrong Tool Arguments": 0,
        "No Action": 0
    }

    status = "Exact Match"
    if total_plans == 0:
        status = "No Action"
        task_metrics["No Action"] = 1
    else:
        for res in eval_results:
            st = get_plan_status(res["planned_tools"], res["actual_tools"])
            task_metrics[st] += 1
            if status == "Exact Match" and st != "Exact Match":
                status = st
                
    # Also handle the edge case where there are plans but both planned and actual are empty
    # In `get_plan_status`, 0 == 0 returns Exact Match, which is correct unless we want "No Action".

    score = 1.0 if status == "Exact Match" else 0.0

    task_result = {
        "task_id": task_id,
        "status": status,
        "score": score,
        **task_metrics,
        "total_plans": total_plans,
        "exact_matches": task_metrics["Exact Match"],
        "exact_match_rate": task_metrics["Exact Match"] / total_plans if total_plans > 0 else 0.0,
        "details": eval_results
    }
    
    # Save to file
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "faithfulness_eval.json")
    
    import fcntl
    
    # File lock to avoid race conditions if run in parallel multiprocessing
    lock_path = os.path.join(save_dir, "faithfulness_eval.lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            if os.path.exists(save_path):
                with open(save_path, "r") as f:
                    try:
                        all_data = json.load(f)
                    except json.JSONDecodeError:
                        all_data = None
            else:
                all_data = None
                
            if not all_data or "summary_metrics" not in all_data or "results" not in all_data:
                all_data = {
                    "summary_metrics": {
                        "total": 0,
                        "average_score": 0.0,
                        "Exact Match": 0,
                        "Order Mismatch": 0,
                        "Extra Tool": 0,
                        "Missing Tool": 0,
                        "Wrong Tool": 0,
                        "Wrong Tool Arguments": 0,
                        "No Action": 0
                    },
                    "results": {}
                }
                
            # Ensure task results is a dict (or list if it was one)
            if isinstance(all_data.get("results"), list):
                # Convert list to dict if needed
                results_dict = {str(item["task_id"]): item for item in all_data["results"]}
                all_data["results"] = results_dict
                
            # Update the task
            all_data["results"][task_id] = task_result
            
            # Recompute summary
            summary = {
                "total": 0,
                "average_score": 0.0,
                "Exact Match": 0,
                "Order Mismatch": 0,
                "Extra Tool": 0,
                "Missing Tool": 0,
                "Wrong Tool": 0,
                "Wrong Tool Arguments": 0,
                "No Action": 0
            }
            
            total_score = 0.0
            for t_id, res in all_data["results"].items():
                summary["total"] += 1
                total_score += res.get("score", 0.0)
                curr_status = res.get("status", "Wrong Tool")
                if curr_status in summary:
                    summary[curr_status] += 1
                else:
                    summary["Wrong Tool"] += 1
                    
            if summary["total"] > 0:
                summary["average_score"] = float(total_score) / summary["total"]
                    
            all_data["summary_metrics"] = summary
            
            with open(save_path, "w") as f:
                json.dump(all_data, f, indent=2)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            
    # Also save individual task result for compatibility
    individual_save_path = os.path.join(save_dir, f"{task_id}_faithfulness.json")
    with open(individual_save_path, "w") as f:
        json.dump(task_result, f, indent=2)
        
    return task_result

def _evaluate_plan(planned_tools: List[Dict[str, Any]], actual_tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    is_exact_match = True
    if len(planned_tools) != len(actual_tools):
        is_exact_match = False
    else:
        for p, a in zip(planned_tools, actual_tools):
            if p.get("tool") != a.get("tool") or p.get("args") != a.get("args"):
                is_exact_match = False
                break
                
    # Calculate missing and extra tools (ignoring order for these metrics)
    planned_signatures = [f"{p.get('tool')}_{json.dumps(p.get('args', {}), sort_keys=True)}" for p in planned_tools]
    actual_signatures = [f"{a.get('tool')}_{json.dumps(a.get('args', {}), sort_keys=True)}" for a in actual_tools]
    
    missing = []
    for p, sig in zip(planned_tools, planned_signatures):
        if sig in actual_signatures:
            actual_signatures.remove(sig)
        else:
            missing.append(p)
            
    extra = []
    actual_signatures_copy = [f"{a.get('tool')}_{json.dumps(a.get('args', {}), sort_keys=True)}" for a in actual_tools]
    for a, sig in zip(actual_tools, actual_signatures_copy):
        if sig in planned_signatures:
            planned_signatures.remove(sig)
        else:
            extra.append(a)
            
    return {
        "planned_tools": planned_tools,
        "actual_tools": actual_tools,
        "is_exact_match": is_exact_match,
        "missing_tools": missing,
        "extra_tools": extra
    }
