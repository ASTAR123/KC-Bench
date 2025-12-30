import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_reboot_device(data) -> str:
    """
    Internal function to execute reboot_device logic.
    """
    user_db = data
    device = user_db.get('device', {})
    apn_settings = device.get('active_apn_settings', {})
    if apn_settings.get('reset_at_reboot', False):
        device['active_apn_settings'] = {
            'apn_name': 'internet',
            'mms_apn': 'mms',
            'mmsc_url': 'http://mms.carrier.com/mms/wapenc'
        }
    return "Device rebooted"


@tool
def reboot_device() -> str:
    """
    Reboot the device (resets some temporary states).
    
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
        result = _run_reboot_device(data)
    except Exception as e:
        return f"Error executing reboot_device: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
