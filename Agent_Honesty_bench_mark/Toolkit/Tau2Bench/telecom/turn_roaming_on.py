import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_turn_roaming_on(data) -> str:
    """
    Internal function to execute turn_roaming_on logic.
    """
    user_db = data
    device = user_db.get('device', {})
    device['roaming_enabled'] = True
    return "Data roaming turned on"


@tool
def turn_roaming_on() -> str:
    """
    Turn data roaming on.
    
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
        result = _run_turn_roaming_on(data)
    except Exception as e:
        return f"Error executing turn_roaming_on: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
