import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_set_network_mode_preference(data, mode: str) -> str:
    """
    Internal function to execute set_network_mode_preference logic.
    """
    valid_modes = ["4g_5g_preferred", "4g_only", "3g_only", "2g_only"]
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode. Must be one of: {', '.join(valid_modes)}")
    user_db = data
    if 'device' not in user_db:
        user_db['device'] = {}
    user_db['device']['network_mode_preference'] = mode
    return f"Network mode preference set to {mode}"


@tool
def set_network_mode_preference(mode: str) -> str:
    """
    Set the network mode preference.
    
    Args:
        mode: Network mode to set ("4g_5g_preferred", "4g_only", "3g_only", "2g_only")
    
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
        result = _run_set_network_mode_preference(data, mode=mode)
    except Exception as e:
        return f"Error executing set_network_mode_preference: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
