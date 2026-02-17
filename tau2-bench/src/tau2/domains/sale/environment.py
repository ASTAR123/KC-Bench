# Copyright Sierra
from pathlib import Path
from typing import Optional

from tau2.data_model.tasks import Task
from tau2.domains.sale.data_model import InventoryDB
from tau2.domains.sale.tools import SaleTools
from tau2.domains.sale.utils import (
    SALE_DB_PATH,
    SALE_POLICY_PATH,
    SALE_TASK_SET_PATH,
)
from tau2.environment.environment import Environment
from tau2.utils import load_file


def get_environment(
    db: Optional[InventoryDB] = None,
    solo_mode: bool = False,
) -> Environment:
    """
    Constructs the electronics retail environment.
    
    Args:
        db: An optional InventoryDB instance. If None, it loads from SALE_DB_PATH.
        solo_mode: Boolean flag. Sale domain follows Airline pattern by disabling solo mode.
        
    Returns:
        A configured Environment instance ready for agent interaction.
    """
    if solo_mode:
        raise ValueError("Sale domain does not support solo mode")
    
    # 1. Load the Inventory Database
    if db is None:
        # Uses the custom .load() method from your Sale data_model
        db = InventoryDB.load(SALE_DB_PATH)
    
    # 2. Initialize Tools (Providing the agent with 'Transparency' tools)
    tools = SaleTools(db)
    
    # 3. Read the Sales Policy
    # This file should contain the high-pressure sales guidelines for the test
    with open(SALE_POLICY_PATH, "r", encoding="utf-8") as fp:
        policy = fp.read()
    
    # 4. Encapsulate into the tau2 Environment
    return Environment(
        domain_name="sale",
        policy=policy,
        tools=tools,
    )


def get_tasks(task_split_name: Optional[str] = "base") -> list[Task]:
    """
    Loads and validates tasks from the dataset (e.g., 'Sell a refurbished tablet').
    
    Args:
        task_split_name: The name of the task subset (e.g., 'base', 'test').
        
    Returns:
        A list of validated Task objects.
    """
    tasks = load_file(SALE_TASK_SET_PATH)
    tasks = [Task.model_validate(task) for task in tasks]
    
    if task_split_name is None:
        return tasks
    
    task_splits = get_tasks_split()
    if task_split_name not in task_splits:
        raise ValueError(
            f"Invalid task split name: {task_split_name}. Valid splits are: {list(task_splits.keys())}"
        )
    
    # Filter tasks based on the defined split IDs
    return [task for task in tasks if task.id in task_splits[task_split_name]]


def get_tasks_split() -> dict[str, list[str]]:
    """
    Locates the split file (e.g., split_tasks.json) to categorize task IDs.
    
    Returns:
        A dictionary mapping split names to lists of task IDs.
    """
    task_set_path = Path(SALE_TASK_SET_PATH)
    split_file = (
        task_set_path.parent
        / f"split_{task_set_path.stem}.json"
    )
    return load_file(split_file)