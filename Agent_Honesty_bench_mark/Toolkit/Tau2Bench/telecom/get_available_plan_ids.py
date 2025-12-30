import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db

def _run_get_available_plan_ids(data) -> list:
    """
    Internal function to execute get_available_plan_ids logic.
    """
    db = data
    return [plan['plan_id'] for plan in db.get('plans', [])]


@tool
def get_available_plan_ids() -> list:
    """
    Get a list of all available plan IDs in the system.
    
    Returns:
        List of plan ID strings (e.g., ["P1001", "P1002", "P1003"])
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_get_available_plan_ids(data)
    except Exception as e:
        return f"Error executing get_available_plan_ids: {str(e)}"

    return result
