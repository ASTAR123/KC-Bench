from pathlib import Path
import json
from typing import Dict
from smolagents import tool
from Utils.environment_utils import get_task_environment_resources

_FILE_MAP = {'data': 'db.json'}
_LABEL_HINTS = ('tau2_retail_data', 'retail_data')
_DOMAIN = "retail"

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
    bundle = {}
    for key, filename in _FILE_MAP.items():
        with (base / filename).open('r', encoding='utf-8') as file:
            bundle[key] = json.load(file)
    return bundle, base

def _save_domain_data(base: Path, data: dict):
    for key, filename in _FILE_MAP.items():
        if key in data:
            with (base / filename).open('w', encoding='utf-8') as file:
                json.dump(data[key], file, ensure_ascii=False, indent=2)

def _run_modify_user_address(
    data: dict,
    user_id: str,
    address1: str,
    address2: str,
    city: str,
    state: str,
    country: str,
    zip: str,
) -> str:
    users = data["users"]
    if user_id not in users:
        return "Error: user not found"
    user = users[user_id]
    user["address"] = {
        "address1": address1,
        "address2": address2,
        "city": city,
        "state": state,
        "country": country,
        "zip": zip,
    }
    return json.dumps(user)

@tool
def modify_user_address(user_id: str, address1: str, address2: str, city: str, state: str, country: str, zip: str) -> str:
    """
    Modify the default address of a user. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.
    
    Args:
        user_id (string): The user id, such as 'sara_doe_496'.
        address1 (string): The first line of the address, such as '123 Main St'.
        address2 (string): The second line of the address, such as 'Apt 1' or ''.
        city (string): The city, such as 'San Francisco'.
        state (string): The state, such as 'CA'.
        country (string): The country, such as 'USA'.
        zip (string): The zip code, such as '12345'.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_modify_user_address(data, user_id=user_id, address1=address1, address2=address2, city=city, state=state, country=country, zip=zip)
    except Exception as exc:
        return f"Error executing modify_user_address: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
