import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_set_wifi_calling(data, enabled: bool, mms_over_wifi: bool = None) -> str:
    """
    Internal function to execute set_wifi_calling logic.
    """
    user_db = data
    device = user_db.get('device', {})
    device['wifi_calling_enabled'] = enabled
    if mms_over_wifi is not None:
        device['wifi_calling_mms_over_wifi'] = mms_over_wifi
    status = "enabled" if enabled else "disabled"
    return f"WiFi calling {status}"


@tool
def set_wifi_calling(enabled: bool, mms_over_wifi: bool = None) -> str:
    """
    Set WiFi calling configuration.
    
    Args:
        enabled: Whether to enable WiFi calling
        mms_over_wifi: Whether to enable MMS over WiFi (optional)
    
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
        result = _run_set_wifi_calling(data, enabled=enabled, mms_over_wifi=mms_over_wifi)
    except Exception as e:
        return f"Error executing set_wifi_calling: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
