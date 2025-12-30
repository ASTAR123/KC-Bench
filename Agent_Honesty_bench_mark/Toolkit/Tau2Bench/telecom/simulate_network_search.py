import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_simulate_network_search(data) -> str:
    """
    Internal function to execute simulate_network_search logic.
    """
    user_db = data
    device = user_db.get('device', {})
    if device.get('airplane_mode', False):
        return "Cannot search for network in airplane mode"
    if device.get('sim_card_status') != 'active':
        return "Cannot search for network with inactive SIM"
    device['network_connection_status'] = 'connected'
    device['network_technology_connected'] = '5G'
    device['network_signal_strength'] = 'good'
    return "Network search completed, connected to 5G"


@tool
def simulate_network_search() -> str:
    """
    Simulate a network search and reconnection.
    
    Returns:
        Result message.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_simulate_network_search(data)
    except Exception as e:
        return f"Error executing simulate_network_search: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
