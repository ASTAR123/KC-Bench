import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_network_mode_preference(data) -> str:
    """
    Internal function to execute check_network_mode_preference logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return device.get('network_mode_preference', '4g_5g_preferred')


@tool
def check_network_mode_preference() -> str:
    """
    Check the current network mode preference setting.
    
    Returns:
        Network mode preference (e.g., "4g_5g_preferred", "4g_only", "3g_only", "2g_only").
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_network_mode_preference(data)
    except Exception as e:
        return f"Error executing check_network_mode_preference: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    return result
