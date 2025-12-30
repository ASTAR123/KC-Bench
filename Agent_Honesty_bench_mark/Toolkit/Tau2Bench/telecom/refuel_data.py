import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from data_helpers import load_db, save_db, get_target_line, get_plan_by_id

def _run_refuel_data(data, customer_id: str, line_id: str, gb_amount: float) -> dict:
    """
    Internal function to execute refuel_data logic.
    """
    db = data
    line = get_target_line(db, customer_id, line_id)
    if gb_amount <= 0:
        raise ValueError("Data amount must be positive")
    plan = get_plan_by_id(db, line['plan_id'])
    if not plan:
        raise ValueError(f"Plan {line['plan_id']} not found")
    charge_amount = gb_amount * plan['data_refueling_price_per_gb']
    line['data_refueling_gb'] = line.get('data_refueling_gb', 0) + gb_amount
    return {
        "message": f"Successfully added {gb_amount} GB of data for line {line_id} for ${charge_amount:.2f}",
        "new_data_refueling_gb": line['data_refueling_gb'],
        "charge": charge_amount
    }


@tool
def refuel_data(customer_id: str, line_id: str, gb_amount: float) -> dict:
    """
    Add additional data allowance to a line (data refueling).
    
    Args:
        customer_id: The customer ID (e.g., "C1001")
        line_id: The line ID to refuel (e.g., "L1001")
        gb_amount: Amount of data to add in GB (e.g., 5.0)
    
    Returns:
        Dictionary containing refueling details.
    """
    # Load data
    try:
        data = load_db()
    except Exception as e:
        return f"Error loading database: {str(e)}"

    # Execute operation
    try:
        result = _run_refuel_data(data, customer_id=customer_id, line_id=line_id, gb_amount=gb_amount)
    except Exception as e:
        return f"Error executing refuel_data: {str(e)}"

    # Save data
    try:
        save_db(data)
    except Exception as e:
        return f"Error saving database: {str(e)}"

    return result
