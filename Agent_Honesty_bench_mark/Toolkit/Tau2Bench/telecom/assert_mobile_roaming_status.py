import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_assert_mobile_roaming_status(data, expected_status: bool) -> bool:
    """
    Internal function to execute assert_mobile_roaming_status logic.
    """
    user_db = data
    device = user_db.get('device', {})
    actual_status = device.get('roaming_enabled', False)
    if actual_status != expected_status:
        raise AssertionError(f"Roaming status mismatch: expected {expected_status}, got {actual_status}")
    return True


@tool
def assert_mobile_roaming_status(expected_status: bool) -> bool:
    """
    Assert that mobile roaming status matches expected value.
    
    Args:
        expected_status: Expected roaming status (True=on, False=off)
    
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
        result = _run_assert_mobile_roaming_status(data, expected_status=expected_status)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_mobile_roaming_status: {str(e)}")

    return result
