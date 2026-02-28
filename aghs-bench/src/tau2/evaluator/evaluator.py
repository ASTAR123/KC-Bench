from enum import Enum

from tau2.data_model.simulation import RewardInfo, SimulationRun, TerminationReason
from tau2.data_model.tasks import RewardType, Task
from tau2.evaluator.evaluator_nl_assertions import NLAssertionsEvaluator


class EvaluationType(str, Enum):
    ENV = "env"
    COMMUNICATE = "communicate"
    ACTION = "action"
    ALL = "all"
    NL_ASSERTIONS = "nl_assertions"  # WIP
    ALL_WITH_NL_ASSERTIONS = "all_with_nl_assertions"  # WIP


def evaluate_simulation(
    simulation: SimulationRun,
    task: Task,
    evaluation_type: EvaluationType,
    solo_mode: bool,
    domain: str,
    **kwargs
) -> RewardInfo:
    """
    Evaluate the simulation based on the evaluation type.
    """
    evaluation_type = EvaluationType.NL_ASSERTIONS
    if simulation.termination_reason not in {
        TerminationReason.AGENT_STOP,
        TerminationReason.USER_STOP,
    }:
        return RewardInfo(
            reward=0.0,
            reward_basis=None,
            info={
                "note": f"Simulation terminated prematurely. Termination reason: {simulation.termination_reason.value}"
            },
        )
    if task.evaluation_criteria is None:
        return RewardInfo(
            reward=1.0,
            reward_basis=None,
            info={"note": "No evaluation criteria"},
        )
    
    reward_info = NLAssertionsEvaluator.calculate_reward(
        task=task,
        full_trajectory=simulation.messages,
    )

    if domain == "faithfulness":
        from tau2.evaluator.evaluator_faithfulness import evaluate_faithfulness
        
        save_dir = kwargs.get("faithfulness_save_dir", "results/faithfulness_eval")
        
        faithfulness_result = evaluate_faithfulness(
            messages=simulation.messages,
            task_id=task.id,
            save_dir=save_dir
        )
        if reward_info.info is None:
            reward_info.info = {}
        reward_info.info["faithfulness_eval"] = faithfulness_result

    return reward_info