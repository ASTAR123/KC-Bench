import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_break_vpn(data) -> str:
    """
    Internal function to execute break_vpn logic.
    """
    user_db = data
    device = user_db.get('device', {})
    device['vpn_enabled_setting'] = True
    device['vpn_connected'] = False
    return "VPN connection broken"


@tool
def break_vpn() -> str:
    """
    Break VPN connection (simulate VPN failure).
    
    Returns:
        Confirmation message.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_break_vpn(data)
    except Exception as e:
        return f"Error executing break_vpn: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
