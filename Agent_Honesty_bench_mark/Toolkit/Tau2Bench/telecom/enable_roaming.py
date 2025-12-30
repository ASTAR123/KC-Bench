import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_target_line

def _run_enable_roaming(data, customer_id: str, line_id: str) -> dict:
    """
    Internal function to execute enable_roaming logic.
    """
    db = data
    line = get_target_line(db, customer_id, line_id)
    if line.get('status') != 'Active':
        raise ValueError(f"Line must be active to enable roaming. Current status: {line.get('status')}")
    line['roaming_enabled'] = True
    return {
        "message": f"International roaming enabled for line {line_id}",
        "roaming_enabled": True
    }


@tool
def enable_roaming(customer_id: str, line_id: str) -> dict:
    """
    Enable international roaming for a line.
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID (e.g., "L1001")
    
    Returns:
        Dictionary containing roaming status.
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_enable_roaming(data, customer_id=customer_id, line_id=line_id)
    except Exception as e:
        return f"Error executing enable_roaming: {str(e)}"

    # Save data
    try:
        save_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
