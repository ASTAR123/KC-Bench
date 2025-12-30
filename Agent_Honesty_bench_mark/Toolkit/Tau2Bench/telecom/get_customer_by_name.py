"""Tool to retrieve customer information by name and date of birth."""

import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))


from smolagents import tool
from data_helpers import load_db
import json


def _run_get_customer_by_name(data: dict, full_name: str, dob: str) -> str:
    """Internal function to execute logic."""

    matching_customers = []
    
    for customer in data.get('customers', []):
        if customer.get('full_name') == full_name and customer.get('date_of_birth') == dob:
            matching_customers.append(customer)
    
    if not matching_customers:
        return f"Error: No customer found with name {full_name} and DOB {dob}"
    
    return json.dumps(matching_customers, ensure_ascii=False)


@tool
def get_customer_by_name(full_name: str, dob: str) -> str:
    """
    Retrieve customer information using their full name and date of birth.
    
    Args:
        full_name: The customer's full name (e.g., "John Smith")
        dob: The customer's date of birth in YYYY-MM-DD format (e.g., "1985-06-15")
    
    Returns:
        JSON string containing list of matching customers or error message.
    """
    try:
        data = load_db()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    
    try:
        result = _run_get_customer_by_name(data, full_name=full_name, dob=dob)
    except Exception as exc:
        return f"Error executing get_customer_by_name: {exc}"
    
    return result
