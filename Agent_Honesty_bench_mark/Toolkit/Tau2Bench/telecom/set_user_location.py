import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_set_user_location(data, abroad: bool) -> str:
    """
    Internal function to execute set_user_location logic.
    """
    user_db = data
    if 'surroundings' not in user_db:
        user_db['surroundings'] = {}
    user_db['surroundings']['is_abroad'] = abroad
    location = "abroad" if abroad else "in home country"
    return f"User location set: {location}"


@tool
def set_user_location(abroad: bool) -> str:
    """
    Set whether the user is currently abroad or in their home country.
    
    Args:
        abroad: True if user is abroad, False if in home country
    
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
        result = _run_set_user_location(data, abroad=abroad)
    except Exception as e:
        return f"Error executing set_user_location: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
