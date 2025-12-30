import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_reseat_sim_card(data) -> str:
    """
    Internal function to execute reseat_sim_card logic.
    """
    user_db = data
    device = user_db.get('device', {})
    device['sim_card_missing'] = False
    device['sim_card_status'] = 'active'
    return "SIM card reseated successfully"


@tool
def reseat_sim_card() -> str:
    """
    Reseat the SIM card (remove and reinsert).
    
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
        result = _run_reseat_sim_card(data)
    except Exception as e:
        return f"Error executing reseat_sim_card: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
