import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_assert_internet_not_excellent(data) -> bool:
    """
    Internal function to execute assert_internet_not_excellent logic.
    """
    user_db = data
    device = user_db.get('device', {})
    if device.get('wifi_connected', False):
        is_excellent = True
    else:
        network_tech = device.get('network_technology_connected', 'none')
        is_excellent = network_tech in ['5G', '4G']
    if is_excellent:
        raise AssertionError("Internet connection is excellent when it should not be")
    return True


@tool
def assert_internet_not_excellent() -> bool:
    """
    Assert that internet connection is not at excellent level.
    
    Returns:
        True if assertion passes.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        raise RuntimeError(f"Error loading database: {str(e)}")

    # Execute operation
    try:
        result = _run_assert_internet_not_excellent(data)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_internet_not_excellent: {str(e)}")

    return result
