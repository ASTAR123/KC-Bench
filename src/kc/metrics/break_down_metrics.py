import pandas as pd

from kc.data_model.simulation import Results, RewardInfo, RewardType
from kc.environment.toolkit import ToolType
from kc.metrics.agent_metrics import is_successful
from kc.registry import registry


def get_write_tools(domain):
    env = registry.get_env_constructor(domain)()
    user_write_tools = []
    agent_write_tools = []

    for tool in env.tools.get_tools():
        tool_type = getattr(env.tools, tool).__tool_type__
        if tool_type == ToolType.WRITE:
            agent_write_tools.append(tool)

    if env.user_tools:
        for tool in env.user_tools.get_tools():
            tool_type = getattr(env.user_tools, tool).__tool_type__
            if tool_type == ToolType.WRITE:
                user_write_tools.append(tool)
    return set(agent_write_tools), set(user_write_tools)


def analyze_reward(
    reward_info: RewardInfo, agent_write_tools: set[str], user_write_tools: set[str]
):
    """
    Analyze the reward breakdown.
    """
    reward_breakdown = reward_info.reward_breakdown
    reward_basis = reward_info.reward_basis or []
    
    reward_analysis = {
        "success": is_successful(reward_info.reward),
        "nl_assertion": is_successful(reward_info.reward) if RewardType.NL_ASSERTION in reward_basis else None,
    }
    return reward_analysis


def analyze_reward_actions(reward_info: RewardInfo) -> pd.DataFrame:
    """
    Analyze the actions taken by the agent and the user.
    """
    reward_breakdown = reward_info.reward_breakdown
    if reward_breakdown is None:
        return None
    rows = []
    if reward_info.action_checks is None:
        return None
    for action_check in reward_info.action_checks:
        row = {
            "requestor": action_check.action.requestor,
            "action_name": action_check.action.name,
            "action": action_check.action.get_func_format(),
            "action_match": action_check.action_match,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def result_reward_analysis(results: Results):
    """
    Analyze the reward breakdown.
    """
    rows = []
    agent_write_tools, user_write_tools = get_write_tools(
        results.info.environment_info.domain_name
    )
    for simulation in results.simulations:
        reward_analysis = analyze_reward(
            simulation.reward_info, agent_write_tools, user_write_tools
        )
        reward_analysis["task_id"] = simulation.task_id
        reward_analysis["trial"] = simulation.trial
        rows.append(reward_analysis)
    return pd.DataFrame(rows)


def result_reward_actions_analysis(results: Results):
    """
    Analyze the actions taken by the agent and the user.
    """
    dfs = []
    for simulation in results.simulations:
        reward_actions_analysis = analyze_reward_actions(simulation.reward_info)
        if reward_actions_analysis is None:
            continue
        reward_actions_analysis["task_id"] = simulation.task_id
        reward_actions_analysis["trial"] = simulation.trial
        dfs.append(reward_actions_analysis)
    return pd.concat(dfs)
