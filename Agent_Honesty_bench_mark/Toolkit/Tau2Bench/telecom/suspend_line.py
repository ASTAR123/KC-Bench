import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_target_line, get_today

def _run_suspend_line(data, customer_id: str, line_id: str) -> str:
    """
    Internal function to execute suspend_line logic.
    """
    db = data
    line = get_target_line(db, customer_id, line_id)
    if line.get('status') == 'Suspended':
        raise ValueError(f"Line {line_id} is already suspended")
    line['status'] = 'Suspended'
    line['suspension_start_date'] = str(get_today())
    return f"Line {line_id} has been suspended"


@tool
def suspend_line(customer_id: str, line_id: str) -> str:
    """
    Suspend a line (temporarily deactivate service).
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID to suspend (e.g., "L1001")
    
    Returns:
        Success message string.
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_suspend_line(data, customer_id=customer_id, line_id=line_id)
    except Exception as e:
        return f"Error executing suspend_line: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
