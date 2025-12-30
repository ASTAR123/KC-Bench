import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_check_app_permissions(data, app_name: str) -> dict:
    """
    Internal function to execute check_app_permissions logic.
    """
    user_db = data
    device = user_db.get('device', {})
    app_statuses = device.get('app_statuses', {})
    if app_name not in app_statuses:
        raise ValueError(f"App {app_name} not found")
    return app_statuses[app_name].get('permissions', {})


@tool
def check_app_permissions(app_name: str) -> dict:
    """
    Check the permissions for a specific app.
    
    Args:
        app_name: The name of the app (e.g., "messaging", "browser")
    
    Returns:
        Dictionary with app permissions.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_check_app_permissions(data, app_name=app_name)
    except Exception as e:
        return f"Error executing check_app_permissions: {str(e)}"

    return result
