from pathlib import Path
import json
from typing import Dict
from smolagents import tool
from Utils.environment_utils import get_task_environment_resources

_LABEL_HINTS = ('tau2_airline_data', 'airline_data')
_DOMAIN = 'airline'

def _locate_domain_base() -> Path:
    resources = get_task_environment_resources()
    for resource in resources:
        path_value = resource.get('path')
        if not path_value:
            continue
        candidate = Path(path_value)
        if candidate.is_file():
            candidate = candidate.parent
        label = (resource.get('label') or '').lower()
        normalized = str(candidate).lower()
        if label in _LABEL_HINTS or any(hint in label for hint in _LABEL_HINTS):
            return candidate
        if f"tau2bench/{_DOMAIN}" in normalized or normalized.endswith(f"{_DOMAIN}/data"):
            return candidate
    raise FileNotFoundError(f"Tau2Bench environment for domain '{_DOMAIN}' not found.")

def _load_domain_data():
    base = _locate_domain_base()
    db_path = base / "db.json"
    with db_path.open('r', encoding='utf-8') as file:
        return json.load(file), base

def _save_domain_data(base: Path, data: dict):
    db_path = base / "db.json"
    with db_path.open('w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

def _run_get_flight_status(data: Dict, flight_number: str, date: str) -> str:
    flights = data["flights"]
    if flight_number not in flights:
        return f"Error: Flight {flight_number} not found"
    
    flight = flights[flight_number]
    if date not in flight.get("dates", {}):
        return f"Error: Flight {flight_number} not found on date {date}"
    
    return flight["dates"][date].get("status", "unknown")

@tool
def get_flight_status(flight_number: str, date: str) -> str:
    """
    Get the status of a flight.

    Args:
        flight_number (str): The flight number.
        date (str): The date of the flight.

    Returns:
        str: The status of the flight or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_get_flight_status(data, flight_number=flight_number, date=date)
    except Exception as exc:
        return f"Error executing get_flight_status: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result