from pathlib import Path
import json
from copy import deepcopy
from typing import Dict, List
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

def _run_update_reservation_flights(
    data: dict,
    reservation_id: str,
    cabin: str,
    flights: List[dict],
    payment_id: str,
) -> str:
    users, reservations = data["users"], data["reservations"]
    if reservation_id not in reservations:
        return "Error: reservation not found"
    reservation = reservations[reservation_id]

    # update flights and calculate price
    total_price = 0
    flights = deepcopy(flights)
    for flight in flights:
        # if existing flight, ignore
        if _ := [
            f
            for f in reservation["flights"]
            if f["flight_number"] == flight["flight_number"]
            and f["date"] == flight["date"]
            and cabin == reservation["cabin"]
        ]:
            total_price += _[0]["price"] * len(reservation["passengers"])
            flight["price"] = _[0]["price"]
            flight["origin"] = _[0]["origin"]
            flight["destination"] = _[0]["destination"]
            continue
        flight_number = flight["flight_number"]
        if flight_number not in data["flights"]:
            return f"Error: flight {flight_number} not found"
        flight_data = data["flights"][flight_number]
        if flight["date"] not in flight_data["dates"]:
            return (
                f"Error: flight {flight_number} not found on date {flight['date']}"
            )
        flight_date_data = flight_data["dates"][flight["date"]]
        if flight_date_data["status"] != "available":
            return f"Error: flight {flight_number} not available on date {flight['date']}"
        if flight_date_data["available_seats"][cabin] < len(
            reservation["passengers"]
        ):
            return f"Error: not enough seats on flight {flight_number}"
        flight["price"] = flight_date_data["prices"][cabin]
        flight["origin"] = flight_data["origin"]
        flight["destination"] = flight_data["destination"]
        total_price += flight["price"] * len(reservation["passengers"])

    total_price -= sum(flight["price"] for flight in reservation["flights"]) * len(
        reservation["passengers"]
    )

    # check payment
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

    # if checks pass, deduct payment and update seats
    if payment_method["source"] == "gift_card":
        payment_method["amount"] -= total_price
    reservation["flights"] = flights
    if total_price != 0:
        reservation["payment_history"].append(
            {
                "payment_id": payment_id,
                "amount": total_price,
            }
        )
    # do not make flight database update here, assume it takes time to be updated
    return json.dumps(reservation)

@tool
def update_reservation_flights(reservation_id: str, cabin: str, flights: List[dict], payment_id: str) -> str:
    """
    Update the flight information of a reservation.
    
    Args:
        reservation_id (string): The reservation ID, such as 'ZFA04Y'.
        cabin (string): Refer to Tau2Bench documentation.
        flights (array): An array of objects containing details about each piece of flight in the ENTIRE new reservation. Even if the a flight segment is not changed, it should still be included in the array.
        payment_id (string): The payment id stored in user profile, such as 'credit_card_7815826', 'gift_card_7815826', 'certificate_7815826'.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_update_reservation_flights(data, reservation_id=reservation_id, cabin=cabin, flights=flights, payment_id=payment_id)
    except Exception as exc:
        return f"Error executing update_reservation_flights: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
