# Copyright Sierra
import json
from pathlib import Path
from typing import Optional

from kc.data_model.tasks import Task
from kc.domains.region.data_model import RegionBenchmarkDB
from kc.domains.region.tools import RegionTools
from kc.domains.region.utils import (
    REGION_DB_PATH,
    REGION_POLICY_PATH,
    REGION_TASK_SET_PATH,
)
from kc.environment.environment import Environment
from kc.utils import load_file


def get_environment(
    db: Optional[RegionBenchmarkDB] = None,
    solo_mode: bool = False,
) -> Environment:
    if solo_mode:
        raise ValueError("Knowledge Conflict domain does not support solo mode")
    if db is None:
        db = RegionBenchmarkDB.load(REGION_DB_PATH)
    tools = RegionTools(db)
    with open(REGION_POLICY_PATH, "r") as fp:
        policy = fp.read()
    return Environment(
        domain_name="region",
        policy=policy,
        tools=tools,
    )


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    tasks_data = load_file(REGION_TASK_SET_PATH)

    # Preprocess tasks to fix validation error where 'info' is a dict instead of string
    for task in tasks_data:
        criteria = task.get("evaluation_criteria")
        if criteria:
            # Ensure we handle both list and single dict cases for evaluation_criteria to be robust
            criteria_list = criteria if isinstance(criteria, list) else [criteria]
            for criterion in criteria_list:
                if isinstance(criterion, dict) and "actions" in criterion:
                    for action in criterion["actions"]:
                        if isinstance(action, dict) and isinstance(action.get("info"), dict):
                            # Extract description or dump to string to satisfy Pydantic string_type requirement
                            action["info"] = action["info"].get("desc", json.dumps(action["info"]))

    tasks = [Task.model_validate(task) for task in tasks_data]
    if task_split_name is None:
        return tasks
    task_splits = get_tasks_split()
    if task_split_name not in task_splits:
        raise ValueError(
            f"Invalid task split name: {task_split_name}. Valid splits are: {task_splits.keys()}"
        )
    tasks = [task for task in tasks if task.id in task_splits[task_split_name]]
    return tasks


def get_tasks_split() -> dict[str, list[str]]:
    split_file = (
        Path(REGION_TASK_SET_PATH).parent
        / f"split_{Path(REGION_TASK_SET_PATH).stem}.json"
    )
    return load_file(split_file)
