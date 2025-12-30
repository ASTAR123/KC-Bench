import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_customer_by_id, get_bill_by_id

def _run_assert_overdue_bill_exists(data, customer_id: str, overdue_bill_id: str) -> bool:
    """
    Internal function to execute assert_overdue_bill_exists logic.
    """
    db = data
    customer = get_customer_by_id(db, customer_id)
    if not customer:
        raise ValueError(f"Customer {customer_id} not found")
    if overdue_bill_id not in customer.get('bill_ids', []):
        raise AssertionError(f"Overdue bill {overdue_bill_id} not found for customer {customer_id}")
    bill = get_bill_by_id(db, overdue_bill_id)
    if not bill:
        raise AssertionError(f"Bill {overdue_bill_id} not found in database")
    if bill.get('status') != 'Overdue':
        raise AssertionError(f"Bill {overdue_bill_id} is not overdue, status is {bill.get('status')}")
    return True


@tool
def assert_overdue_bill_exists(customer_id: str, overdue_bill_id: str) -> bool:
    """
    Assert that an overdue bill exists for a customer.
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        overdue_bill_id: The bill ID to check (e.g., "B1001")
    
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
        result = _run_assert_overdue_bill_exists(data, customer_id=customer_id, overdue_bill_id=overdue_bill_id)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_overdue_bill_exists: {str(e)}")

    return result
