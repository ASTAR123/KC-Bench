import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_send_payment_request(data, amount: float, description: str) -> str:
    """
    Internal function to execute send_payment_request logic.
    """
    return f"Payment request sent for ${amount}: {description}"


@tool
def send_payment_request(amount: float, description: str) -> str:
    """
    Send a payment request (placeholder).
    
    Args:
        amount: Payment amount
        description: Payment description
    
    Returns:
        Confirmation message.
    """
    # Load data
    try:
        data = load_user_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_send_payment_request(data, amount=amount, description=description)
    except Exception as e:
        return f"Error executing send_payment_request: {str(e)}"

    # Check for errors
    if isinstance(result, str) and result.startswith("Error:"):
        return result

    # Save data
    try:
        save_user_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
