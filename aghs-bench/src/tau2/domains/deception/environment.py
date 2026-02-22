# Copyright Sierra
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.deception.data_model import FlightDB
from tau2.domains.deception.tools import DeceptionTools
from tau2.domains.deception.utils import (
    Deception_DB_PATH,
    Deception_POLICY_PATH,
    Deception_TASK_SET_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils import load_file


def get_environment(
    db: Optional[FlightDB] = None,
    solo_mode: bool = False,
) -> Environment:
    if solo_mode:
        raise ValueError("Deception domain does not support solo mode")
    if db is None:
        db = FlightDB.load(Deception_DB_PATH)
    tools = DeceptionTools(db)
    with open(Deception_POLICY_PATH, "r") as fp:
        policy = fp.read()
    return Environment(
        domain_name="deception",
        policy=policy,
        tools=tools,
    )


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    tasks = load_file(Deception_TASK_SET_PATH)
    tasks = [Task.model_validate(task) for task in tasks]
    if task_split_name is None:
        return tasks
    task_splits = get_tasks_split()
    if task_split_name not in task_splits:
        raise ValueError(
            f"Invalid task split name: {task_split_name}. Valid splits are: {task_splits.keys()}"
        )
    return [task for task in tasks if task.id in task_splits[task_split_name]]


def get_tasks_split() -> dict[str, list[str]]:
    split_file = (
        Path(Deception_TASK_SET_PATH).parent
        / f"split_{Path(Deception_TASK_SET_PATH).stem}.json"
    )
    return load_file(split_file)
