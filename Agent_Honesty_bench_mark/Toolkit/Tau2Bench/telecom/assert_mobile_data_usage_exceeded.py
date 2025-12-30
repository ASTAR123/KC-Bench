import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_assert_mobile_data_usage_exceeded(data, customer_id: str, line_id: str) -> bool:
    """
    Internal function to execute assert_mobile_data_usage_exceeded logic.
    """
    from data_helpers import get_target_line, get_plan_by_id
    db = data
    line = get_target_line(db, customer_id, line_id)
    plan = get_plan_by_id(db, line['plan_id'])
    data_used = line.get('data_used_gb', 0)
    data_refueling = line.get('data_refueling_gb', 0)
    data_limit = plan['data_limit_gb'] + data_refueling
    if data_used <= data_limit:
        raise AssertionError(f"Data usage ({data_used} GB) has not exceeded limit ({data_limit} GB)")
    return True


@tool
def assert_mobile_data_usage_exceeded(customer_id: str, line_id: str) -> bool:
    """
    Assert that mobile data usage has exceeded the plan limit.
    
    Args:
        customer_id: Customer ID
        line_id: Line ID
    
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
        result = _run_assert_mobile_data_usage_exceeded(data, customer_id=customer_id, line_id=line_id)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_mobile_data_usage_exceeded: {str(e)}")

    return result
