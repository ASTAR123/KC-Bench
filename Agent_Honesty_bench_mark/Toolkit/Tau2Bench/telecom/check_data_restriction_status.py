import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_data_restriction_status(data) -> dict:
    """
    Internal function to execute check_data_restriction_status logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return {
        "data_saver_mode": device.get('data_saver_mode', False)
    }


@tool
def check_data_restriction_status() -> dict:
    """
    Check data restriction and data saver mode status.
    
    Returns:
        Dictionary with data restriction information.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_data_restriction_status(data)
    except Exception as e:
        return f"Error executing check_data_restriction_status: {str(e)}"

    return result
