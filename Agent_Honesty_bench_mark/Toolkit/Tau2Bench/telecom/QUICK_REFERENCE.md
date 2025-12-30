# Telecom Tools 快速参考

## 🎯 核心信息

- **工具总数**: 77个
- **错误处理**: 100%覆盖（airline模式）
- **数据库**: db.json (主数据), user_db.json (设备数据)

## 🔧 Helper模块

### data_helpers.py
```python
from .data_helpers import load_db, save_db, get_customer_by_id, get_line_by_id
```

### user_helpers.py
```python
from .user_helpers import load_user_db, save_user_db, check_can_send_mms
```

## 📚 工具分类速查

### 客户管理 (Customer)
- `get_customer_by_phone(phone: str)` → str
- `get_customer_by_id(customer_id: str)` → str
- `get_customer_by_name(name: str)` → str
- `get_bills_for_customer(customer_id: str)` → list
- `get_details_by_id(item_type: str, item_id: str)` → dict

### 计费 (Billing)
- `make_payment(customer_id: str, amount: float)` → str
- `assert_no_overdue_bill(customer_id: str)` → bool
- `assert_overdue_bill_exists(customer_id: str)` → bool

### 数据管理 (Data Management)
- `get_data_usage(line_id: str)` → dict
- `set_data_usage(line_id: str, amount: float)` → str
- `refuel_data(line_id: str, amount: float)` → dict
- `assert_data_refueling_amount(line_id: str, expected: float)` → bool

### 线路管理 (Line Management)
- `suspend_line(line_id: str)` → str
- `resume_line(line_id: str)` → str
- `suspend_line_for_overdue_bill(customer_id: str)` → str
- `assert_line_status(line_id: str, expected: str)` → bool
- `get_available_plan_ids()` → list

### 设备状态 (Device Status)
- `check_status_bar()` → str
- `check_network_status()` → dict
- `reboot_device()` → str
- `simulate_network_search()` → str
- `assert_service_status(expected: str)` → bool

### 网络模式 (Network Mode)
- `check_network_mode_preference()` → str
- `set_network_mode_preference(mode: str)` → str
- `run_speed_test()` → dict
- `assert_internet_speed(expected: str)` → bool
- `assert_internet_not_excellent()` → bool

### 飞行模式 (Airplane Mode)
- `toggle_airplane_mode()` → bool
- `turn_airplane_mode_on()` → str
- `turn_airplane_mode_off()` → str
- `assert_airplane_mode_status(expected: bool)` → bool

### SIM卡 (SIM Card)
- `check_sim_status()` → dict
- `reseat_sim_card()` → str
- `unseat_sim_card()` → str
- `lock_sim_card()` → str

### 移动数据 (Mobile Data)
- `toggle_data()` → bool
- `turn_data_on()` → str
- `turn_data_off()` → str
- `assert_mobile_data_status(expected: bool)` → bool
- `check_data_restriction_status()` → dict
- `toggle_data_saver_mode()` → bool
- `turn_data_saver_mode_on()` → str
- `turn_data_saver_mode_off()` → str
- `assert_mobile_data_saver_mode_status(expected: bool)` → bool
- `assert_mobile_data_usage_exceeded(line_id: str)` → bool

### 漫游 (Roaming)
- `enable_roaming(line_id: str)` → dict
- `disable_roaming(line_id: str)` → str
- `toggle_roaming()` → bool
- `turn_roaming_on()` → str
- `turn_roaming_off()` → str
- `assert_mobile_roaming_status(expected: bool)` → bool

### APN设置 (APN Settings)
- `check_apn_settings()` → dict
- `set_apn_settings(apn: str, username: str, password: str)` → str
- `reset_apn_settings()` → str
- `break_apn_settings()` → str
- `break_apn_mms_setting()` → str

### WiFi
- `check_wifi_status()` → dict
- `toggle_wifi()` → bool
- `check_wifi_calling_status()` → dict
- `toggle_wifi_calling()` → bool
- `set_wifi_calling(enabled: bool)` → str

### VPN
- `check_vpn_status()` → dict
- `connect_vpn(config_name: str)` → bool
- `disconnect_vpn()` → bool
- `break_vpn()` → str

### 应用管理 (Apps)
- `check_installed_apps()` → list
- `check_app_status(app_name: str)` → dict
- `check_app_permissions(app_name: str)` → dict
- `grant_app_permission(app_name: str, permission: str)` → str
- `remove_app_permission(app_name: str, permission: str)` → str

### MMS
- `can_send_mms()` → bool
- `assert_can_send_mms(expected: bool)` → bool

### 支付请求 (Payment Requests)
- `check_payment_request()` → dict
- `send_payment_request(amount: float, reason: str)` → str

### 用户信息 (User Info)
- `set_user_info(key: str, value: str)` → str
- `set_user_location(location: str)` → str

### 其他 (Misc)
- `transfer_to_human_agents(summary: str)` → str

## 💡 使用模式

### 读取数据
```python
from check_network_status import check_network_status
status = check_network_status()
# Returns: {"network": "LTE", "signal": "strong", ...}
```

### 修改配置
```python
from set_network_mode_preference import set_network_mode_preference
result = set_network_mode_preference("4g_only")
# Returns: "Network mode preference set to 4g_only"
```

### 断言检查
```python
from assert_mobile_data_status import assert_mobile_data_status
try:
    assert_mobile_data_status(expected_status=True)
    print("Mobile data is ON as expected")
except RuntimeError as e:
    print(f"Assertion failed: {e}")
```

## ⚠️ 错误处理

所有工具遵循统一的错误处理模式：

- **str返回**: 错误时返回 `"Error: ..."`
- **bool返回**: 错误时抛出 `RuntimeError`
- **dict/list返回**: 错误时可能返回字符串错误消息

示例:
```python
result = get_customer_by_phone("9999999999")
if isinstance(result, str) and result.startswith("Error:"):
    print(f"Tool failed: {result}")
```

## 📋 常见参数

- **line_id**: 线路ID (L001, L002, ...)
- **customer_id**: 客户ID (C001, C002, ...)
- **mode**: 网络模式 ("4g_5g_preferred", "4g_only", "3g_only", "2g_only")
- **expected_status**: 期望状态 (True/False)
- **app_name**: 应用名称 (如 "WhatsApp", "Facebook")
- **permission**: 权限名称 (如 "camera", "microphone", "location")

---

✅ **所有77个工具已实现airline风格的错误处理**
