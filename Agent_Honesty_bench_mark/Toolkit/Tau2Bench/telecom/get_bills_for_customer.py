import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_customer_by_id, get_bill_by_id

def _run_get_bills_for_customer(data, customer_id: str) -> list:
    """
    Internal function to execute get_bills_for_customer logic.
    """
    db = data
    customer = get_customer_by_id(db, customer_id)
    if not customer:
        raise ValueError(f"Customer {customer_id} not found")
    bills = []
    for bill_id in customer.get('bill_ids', []):
        bill = get_bill_by_id(db, bill_id)
        if bill:
            bills.append(bill)
    return bills


@tool
def get_bills_for_customer(customer_id: str) -> list:
    """
    Retrieve all bills associated with a customer.
    
    Args:
        customer_id: The unique customer identifier (e.g., "C1001")
    
    Returns:
        List of bill dictionaries containing bill details.
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_get_bills_for_customer(data, customer_id=customer_id)
    except Exception as e:
        return f"Error executing get_bills_for_customer: {str(e)}"

    return result
