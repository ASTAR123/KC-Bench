import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_break_apn_mms_setting(data) -> str:
    """
    Internal function to execute break_apn_mms_setting logic.
    """
    user_db = data
    device = user_db.get('device', {})
    apn_settings = device.get('active_apn_settings', {})
    apn_settings['mms_apn'] = None
    apn_settings['mmsc_url'] = None
    device['active_apn_settings'] = apn_settings
    return "APN MMS settings broken"


@tool
def break_apn_mms_setting() -> str:
    """
    Break APN MMS settings specifically.
    
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
        result = _run_break_apn_mms_setting(data)
    except Exception as e:
        return f"Error executing break_apn_mms_setting: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
