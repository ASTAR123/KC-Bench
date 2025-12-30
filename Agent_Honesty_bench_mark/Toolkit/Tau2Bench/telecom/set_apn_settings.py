import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_set_apn_settings(data, apn_name: str, mms_apn: str = None, mmsc_url: str = None) -> str:
    """
    Internal function to execute set_apn_settings logic.
    """
    user_db = data
    device = user_db.get('device', {})
    apn_settings = device.get('active_apn_settings', {})
    apn_settings['apn_name'] = apn_name
    if mms_apn:
        apn_settings['mms_apn'] = mms_apn
    if mmsc_url:
        apn_settings['mmsc_url'] = mmsc_url
    device['active_apn_settings'] = apn_settings
    return f"APN settings updated: {apn_name}"


@tool
def set_apn_settings(apn_name: str, mms_apn: str = None, mmsc_url: str = None) -> str:
    """
    Set APN settings for data and MMS.
    
    Args:
        apn_name: The APN name (e.g., "internet")
        mms_apn: The MMS APN name (optional)
        mmsc_url: The MMSC URL (optional)
    
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
        result = _run_set_apn_settings(data, apn_name=apn_name, mms_apn=mms_apn, mmsc_url=mmsc_url)
    except Exception as e:
        return f"Error executing set_apn_settings: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
