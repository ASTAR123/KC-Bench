import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, check_can_send_mms

def _run_assert_can_send_mms(data, expected: bool) -> bool:
    """
    Internal function to execute assert_can_send_mms logic.
    """
    user_db = data
    device = user_db.get('device', {})
    actual = check_can_send_mms(device)
    if actual != expected:
        raise AssertionError(f"MMS capability mismatch: expected {expected}, got {actual}")
    return True


@tool
def assert_can_send_mms(expected: bool) -> bool:
    """
    Assert that MMS sending capability matches expected value.
    
    Args:
        expected: Expected MMS capability (True=can send, False=cannot send)
    
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
        result = _run_assert_can_send_mms(data, expected=expected)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_can_send_mms: {str(e)}")

    return result
