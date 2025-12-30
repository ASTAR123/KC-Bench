import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_wifi_status(data) -> dict:
    """
    Internal function to execute check_wifi_status logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return {
        "enabled": device.get('wifi_enabled', False),
        "connected": device.get('wifi_connected', False),
        "signal_strength": device.get('wifi_signal_strength', 'none')
    }


@tool
def check_wifi_status() -> dict:
    """
    Check the WiFi connection status.
    
    Returns:
        Dictionary with WiFi status information.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_wifi_status(data)
    except Exception as e:
        return f"Error executing check_wifi_status: {str(e)}"

    return result
