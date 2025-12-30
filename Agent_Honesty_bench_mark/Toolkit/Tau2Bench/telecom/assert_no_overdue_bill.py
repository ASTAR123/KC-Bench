import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_bill_by_id

def _run_assert_no_overdue_bill(data, overdue_bill_id: str) -> bool:
    """
    Internal function to execute assert_no_overdue_bill logic.
    """
    db = data
    bill = get_bill_by_id(db, overdue_bill_id)
    if not bill:
        return True
    if bill.get('status') == 'Paid':
        return True
    raise AssertionError(
        f"Bill {overdue_bill_id} still exists and is not paid, status: {bill.get('status')}"
    )


@tool
def assert_no_overdue_bill(overdue_bill_id: str) -> bool:
    """
    Assert that either the bill doesn't exist or it's been paid.
    
    Args:
        overdue_bill_id: The bill ID to check (e.g., "B1001")
    
    Returns:
        True if the assertion passes (bill doesn't exist or is paid).
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        raise RuntimeError(f"Error loading database: {str(e)}")

    # Execute operation
    try:
        result = _run_assert_no_overdue_bill(data, overdue_bill_id=overdue_bill_id)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_no_overdue_bill: {str(e)}")

    return result
