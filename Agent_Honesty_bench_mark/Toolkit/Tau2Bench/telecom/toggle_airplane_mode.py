import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_toggle_airplane_mode(data) -> bool:
    """
    Internal function to execute toggle_airplane_mode logic.
    """
    user_db = data
    device = user_db.get('device', {})
    current_state = device.get('airplane_mode', False)
    new_state = not current_state
    device['airplane_mode'] = new_state
    if new_state:
        device['data_enabled'] = False
        device['wifi_connected'] = False
        device['network_connection_status'] = 'no_service'
        device['network_technology_connected'] = 'none'
        device['network_signal_strength'] = 'none'
    return new_state


@tool
def toggle_airplane_mode() -> bool:
    """
    Toggle airplane mode on or off.
    
    Returns:
        New airplane mode state (True=on, False=off).
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        raise RuntimeError(f"Error loading database: {str(e)}")

    # Execute operation
    try:
        result = _run_toggle_airplane_mode(data)
    except Exception as e:
        raise RuntimeError(f"Error executing toggle_airplane_mode: {str(e)}")

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        raise RuntimeError(f"Error saving database: {str(e)}")

    return result
