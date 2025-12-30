import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_reset_apn_settings(data) -> str:
    """
    Internal function to execute reset_apn_settings logic.
    """
    user_db = data
    device = user_db.get('device', {})
    device['active_apn_settings'] = {
        'apn_name': 'internet',
        'mms_apn': 'mms',
        'mmsc_url': 'http://mms.carrier.com/mms/wapenc'
    }
    return "APN settings reset to default"


@tool
def reset_apn_settings() -> str:
    """
    Reset APN settings to default values.
    
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
        result = _run_reset_apn_settings(data)
    except Exception as e:
        return f"Error executing reset_apn_settings: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
