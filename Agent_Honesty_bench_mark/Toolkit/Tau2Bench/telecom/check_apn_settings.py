import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_apn_settings(data) -> dict:
    """
    Internal function to execute check_apn_settings logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return device.get('active_apn_settings', {})


@tool
def check_apn_settings() -> dict:
    """
    Check the current APN settings.
    
    Returns:
        Dictionary with APN configuration.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_apn_settings(data)
    except Exception as e:
        return f"Error executing check_apn_settings: {str(e)}"

    return result
