import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_vpn_status(data) -> dict:
    """
    Internal function to execute check_vpn_status logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return {
        "enabled_setting": device.get('vpn_enabled_setting', False),
        "connected": device.get('vpn_connected', False)
    }


@tool
def check_vpn_status() -> dict:
    """
    Check the VPN connection status.
    
    Returns:
        Dictionary with VPN status information.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_vpn_status(data)
    except Exception as e:
        return f"Error executing check_vpn_status: {str(e)}"

    return result
