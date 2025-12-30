"""Tool to retrieve customer information by customer ID."""

import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))


from smolagents import tool
from data_helpers import load_db, get_customer_by_id as get_customer_helper
import json


def _run_get_customer_by_id(data: dict, customer_id: str) -> str:
    """Internal function to execute logic."""

    customer = get_customer_helper(data, customer_id)
    
    if not customer:
        return f"Error: Customer {customer_id} not found"
    
    return json.dumps(customer, ensure_ascii=False)


@tool
def get_customer_by_id(customer_id: str) -> str:
    """
    Retrieve customer information using their customer ID.
    
    Args:
        customer_id: The unique customer identifier (e.g., "C1001")
    
    Returns:
        JSON string containing customer information or error message.
    """
    try:
        data = load_db()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    
    try:
        result = _run_get_customer_by_id(data, customer_id=customer_id)
    except Exception as exc:
        return f"Error executing get_customer_by_id: {exc}"
    
    return result
