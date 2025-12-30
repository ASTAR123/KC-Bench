import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_remove_app_permission(data, app_name: str, permission: str) -> str:
    """
    Internal function to execute remove_app_permission logic.
    """
    user_db = data
    device = user_db.get('device', {})
    app_statuses = device.get('app_statuses', {})
    if app_name not in app_statuses:
        raise ValueError(f"App {app_name} not found")
    if 'permissions' in app_statuses[app_name]:
        app_statuses[app_name]['permissions'][permission] = False
    return f"Removed {permission} permission from {app_name}"


@tool
def remove_app_permission(app_name: str, permission: str) -> str:
    """
    Remove a permission from an app.
    
    Args:
        app_name: The name of the app (e.g., "messaging")
        permission: The permission to remove (e.g., "sms", "storage", "phone", "network")
    
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
        result = _run_remove_app_permission(data, app_name=app_name, permission=permission)
    except Exception as e:
        return f"Error executing remove_app_permission: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
