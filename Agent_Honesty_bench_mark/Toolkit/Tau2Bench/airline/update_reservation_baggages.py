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

def _run_update_reservation_baggages(
    data: dict,
    reservation_id: str,
    total_baggages: int,
    nonfree_baggages: int,
    payment_id: str,
) -> str:
    users, reservations = data["users"], data["reservations"]
    if reservation_id not in reservations:
        return "Error: reservation not found"
    reservation = reservations[reservation_id]

    total_price = 50 * max(0, nonfree_baggages - reservation["nonfree_baggages"])
    if payment_id not in users[reservation["user_id"]]["payment_methods"]:
        return "Error: payment method not found"
    payment_method = users[reservation["user_id"]]["payment_methods"][payment_id]
    if payment_method["source"] == "certificate":
        return "Error: certificate cannot be used to update reservation"
    elif (
        payment_method["source"] == "gift_card"
        and payment_method["amount"] < total_price
    ):
        return "Error: gift card balance is not enough"

    reservation["total_baggages"] = total_baggages
    reservation["nonfree_baggages"] = nonfree_baggages
    if payment_method["source"] == "gift_card":
        payment_method["amount"] -= total_price

    if total_price != 0:
        reservation["payment_history"].append(
            {
                "payment_id": payment_id,
                "amount": total_price,
            }
        )

    return json.dumps(reservation)

@tool
def update_reservation_baggages(reservation_id: str, total_baggages: int, nonfree_baggages: int, payment_id: str) -> str:
    """
    Update the baggage information of a reservation.
    
    Args:
        reservation_id (string): The reservation ID, such as 'ZFA04Y'.
        total_baggages (integer): The updated total number of baggage items included in the reservation.
        nonfree_baggages (integer): The updated number of non-free baggage items included in the reservation.
        payment_id (string): The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_update_reservation_baggages(data, reservation_id=reservation_id, total_baggages=total_baggages, nonfree_baggages=nonfree_baggages, payment_id=payment_id)
    except Exception as exc:
        return f"Error executing update_reservation_baggages: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
