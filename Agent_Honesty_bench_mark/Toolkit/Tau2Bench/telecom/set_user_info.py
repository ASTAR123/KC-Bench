import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_set_user_info(data, name: str, phone_number: str) -> str:
    """
    Internal function to execute set_user_info logic.
    """
    user_db = data
    if 'surroundings' not in user_db:
        user_db['surroundings'] = {}
    user_db['surroundings']['name'] = name
    user_db['surroundings']['phone_number'] = phone_number
    return f"User info set: {name}, {phone_number}"


@tool
def set_user_info(name: str, phone_number: str) -> str:
    """
    Set the user's name and phone number in the system.
    
    Args:
        name: The user's full name (e.g., "John Smith")
        phone_number: The user's phone number (e.g., "555-123-2001")
    
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
        result = _run_set_user_info(data, name=name, phone_number=phone_number)
    except Exception as e:
        return f"Error executing set_user_info: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
