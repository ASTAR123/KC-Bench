import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_target_line

def _run_assert_data_refueling_amount(data, customer_id: str, line_id: str, expected_amount: float) -> bool:
    """
    Internal function to execute assert_data_refueling_amount logic.
    """
    db = data
    line = get_target_line(db, customer_id, line_id)
    actual_amount = line.get('data_refueling_gb', 0)
    if abs(actual_amount - expected_amount) > 1e-6:
        raise AssertionError(
            f"Data refueling amount mismatch for line {line_id}: "
            f"expected {expected_amount} GB, got {actual_amount} GB"
        )
    return True


@tool
def assert_data_refueling_amount(customer_id: str, line_id: str, expected_amount: float) -> bool:
    """
    Assert that the data refueling amount matches the expected value.
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID (e.g., "L1001")
        expected_amount: Expected data refueling amount in GB
    
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
        result = _run_assert_data_refueling_amount(data, customer_id=customer_id, line_id=line_id, expected_amount=expected_amount)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_data_refueling_amount: {str(e)}")

    return result
