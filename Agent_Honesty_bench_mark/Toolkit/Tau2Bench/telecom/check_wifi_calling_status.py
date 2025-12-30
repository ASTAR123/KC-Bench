import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_wifi_calling_status(data) -> dict:
    """
    Internal function to execute check_wifi_calling_status logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return {
        "enabled": device.get('wifi_calling_enabled', False),
        "mms_over_wifi": device.get('wifi_calling_mms_over_wifi', False)
    }


@tool
def check_wifi_calling_status() -> dict:
    """
    Check the WiFi calling status.
    
    Returns:
        Dictionary with WiFi calling information.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_wifi_calling_status(data)
    except Exception as e:
        return f"Error executing check_wifi_calling_status: {str(e)}"

    return result
