import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_target_line

def _run_set_data_usage(data, customer_id: str, line_id: str, data_used_gb: float) -> str:
    """
    Internal function to execute set_data_usage logic.
    """
    db = data
    line = get_target_line(db, customer_id, line_id)
    if data_used_gb < 0:
        raise ValueError("Data usage cannot be negative")
    line['data_used_gb'] = data_used_gb
    return f"Data usage for line {line_id} set to {data_used_gb} GB"


@tool
def set_data_usage(customer_id: str, line_id: str, data_used_gb: float) -> str:
    """
    Set the data usage for a line (typically used for testing/simulation).
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID (e.g., "L1001")
        data_used_gb: Amount of data used in GB (e.g., 3.5)
    
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
        result = _run_set_data_usage(data, customer_id=customer_id, line_id=line_id, data_used_gb=data_used_gb)
    except Exception as e:
        return f"Error executing set_data_usage: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
