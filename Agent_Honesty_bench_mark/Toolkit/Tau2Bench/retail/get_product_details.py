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

def _run_get_product_details(data: dict, product_id: str) -> str:
    products = data["products"]
    if product_id in products:
        return json.dumps(products[product_id])
    return "Error: product not found"

@tool
def get_product_details(product_id: str) -> str:
    """
    Get the inventory details of a product.
    
    Args:
        product_id (string): The product id, such as '6086499569'. Be careful the product id is different from the item id.
    
    Returns:
        str: Result string or error message.
    """
    try:
        data, base = _load_domain_data()
    except Exception as exc:
        return f"Error loading Tau2Bench data: {exc}"
    try:
        result = _run_get_product_details(data, product_id=product_id)
    except Exception as exc:
        return f"Error executing get_product_details: {exc}"
    if isinstance(result, str) and result.startswith('Error'):
        return result
    try:
        _save_domain_data(base, data)
    except Exception as exc:
        return f"Error persisting Tau2Bench data: {exc}"
    return result
