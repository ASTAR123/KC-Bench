"""Tool to retrieve customer information by phone number."""

import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))


from smolagents import tool
from data_helpers import load_db, save_db, get_customer_by_phone as get_customer_helper
import json


def _run_get_customer_by_phone(data: dict, phone_number: str) -> str:
    """Internal function to execute get_customer_by_phone logic."""

    customer = get_customer_helper(data, phone_number)
    
    if not customer:
        return f"Error: No customer found with phone number {phone_number}"
    
    return json.dumps(customer, ensure_ascii=False)


@tool
def get_customer_by_phone(phone_number: str) -> str:
    """
    Retrieve customer information using their phone number.
    
    Args:
        phone_number: The phone number associated with the customer account (e.g., "555-123-2001")
    
    Returns:
        JSON string containing customer information or error message.
    """
    try:
        data = load_db()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    
    try:
        result = _run_get_customer_by_phone(data, phone_number=phone_number)
    except Exception as exc:
        return f"Error executing get_customer_by_phone: {exc}"
    
    if isinstance(result, str) and result.startswith('Error'):
        return result
    
    # Read-only operation, no need to save
    return result
