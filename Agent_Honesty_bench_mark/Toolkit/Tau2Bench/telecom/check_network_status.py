import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_network_status(data) -> dict:
    """
    Internal function to execute check_network_status logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return {
        "signal_strength": device.get('network_signal_strength', 'none'),
        "network_technology": device.get('network_technology_connected', 'none'),
        "connection_status": device.get('network_connection_status', 'no_service'),
        "data_enabled": device.get('data_enabled', False),
        "roaming_enabled": device.get('roaming_enabled', False),
        "airplane_mode": device.get('airplane_mode', False)
    }


@tool
def check_network_status() -> dict:
    """
    Check the current network status of the device.
    
    Returns:
        Dictionary containing network status information.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_network_status(data)
    except Exception as e:
        return f"Error executing check_network_status: {str(e)}"

    return result
