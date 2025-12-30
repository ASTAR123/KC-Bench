import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_run_speed_test(data) -> dict:
    """
    Internal function to execute run_speed_test logic.
    """
    user_db = data
    device = user_db.get('device', {})
    if device.get('airplane_mode', False):
        return {"speed_mbps": None, "status": "Airplane mode is on"}
    if not device.get('data_enabled', False) and not device.get('wifi_connected', False):
        return {"speed_mbps": None, "status": "No internet connection"}
    if device.get('wifi_connected', False):
        speed = 100.0  # WiFi typically faster
    else:
        network_tech = device.get('network_technology_connected', 'none')
        if network_tech == '5G':
            speed = 150.0
        elif network_tech == '4G':
            speed = 50.0
        elif network_tech == '3G':
            speed = 10.0
        else:
            speed = 1.0
    return {"speed_mbps": speed, "status": "excellent"}


@tool
def run_speed_test() -> dict:
    """
    Run an internet speed test.
    
    Returns:
        Dictionary with speed test results.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_run_speed_test(data)
    except Exception as e:
        return f"Error executing run_speed_test: {str(e)}"

    return result
