import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_plan_by_id, get_device_by_id, get_line_by_id, get_bill_by_id

def _run_get_details_by_id(data, plan_id: str = None, device_id: str = None, line_id: str = None, bill_id: str = None) -> dict:
    """
    Internal function to execute get_details_by_id logic.
    """
    db = data
    provided_ids = sum([plan_id is not None, device_id is not None, line_id is not None, bill_id is not None])
    if provided_ids == 0:
        raise ValueError("Must provide exactly one ID parameter")
    if provided_ids > 1:
        raise ValueError("Must provide exactly one ID parameter, got multiple")
    if plan_id:
        result = get_plan_by_id(db, plan_id)
        if not result:
            raise ValueError(f"Plan {plan_id} not found")
        return result
    if device_id:
        result = get_device_by_id(db, device_id)
        if not result:
            raise ValueError(f"Device {device_id} not found")
        return result
    if line_id:
        result = get_line_by_id(db, line_id)
        if not result:
            raise ValueError(f"Line {line_id} not found")
        return result
    if bill_id:
        result = get_bill_by_id(db, bill_id)
        if not result:
            raise ValueError(f"Bill {bill_id} not found")
        return result


@tool
def get_details_by_id(plan_id: str = None, device_id: str = None, line_id: str = None, bill_id: str = None) -> dict:
    """
    Retrieve detailed information about a plan, device, line, or bill by its ID.
    Provide exactly one ID parameter.
    
    Args:
        plan_id: The plan ID to look up (e.g., "P1001")
        device_id: The device ID to look up (e.g., "D1001")
        line_id: The line ID to look up (e.g., "L1001")
        bill_id: The bill ID to look up (e.g., "B1001")
    
    Returns:
        Dictionary containing the detailed information for the requested entity.
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_get_details_by_id(data, plan_id=plan_id, device_id=device_id, line_id=line_id, bill_id=bill_id)
    except Exception as e:
        return f"Error executing get_details_by_id: {str(e)}"

    return result
