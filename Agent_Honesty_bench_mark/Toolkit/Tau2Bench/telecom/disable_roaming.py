import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_target_line

def _run_disable_roaming(data, customer_id: str, line_id: str) -> str:
    """
    Internal function to execute disable_roaming logic.
    """
    db = data
    line = get_target_line(db, customer_id, line_id)
    line['roaming_enabled'] = False
    return f"International roaming disabled for line {line_id}"


@tool
def disable_roaming(customer_id: str, line_id: str) -> str:
    """
    Disable international roaming for a line.
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID (e.g., "L1001")
    
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
        result = _run_disable_roaming(data, customer_id=customer_id, line_id=line_id)
    except Exception as e:
        return f"Error executing disable_roaming: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
