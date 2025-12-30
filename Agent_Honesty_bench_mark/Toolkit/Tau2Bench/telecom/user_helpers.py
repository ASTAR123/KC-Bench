"""Helper functions for user device operations."""

import json
from typing import Dict
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


def load_user_db() -> Dict:
    """Load the user device database from JSON."""
    try:
        base = _locate_domain_base()
        user_db_path = base / "user_db.json"
        with open(user_db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Error loading user database: {e}")


def save_user_db(user_db: Dict) -> None:
    """Save the user device database to JSON."""
    try:
        base = _locate_domain_base()
        user_db_path = base / "user_db.json"
        with open(user_db_path, 'w', encoding='utf-8') as f:
            json.dump(user_db, f, indent=2, default=str, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"Error saving user database: {e}")


def check_can_send_mms(device: Dict) -> bool:
    """Check if device can send MMS based on various conditions."""
    # Need mobile data or wifi calling with MMS enabled
    mobile_data_ok = (
        not device.get('airplane_mode', False) and
        device.get('data_enabled', False) and
        device.get('network_connection_status') == 'connected'
    )
    
    wifi_calling_ok = (
        device.get('wifi_calling_enabled', False) and
        device.get('wifi_calling_mms_over_wifi', False) and
        device.get('wifi_connected', False)
    )
    
    if not (mobile_data_ok or wifi_calling_ok):
        return False
    
    # Check APN settings for MMS
    apn_settings = device.get('active_apn_settings', {})
    if not apn_settings.get('mms_apn') or not apn_settings.get('mmsc_url'):
        return False
    
    # Check messaging app has permissions
    app_statuses = device.get('app_statuses', {})
    messaging_app = app_statuses.get('messaging', {})
    permissions = messaging_app.get('permissions', {})
    
    if not (permissions.get('sms') and permissions.get('storage') and 
            permissions.get('phone') and permissions.get('network')):
        return False
    
    return True
