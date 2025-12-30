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

def _run_search_direct_flight(data: dict, origin: str, destination: str, date: str) -> str:
    flights = data["flights"]
    results = []
    for flight in flights.values():
        if flight["origin"] == origin and flight["destination"] == destination:
            if (
                date in flight["dates"]
                and flight["dates"][date]["status"] == "available"
            ):
                # results add flight except dates, but add flight["datas"][date]
                results.append({k: v for k, v in flight.items() if k != "dates"})
                results[-1].update(flight["dates"][date])
    return json.dumps(results)

@tool
def search_direct_flight(origin: str, destination: str, date: str) -> str:
    """
    Search direct flights between two cities on a specific date.
    
    Args:
        origin (string): The origin city airport in three letters, such as 'JFK'.
        destination (string): The destination city airport in three letters, such as 'LAX'.
        date (string): The date of the flight in the format 'YYYY-MM-DD', such as '2024-01-01'.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_search_direct_flight(data, origin=origin, destination=destination, date=date)
    except Exception as exc:
        return f"Error executing search_direct_flight: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
