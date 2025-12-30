import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_target_line

def _run_assert_line_status(data, customer_id: str, line_id: str, expected_status: str) -> bool:
    """
    Internal function to execute assert_line_status logic.
    """
    db = data
    line = get_target_line(db, customer_id, line_id)
    actual_status = line.get('status')
    if actual_status != expected_status:
        raise AssertionError(
            f"Line status mismatch for line {line_id}: "
            f"expected '{expected_status}', got '{actual_status}'"
        )
    return True


@tool
def assert_line_status(customer_id: str, line_id: str, expected_status: str) -> bool:
    """
    Assert that the line status matches the expected value.
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID (e.g., "L1001")
        expected_status: Expected line status (Active, Suspended, Pending Activation, Closed)
    
    Returns:
        True if the assertion passes.
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        raise RuntimeError(f"Error loading database: {str(e)}")

    # Execute operation
    try:
        result = _run_assert_line_status(data, customer_id=customer_id, line_id=line_id, expected_status=expected_status)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_line_status: {str(e)}")

    return result
