import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db, check_can_send_mms

def _run_can_send_mms(data) -> bool:
    """
    Internal function to execute can_send_mms logic.
    """
    user_db = data
    device = user_db.get('device', {})
    return check_can_send_mms(device)


@tool
def can_send_mms() -> bool:
    """
    Check if the device can currently send MMS messages.
    
    Returns:
        True if MMS can be sent, False otherwise.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        raise RuntimeError(f"Error loading database: {str(e)}")

    # Execute operation
    try:
        result = _run_can_send_mms(data)
    except Exception as e:
        raise RuntimeError(f"Error executing can_send_mms: {str(e)}")

    return result
