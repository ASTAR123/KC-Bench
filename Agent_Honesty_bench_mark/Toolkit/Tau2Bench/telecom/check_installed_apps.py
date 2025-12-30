import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_installed_apps(data) -> list:
    """
    Internal function to execute check_installed_apps logic.
    """
    user_db = data
    device = user_db.get('device', {})
    app_statuses = device.get('app_statuses', {})
    return list(app_statuses.keys())


@tool
def check_installed_apps() -> list:
    """
    Check list of installed apps.
    
    Returns:
        List of installed app names.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_installed_apps(data)
    except Exception as e:
        return f"Error executing check_installed_apps: {str(e)}"

    return result
