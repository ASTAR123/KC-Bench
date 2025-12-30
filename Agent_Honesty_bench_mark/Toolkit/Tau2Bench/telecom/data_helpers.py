"""Helper functions for loading and manipulating telecom data from JSON files."""

import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from pathlib import Path


def _locate_domain_base() -> Path:
    """Locate the telecom domain data directory."""
    from Utils.environment_utils import get_task_environment_resources
    
    _LABEL_HINTS = ('tau2_telecom_data', 'telecom_data')
    _DOMAIN = 'telecom'
    
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
            # If path ends with /data, go to parent directory
            if normalized.endswith('/data'):
                return candidate.parent
            return candidate
        if f"tau2bench/{_DOMAIN}" in normalized:
            # If path ends with /data, go to parent directory
            if normalized.endswith('/data'):
                return candidate.parent
            return candidate
    
    raise FileNotFoundError(f"Tau2Bench environment for domain '{_DOMAIN}' not found.")


def load_db() -> Dict:
    """Load the main telecom database from JSON."""
    try:
        base = _locate_domain_base()
        db_path = base / "db.json"
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Error loading telecom database: {e}")


def save_db(db: Dict) -> None:
    """Save the main telecom database to JSON."""
    try:
        base = _locate_domain_base()
        db_path = base / "db.json"
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, default=str, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"Error saving telecom database: {e}")


def get_today() -> date:
    """Get today's date (mocked for testing)."""
    return date(2025, 2, 20)


def get_customer_by_id(db: Dict, customer_id: str) -> Optional[Dict]:
    """Get customer by ID."""
    for customer in db.get('customers', []):
        if customer['customer_id'] == customer_id:
            return customer
    return None


def get_customer_by_phone(db: Dict, phone_number: str) -> Optional[Dict]:
    """Get customer by phone number."""
    for customer in db.get('customers', []):
        if customer.get('phone_number') == phone_number:
            return customer
    return None


def get_line_by_id(db: Dict, line_id: str) -> Optional[Dict]:
    """Get line by ID."""
    for line in db.get('lines', []):
        if line['line_id'] == line_id:
            return line
    return None


def get_line_by_phone(db: Dict, phone_number: str) -> Optional[Dict]:
    """Get line by phone number."""
    for line in db.get('lines', []):
        if line['phone_number'] == phone_number:
            return line
    return None


def get_plan_by_id(db: Dict, plan_id: str) -> Optional[Dict]:
    """Get plan by ID."""
    for plan in db.get('plans', []):
        if plan['plan_id'] == plan_id:
            return plan
    return None


def get_device_by_id(db: Dict, device_id: str) -> Optional[Dict]:
    """Get device by ID."""
    for device in db.get('devices', []):
        if device['device_id'] == device_id:
            return device
    return None


def get_bill_by_id(db: Dict, bill_id: str) -> Optional[Dict]:
    """Get bill by ID."""
    for bill in db.get('bills', []):
        if bill['bill_id'] == bill_id:
            return bill
    return None


def get_target_line(db: Dict, customer_id: str, line_id: str) -> Dict:
    """Get a line that belongs to a specific customer."""
    customer = get_customer_by_id(db, customer_id)
    if not customer:
        raise ValueError(f"Customer {customer_id} not found")
    
    if line_id not in customer.get('line_ids', []):
        raise ValueError(f"Line {line_id} does not belong to customer {customer_id}")
    
    line = get_line_by_id(db, line_id)
    if not line:
        raise ValueError(f"Line {line_id} not found")
    
    return line
