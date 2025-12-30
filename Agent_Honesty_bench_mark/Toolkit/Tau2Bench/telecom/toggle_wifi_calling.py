import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_toggle_wifi_calling(data) -> bool:
    """
    Internal function to execute toggle_wifi_calling logic.
    """
    user_db = data
    device = user_db.get('device', {})
    current_state = device.get('wifi_calling_enabled', False)
    new_state = not current_state
    device['wifi_calling_enabled'] = new_state
    return new_state


@tool
def toggle_wifi_calling() -> bool:
    """
    Toggle WiFi calling on or off.
    
    Returns:
        New WiFi calling state (True=on, False=off).
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        raise RuntimeError(f"Error loading database: {str(e)}")

    # Execute operation
    try:
        result = _run_toggle_wifi_calling(data)
    except Exception as e:
        raise RuntimeError(f"Error executing toggle_wifi_calling: {str(e)}")

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        raise RuntimeError(f"Error saving database: {str(e)}")

    return result
