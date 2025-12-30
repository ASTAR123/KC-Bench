import sys
from pathlib import Path
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from smolagents import tool
from user_helpers import load_user_db, save_user_db

def _run_assert_internet_speed(data, min_speed_mbps: float) -> bool:
    """
    Internal function to execute assert_internet_speed logic.
    """
    user_db = data
    device = user_db.get('device', {})
    if device.get('wifi_connected', False):
        speed = 100.0
    else:
        network_tech = device.get('network_technology_connected', 'none')
        if network_tech == '5G':
            speed = 150.0
        elif network_tech == '4G':
            speed = 50.0
        elif network_tech == '3G':
            speed = 10.0
        else:
            speed = 0.0
    if speed < min_speed_mbps:
        raise AssertionError(f"Internet speed too low: expected >= {min_speed_mbps} Mbps, got {speed} Mbps")
    return True


@tool
def assert_internet_speed(min_speed_mbps: float) -> bool:
    """
    Assert that internet speed meets minimum requirement.
    
    Args:
        min_speed_mbps: Minimum speed in Mbps
    
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
        result = _run_assert_internet_speed(data, min_speed_mbps=min_speed_mbps)
    except Exception as e:
        raise RuntimeError(f"Error executing assert_internet_speed: {str(e)}")

    return result
