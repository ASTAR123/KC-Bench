import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_target_line, get_plan_by_id

def _run_get_data_usage(data, customer_id: str, line_id: str) -> dict:
    """
    Internal function to execute get_data_usage logic.
    """
    db = data
    line = get_target_line(db, customer_id, line_id)
    plan = get_plan_by_id(db, line['plan_id'])
    if not plan:
        raise ValueError(f"Plan {line['plan_id']} not found")
    data_used = line.get('data_used_gb', 0.0)
    data_refueling = line.get('data_refueling_gb', 0.0)
    data_limit = plan['data_limit_gb']
    total_available = data_limit + data_refueling
    remaining = max(0, total_available - data_used)
    usage_percentage = (data_used / total_available * 100) if total_available > 0 else 0
    return {
        "data_used_gb": data_used,
        "data_refueling_gb": data_refueling,
        "data_limit_gb": data_limit,
        "remaining_data_gb": remaining,
        "usage_percentage": round(usage_percentage, 2)
    }


@tool
def get_data_usage(customer_id: str, line_id: str) -> dict:
    """
    Get data usage information for a specific line.
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID (e.g., "L1001")
    
    Returns:
        Dictionary containing data usage details.
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_get_data_usage(data, customer_id=customer_id, line_id=line_id)
    except Exception as e:
        return f"Error executing get_data_usage: {str(e)}"

    return result
