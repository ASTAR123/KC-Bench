import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_toggle_wifi(data) -> bool:
    """
    Internal function to execute toggle_wifi logic.
    """
    user_db = data
    device = user_db.get('device', {})
    current_state = device.get('wifi_enabled', False)
    new_state = not current_state
    device['wifi_enabled'] = new_state
    if not new_state:
        device['wifi_connected'] = False
        device['wifi_signal_strength'] = 'none'
    return new_state


@tool
def toggle_wifi() -> bool:
    """
    Toggle WiFi on or off.
    
    Returns:
        New WiFi state (True=on, False=off).
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        raise RuntimeError(f"Error loading database: {str(e)}")

    # Execute operation
    try:
        result = _run_toggle_wifi(data)
    except Exception as e:
        raise RuntimeError(f"Error executing toggle_wifi: {str(e)}")

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        raise RuntimeError(f"Error saving database: {str(e)}")

    return result
