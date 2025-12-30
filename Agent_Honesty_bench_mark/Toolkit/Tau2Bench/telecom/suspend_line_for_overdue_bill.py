import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_line_by_id, get_plan_by_id, get_customer_by_id, get_bill_by_id, get_today

def _run_suspend_line_for_overdue_bill(data, customer_id: str, line_id: str, new_bill_id: str, contract_ended: bool) -> str:
    """
    Internal function to execute suspend_line_for_overdue_bill logic.
    """
    db = data
    line = get_line_by_id(db, line_id)
    if not line:
        raise ValueError(f"Line {line_id} not found")
    if line.get('status') != 'Active':
        raise ValueError("Line must be active to suspend for unpaid bill")
    plan = get_plan_by_id(db, line['plan_id'])
    amount = plan['price_per_month']
    description = f"Charge for line {line['line_id']}"
    if amount <= 0:
        raise ValueError("Amount must be positive for overdue bill")
    customer = get_customer_by_id(db, customer_id)
    if not customer:
        raise ValueError(f"Customer {customer_id} not found")
    overdue_bill_ids = []
    for bill_id in customer.get('bill_ids', []):
        bill = get_bill_by_id(db, bill_id)
        if bill and bill.get('status') == 'Overdue':
            overdue_bill_ids.append(bill_id)
    if len(overdue_bill_ids) > 0:
        raise ValueError("Customer already has an overdue bill")
    today = get_today()
    first_day_of_last_month = today.replace(day=1) - timedelta(days=1)
    first_day_of_last_month = first_day_of_last_month.replace(day=1)
    last_day_of_last_month = today.replace(day=1) - timedelta(days=1)
    overdue_bill = {
        'bill_id': new_bill_id,
        'customer_id': customer_id,
        'period_start': str(first_day_of_last_month),
        'period_end': str(last_day_of_last_month),
        'issue_date': str(first_day_of_last_month),
        'total_due': amount,
        'due_date': str(first_day_of_last_month + timedelta(days=14)),
        'status': 'Overdue',
        'line_items': [{
            'description': description,
            'amount': amount,
            'date': str(get_today()),
            'item_type': 'Charge'
        }]
    }
    db['bills'].append(overdue_bill)
    customer['bill_ids'].append(new_bill_id)
    line['status'] = 'Suspended'
    line['suspension_start_date'] = str(get_today())
    if contract_ended:
        line['contract_end_date'] = str(last_day_of_last_month)
    return f"Line {line_id} suspended for unpaid bill {new_bill_id}. Contract ended: {contract_ended}"


@tool
def suspend_line_for_overdue_bill(customer_id: str, line_id: str, new_bill_id: str, contract_ended: bool) -> str:
    """
    Suspend a line for an unpaid bill and create an overdue bill.
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID to suspend (e.g., "L1001")
        new_bill_id: The ID for the new overdue bill (e.g., "B1010")
        contract_ended: Whether the contract has ended (True/False)
    
    Returns:
        Success message string.
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_suspend_line_for_overdue_bill(data, customer_id=customer_id, line_id=line_id, new_bill_id=new_bill_id, contract_ended=contract_ended)
    except Exception as e:
        return f"Error executing suspend_line_for_overdue_bill: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
