from pathlib import Path
import json
from typing import Dict, List
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

def _run_exchange_delivered_order_items(
    data: dict,
    order_id: str,
    item_ids: List[str],
    new_item_ids: List[str],
    payment_method_id: str,
) -> str:
    products, orders, users = data["products"], data["orders"], data["users"]

    # check order exists and is delivered
    if order_id not in orders:
        return "Error: order not found"
    order = orders[order_id]
    if order["status"] != "delivered":
        return "Error: non-delivered order cannot be exchanged"

    # check the items to be exchanged exist
    all_item_ids = [item["item_id"] for item in order["items"]]
    for item_id in item_ids:
        if item_ids.count(item_id) > all_item_ids.count(item_id):
            return f"Error: {item_id} not found"

    # check new items exist and match old items and are available
    if len(item_ids) != len(new_item_ids):
        return "Error: the number of items to be exchanged should match"

    diff_price = 0
    for item_id, new_item_id in zip(item_ids, new_item_ids):
        item = [item for item in order["items"] if item["item_id"] == item_id][0]
        product_id = item["product_id"]
        if not (
            new_item_id in products[product_id]["variants"]
            and products[product_id]["variants"][new_item_id]["available"]
        ):
            return f"Error: new item {new_item_id} not found or available"

        old_price = item["price"]
        new_price = products[product_id]["variants"][new_item_id]["price"]
        diff_price += new_price - old_price

    diff_price = round(diff_price, 2)

    # check payment method exists and can cover the price difference if gift card
    if payment_method_id not in users[order["user_id"]]["payment_methods"]:
        return "Error: payment method not found"

    payment_method = users[order["user_id"]]["payment_methods"][payment_method_id]
    if (
        payment_method["source"] == "gift_card"
        and payment_method["balance"] < diff_price
    ):
        return (
            "Error: insufficient gift card balance to pay for the price difference"
        )

    # modify the order
    order["status"] = "exchange requested"
    order["exchange_items"] = sorted(item_ids)
    order["exchange_new_items"] = sorted(new_item_ids)
    order["exchange_payment_method_id"] = payment_method_id
    order["exchange_price_difference"] = diff_price

    return json.dumps(order)

@tool
def exchange_delivered_order_items(order_id: str, item_ids: List[str], new_item_ids: List[str], payment_method_id: str) -> str:
    """
    Exchange items in a delivered order to new items of the same product type. For a delivered order, return or exchange can be only done once by the agent. The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.
    
    Args:
        order_id (string): The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
        item_ids (array): The item ids to be exchanged, each such as '1008292230'. There could be duplicate items in the list.
        new_item_ids (array): The item ids to be exchanged for, each such as '1008292230'. There could be duplicate items in the list. Each new item id should match the item id in the same position and be of the same product.
        payment_method_id (string): The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_exchange_delivered_order_items(data, order_id=order_id, item_ids=item_ids, new_item_ids=new_item_ids, payment_method_id=payment_method_id)
    except Exception as exc:
        return f"Error executing exchange_delivered_order_items: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
