import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_turn_airplane_mode_on(data) -> str:
    """
    Internal function to execute turn_airplane_mode_on logic.
    """
    user_db = data
    device = user_db.get('device', {})
    device['airplane_mode'] = True
    device['data_enabled'] = False
    device['wifi_connected'] = False
    device['network_connection_status'] = 'no_service'
    device['network_technology_connected'] = 'none'
    device['network_signal_strength'] = 'none'
    return "Airplane mode turned on"


@tool
def turn_airplane_mode_on() -> str:
    """
    Turn airplane mode on.
    
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
        result = _run_turn_airplane_mode_on(data)
    except Exception as e:
        return f"Error executing turn_airplane_mode_on: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
