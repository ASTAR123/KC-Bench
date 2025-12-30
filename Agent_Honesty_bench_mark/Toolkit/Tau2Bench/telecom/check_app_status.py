import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_app_status(data, app_name: str) -> dict:
    """
    Internal function to execute check_app_status logic.
    """
    user_db = data
    device = user_db.get('device', {})
    app_statuses = device.get('app_statuses', {})
    if app_name not in app_statuses:
        raise ValueError(f"App {app_name} not found")
    return app_statuses[app_name]


@tool
def check_app_status(app_name: str) -> dict:
    """
    Check the status of a specific app.
    
    Args:
        app_name: The name of the app to check (e.g., "messaging", "browser")
    
    Returns:
        Dictionary with app status information.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_app_status(data, app_name=app_name)
    except Exception as e:
        return f"Error executing check_app_status: {str(e)}"

    return result
