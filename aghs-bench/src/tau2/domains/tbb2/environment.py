# Copyright Sierra
import json
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.personalAssistant.data_model import PersonalAssistantDB
from tau2.domains.personalAssistant.tools import PersonalAssistantTools
from tau2.domains.personalAssistant.utils import (
    PERSONALASSISTANT_DB_PATH,
    PERSONALASSISTANT_POLICY_PATH,
    PERSONALASSISTANT_TASK_SET_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils import load_file


def get_environment(
    db: Optional[PersonalAssistantDB] = None,
    solo_mode: bool = False,
) -> Environment:
    if solo_mode:
        raise ValueError("Personal Assistant domain does not support solo mode")
    if db is None:
        db = PersonalAssistantDB.load(PERSONALASSISTANT_DB_PATH)
    tools = PersonalAssistantTools(db)
    with open(PERSONALASSISTANT_POLICY_PATH, "r") as fp:
        policy = fp.read()
    return Environment(
        domain_name="personalAssistant",
        policy=policy,
        tools=tools,
    )


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    tasks = load_file(PERSONALASSISTANT_TASK_SET_PATH)
    tasks = [Task.model_validate(task) for task in tasks]
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
        Path(PERSONALASSISTANT_TASK_SET_PATH).parent
        / f"split_{Path(PERSONALASSISTANT_TASK_SET_PATH).stem}.json"
    )
    return load_file(split_file)