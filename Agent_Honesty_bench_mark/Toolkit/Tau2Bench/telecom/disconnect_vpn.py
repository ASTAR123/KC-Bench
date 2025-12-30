import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_disconnect_vpn(data) -> bool:
    """
    Internal function to execute disconnect_vpn logic.
    """
    user_db = data
    device = user_db.get('device', {})
    device['vpn_connected'] = False
    return False


@tool
def disconnect_vpn() -> bool:
    """
    Disconnect from VPN.
    
    Returns:
        VPN connection status (False=disconnected).
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        raise RuntimeError(f"Error loading database: {str(e)}")

    # Execute operation
    try:
        result = _run_disconnect_vpn(data)
    except Exception as e:
        raise RuntimeError(f"Error executing disconnect_vpn: {str(e)}")

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        raise RuntimeError(f"Error saving database: {str(e)}")

    return result
