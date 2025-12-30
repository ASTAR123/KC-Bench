from pathlib import Path
import json
from copy import deepcopy
from typing import Dict, List, Union
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

def _run_book_reservation(
    data: dict,
    user_id: str,
    origin: str,
    destination: str,
    flight_type: str,
    cabin: str,
    flights: List[dict],
    passengers: List[dict],
    payment_methods: List[dict],
    total_baggages: int,
    nonfree_baggages: int,
    insurance: str,
) -> str:
    reservations, users = data["reservations"], data["users"]
    if user_id not in users:
        return "Error: user not found"
    user = users[user_id]

    # assume each task makes at most 3 reservations
    reservation_id = "HATHAT"
    if reservation_id in reservations:
        reservation_id = "HATHAU"
        if reservation_id in reservations:
            reservation_id = "HATHAV"

    reservation = {
        "reservation_id": reservation_id,
        "user_id": user_id,
        "origin": origin,
        "destination": destination,
        "flight_type": flight_type,
        "cabin": cabin,
        "flights": deepcopy(flights),
        "passengers": passengers,
        "payment_history": payment_methods,
        "created_at": "2024-05-15T15:00:00",
        "total_baggages": total_baggages,
        "nonfree_baggages": nonfree_baggages,
        "insurance": insurance,
    }

    # update flights and calculate price
    total_price = 0
    for flight in reservation["flights"]:
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
        if flight_date_data["available_seats"][cabin] < len(passengers):
            return f"Error: not enough seats on flight {flight_number}"
        flight["price"] = flight_date_data["prices"][cabin]
        flight["origin"] = flight_data["origin"]
        flight["destination"] = flight_data["destination"]
        total_price += flight["price"] * len(passengers)

    if insurance == "yes":
        total_price += 30 * len(passengers)

    total_price += 50 * nonfree_baggages

    for payment_method in payment_methods:
        # 支持 payment_id 或 id 字段
        payment_id = payment_method.get("payment_id") or payment_method.get("id")
        if not payment_id:
            return "Error: payment_id or id field is required in payment_methods"
        amount = payment_method["amount"]
        if payment_id not in user["payment_methods"]:
            return f"Error: payment method {payment_id} not found"
        if user["payment_methods"][payment_id]["source"] in [
            "gift_card",
            "certificate",
        ]:
            if user["payment_methods"][payment_id]["amount"] < amount:
                return f"Error: not enough balance in payment method {payment_id}"
    
    total_payment = sum(payment["amount"] for payment in payment_methods)
    if total_payment != total_price:
        return f"Error: payment amount does not add up, total price is {total_price}, but paid {total_payment}"

    # if checks pass, deduct payment and update seats
    for payment_method in payment_methods:
        payment_id = payment_method.get("payment_id") or payment_method.get("id")
        amount = payment_method["amount"]
        if user["payment_methods"][payment_id]["source"] == "gift_card":
            user["payment_methods"][payment_id]["amount"] -= amount
        elif user["payment_methods"][payment_id]["source"] == "certificate":
            del user["payment_methods"][payment_id]

    reservations[reservation_id] = reservation
    user["reservations"].append(reservation_id)
    return json.dumps(reservation)

@tool
def book_reservation(user_id: str, origin: str, destination: str, flight_type: str, cabin: str, flights: List[dict], passengers: List[dict], payment_methods: List[dict], total_baggages: int, nonfree_baggages: int, insurance: str) -> str:
    """
    Book a reservation.
    
    Args:
        user_id (string): The ID of the user to book the reservation, such as 'sara_doe_496'.
        origin (string): The IATA code for the origin city, such as 'SFO'.
        destination (string): The IATA code for the destination city, such as 'JFK'.
        flight_type (string): Refer to Tau2Bench documentation.
        cabin (string): Refer to Tau2Bench documentation.
        flights (array): An array of objects containing details about each piece of flight.
        passengers (array): An array of objects containing details about each passenger.
        payment_methods (array): An array of objects containing details about each payment method.
        total_baggages (integer): The total number of baggage items included in the reservation.
        nonfree_baggages (integer): The number of non-free baggage items included in the reservation.
        insurance (string): Refer to Tau2Bench documentation.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_book_reservation(data, user_id=user_id, origin=origin, destination=destination, flight_type=flight_type, cabin=cabin, flights=flights, passengers=passengers, payment_methods=payment_methods, total_baggages=total_baggages, nonfree_baggages=nonfree_baggages, insurance=insurance)
    except Exception as exc:
        return f"Error executing book_reservation: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
