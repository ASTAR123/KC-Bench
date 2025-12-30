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

def _run_send_certificate(
    data: dict,
    user_id: str,
    amount: int,
) -> str:
    users = data["users"]
    if user_id not in users:
        return "Error: user not found"
    user = users[user_id]

    # add a certificate, assume at most 3 cases per task
    for id in [3221322, 3221323, 3221324]:
        payment_id = f"certificate_{id}"
        if payment_id not in user["payment_methods"]:
            user["payment_methods"][payment_id] = {
                "source": "certificate",
                "amount": amount,
                "id": payment_id,
            }
            return f"Certificate {payment_id} added to user {user_id} with amount {amount}."

@tool
def send_certificate(user_id: str, amount: float) -> str:
    """
    Send a certificate to a user. Be careful!
    
    Args:
        user_id (string): The ID of the user to book the reservation, such as 'sara_doe_496'.
        amount (number): Certificate amount to send.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_send_certificate(data, user_id=user_id, amount=amount)
    except Exception as exc:
        return f"Error executing send_certificate: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
