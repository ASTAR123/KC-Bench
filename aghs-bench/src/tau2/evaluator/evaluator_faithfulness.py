import json
import os
from typing import List, Dict, Any
from tau2.data_model.message import Message, AssistantMessage, ToolCall

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
    
    task_result = {
        "task_id": task_id,
        "total_plans": total_plans,
        "exact_matches": exact_matches,
        "exact_match_rate": exact_matches / total_plans if total_plans > 0 else 0.0,
        "details": eval_results
    }
    
    # Save to file
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{task_id}_faithfulness.json")
    with open(save_path, "w") as f:
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
