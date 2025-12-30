import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_lock_sim_card(data, mode: str) -> str:
    """
    Internal function to execute lock_sim_card logic.
    """
    if mode not in ["pin", "puk"]:
        raise ValueError("Mode must be 'pin' or 'puk'")
    user_db = data
    device = user_db.get('device', {})
    if mode == "pin":
        device['sim_card_status'] = 'locked_pin'
    else:
        device['sim_card_status'] = 'locked_puk'
    device['network_connection_status'] = 'no_service'
    return f"SIM card locked with {mode.upper()}"


@tool
def lock_sim_card(mode: str) -> str:
    """
    Lock the SIM card with PIN or PUK.
    
    Args:
        mode: Lock mode ("pin" or "puk")
    
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
        result = _run_lock_sim_card(data, mode=mode)
    except Exception as e:
        return f"Error executing lock_sim_card: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
