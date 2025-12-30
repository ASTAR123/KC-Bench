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

def _run_find_user_id_by_name_zip(data: dict, first_name: str, last_name: str, zip: str) -> str:
    users = data["users"]
    for user_id, profile in users.items():
        if (
            profile["name"]["first_name"].lower() == first_name.lower()
            and profile["name"]["last_name"].lower() == last_name.lower()
            and profile["address"]["zip"] == zip
        ):
            return user_id
    return "Error: user not found"

@tool
def find_user_id_by_name_zip(first_name: str, last_name: str, zip: str) -> str:
    """
    Find user id by first name, last name, and zip code. If the user is not found, the function will return an error message. By default, find user id by email, and only call this function if the user is not found by email or cannot remember email.
    
    Args:
        first_name (string): The first name of the customer, such as 'John'.
        last_name (string): The last name of the customer, such as 'Doe'.
        zip (string): The zip code of the customer, such as '12345'.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_find_user_id_by_name_zip(data, first_name=first_name, last_name=last_name, zip=zip)
    except Exception as exc:
        return f"Error executing find_user_id_by_name_zip: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
