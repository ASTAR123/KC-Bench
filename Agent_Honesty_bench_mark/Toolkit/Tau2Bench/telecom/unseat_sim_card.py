import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_unseat_sim_card(data) -> str:
    """
    Internal function to execute unseat_sim_card logic.
    """
    user_db = data
    device = user_db.get('device', {})
    device['sim_card_missing'] = True
    device['sim_card_status'] = 'missing'
    device['network_connection_status'] = 'no_service'
    return "SIM card removed"


@tool
def unseat_sim_card() -> str:
    """
    Remove the SIM card from the device.
    
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
        result = _run_unseat_sim_card(data)
    except Exception as e:
        return f"Error executing unseat_sim_card: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
