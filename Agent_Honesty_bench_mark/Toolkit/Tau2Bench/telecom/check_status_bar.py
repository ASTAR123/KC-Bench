import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_status_bar(data) -> str:
    """
    Internal function to execute check_status_bar logic.
    """
    user_db = data
    device = user_db.get('device', {})
    status_parts = []
    signal = device.get('network_signal_strength', 'none')
    status_parts.append(f"Signal: {signal}")
    network = device.get('network_technology_connected', 'none')
    if network != 'none':
        status_parts.append(f"Network: {network}")
    if device.get('wifi_connected', False):
        status_parts.append("WiFi: Connected")
    if device.get('airplane_mode', False):
        status_parts.append("Airplane Mode: ON")
    if device.get('vpn_connected', False):
        status_parts.append("VPN: Active")
    if device.get('data_saver_mode', False):
        status_parts.append("Data Saver: ON")
    battery = device.get('battery_level', 100)
    status_parts.append(f"Battery: {battery}%")
    return " | ".join(status_parts)


@tool
def check_status_bar() -> str:
    """
    Check the device status bar for network and system status.
    
    Returns:
        String describing the current status bar information.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_status_bar(data)
    except Exception as e:
        return f"Error executing check_status_bar: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    return result
