"""Tool to process a payment for customer bills."""

import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))


from smolagents import tool
from data_helpers import load_db, save_db, get_customer_by_id, get_bill_by_id, get_today
import json


def _run_make_payment(data: dict, customer_id: str, payment_amount: float) -> str:
    """Internal function to execute payment logic."""

    customer = get_customer_by_id(data, customer_id)
    
    if not customer:
        return f"Error: Customer {customer_id} not found"
    
    if payment_amount <= 0:
        return "Error: Payment amount must be positive"
    
    bills_to_pay = []
    for bill_id in customer.get('bill_ids', []):
        bill = get_bill_by_id(data, bill_id)
        if bill and bill.get('status') in ['Awaiting Payment', 'Overdue']:
            bills_to_pay.append(bill)
    
    if not bills_to_pay:
        return "Error: No bills awaiting payment"
    
    bills_to_pay.sort(key=lambda b: b.get('due_date', ''))
    
    remaining_payment = payment_amount
    bills_paid = []
    
    for bill in bills_to_pay:
        if remaining_payment <= 0:
            break
        
        amount_due = bill.get('total_due', 0)
        payment_for_bill = min(remaining_payment, amount_due)
        
        if 'line_items' not in bill:
            bill['line_items'] = []
        
        bill['line_items'].append({
            'description': 'Payment',
            'amount': -payment_for_bill,
            'date': str(get_today()),
            'item_type': 'Payment'
        })
        
        bill['total_due'] -= payment_for_bill
        remaining_payment -= payment_for_bill
        
        if bill['total_due'] <= 0.01:
            bill['status'] = 'Paid'
            bill['total_due'] = 0
        
        bills_paid.append(bill['bill_id'])
    
    result = {
        "message": f"Payment of ${payment_amount:.2f} processed successfully",
        "amount_paid": payment_amount - remaining_payment,
        "bills_paid": bills_paid,
        "remaining_balance": remaining_payment
    }
    
    return json.dumps(result, ensure_ascii=False)


@tool
def make_payment(customer_id: str, payment_amount: float) -> str:
    """
    Process a payment for a customer's outstanding bills.
    
    Args:
        customer_id: The customer ID making the payment (e.g., "C1001")
        payment_amount: The payment amount in USD (e.g., 100.50)
    
    Returns:
        JSON string containing payment details or error message.
    """
    try:
        data = load_db()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    
    try:
        result = _run_make_payment(data, customer_id=customer_id, payment_amount=payment_amount)
    except Exception as exc:
        return f"Error executing make_payment: {exc}"
    
    if isinstance(result, str) and result.startswith('Error'):
        return result
    
    try:
        save_db(data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    
    return result
