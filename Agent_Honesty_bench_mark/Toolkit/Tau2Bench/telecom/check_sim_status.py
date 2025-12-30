import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_sim_status(data) -> dict:
    """
    Internal function to execute check_sim_status logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return {
        "status": device.get('sim_card_status', 'active'),
        "missing": device.get('sim_card_missing', False)
    }


@tool
def check_sim_status() -> dict:
    """
    Check the SIM card status.
    
    Returns:
        Dictionary with SIM status information.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_sim_status(data)
    except Exception as e:
        return f"Error executing check_sim_status: {str(e)}"

    return result
