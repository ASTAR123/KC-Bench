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

def _run_list_all_airports(data: dict) -> str:
    airports = [
        "SFO",
        "JFK",
        "LAX",
        "ORD",
        "DFW",
        "DEN",
        "SEA",
        "ATL",
        "MIA",
        "BOS",
        "PHX",
        "IAH",
        "LAS",
        "MCO",
        "EWR",
        "CLT",
        "MSP",
        "DTW",
        "PHL",
        "LGA",
    ]
    cities = [
        "San Francisco",
        "New York",
        "Los Angeles",
        "Chicago",
        "Dallas",
        "Denver",
        "Seattle",
        "Atlanta",
        "Miami",
        "Boston",
        "Phoenix",
        "Houston",
        "Las Vegas",
        "Orlando",
        "Newark",
        "Charlotte",
        "Minneapolis",
        "Detroit",
        "Philadelphia",
        "LaGuardia",
    ]
    return json.dumps({airport: city for airport, city in zip(airports, cities)})

@tool
def list_all_airports(payload: str) -> str:
    """
    List all airports and their cities.
    
    Args:
        payload (string): Raw payload string.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_list_all_airports(data)
    except Exception as exc:
        return f"Error executing list_all_airports: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
