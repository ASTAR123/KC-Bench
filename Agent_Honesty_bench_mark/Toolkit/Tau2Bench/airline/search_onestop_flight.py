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

def _run_search_onestop_flight(data: dict, origin: str, destination: str, date: str) -> str:
    flights = data["flights"]
    results = []
    for flight1 in flights.values():
        if flight1["origin"] == origin:
            for flight2 in flights.values():
                if (
                    flight2["destination"] == destination
                    and flight1["destination"] == flight2["origin"]
                ):
                    date2 = (
                        f"2024-05-{int(date[-2:])+1}"
                        if "+1" in flight1["scheduled_arrival_time_est"]
                        else date
                    )
                    if (
                        flight1["scheduled_arrival_time_est"]
                        > flight2["scheduled_departure_time_est"]
                    ):
                        continue
                    if date in flight1["dates"] and date2 in flight2["dates"]:
                        if (
                            flight1["dates"][date]["status"] == "available"
                            and flight2["dates"][date2]["status"] == "available"
                        ):
                            result1 = {
                                k: v for k, v in flight1.items() if k != "dates"
                            }
                            result1.update(flight1["dates"][date])
                            result1["date"] = date
                            result2 = {
                                k: v for k, v in flight2.items() if k != "dates"
                            }
                            result2.update(flight2["dates"][date])
                            result2["date"] = date2
                            results.append([result1, result2])
    return json.dumps(results)

@tool
def search_onestop_flight(origin: str, destination: str, date: str) -> str:
    """
    Search direct flights between two cities on a specific date.
    
    Args:
        origin (string): The origin city airport in three letters, such as 'JFK'.
        destination (string): The destination city airport in three letters, such as 'LAX'.
        date (string): The date of the flight in the format 'YYYY-MM-DD', such as '2024-05-01'.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_search_onestop_flight(data, origin=origin, destination=destination, date=date)
    except Exception as exc:
        return f"Error executing search_onestop_flight: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
