# environment_simulator.py
"""Enhanced environment simulator for action-based evaluation with hash comparison."""

import json
import hashlib
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd


class EnhancedEnvironmentSimulator:
    """Enhanced environment simulator with state tracking and hash comparison."""
    
    def __init__(self, original_env_path: str, domain: str = "airline"):
        self.original_env_path = Path(original_env_path)
        self.domain = domain
        self.working_state = {}
        self.action_history = []
        self.original_state_hash = None
        
    def initialize_from_original(self) -> bool:
        """Initialize simulator state from original environment data."""
        try:
            self.working_state = self._load_environment_state(self.original_env_path)
            self.original_state_hash = self._calculate_state_hash(self.working_state)
            print(f"原始环境状态初始化成功，Hash: {self.original_state_hash}")
            return True
        except Exception as e:
            print(f"Failed to initialize from original: {str(e)}")
            return False
    
    def create_working_copy(self) -> Path:
        """Create a working copy of the environment for simulation."""
        temp_dir = tempfile.mkdtemp(prefix="env_sim_")
        temp_path = Path(temp_dir)
        
        # Copy original data to temp directory
        if self.original_env_path.exists():
            # Create same directory structure
            for item in self.original_env_path.rglob("*"):
                if item.is_file():
                    rel_path = item.relative_to(self.original_env_path)
                    dest_path = temp_path / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
        
        print(f"创建工作副本: {temp_path}")
        return temp_path
    
    def simulate_actions(self, actions: List[Dict], task_id: str) -> Tuple[bool, Dict]:
        """Simulate actions on a working copy and return final state."""
        self.action_history = actions.copy()
        
        if not actions:
            print("没有actions可执行")
            return False, {}
        
        print(f"开始模拟 {len(actions)} 个actions...")
        
        # Create working copy
        working_copy_path = self.create_working_copy()
        
        try:
            # Load working state
            working_state = self._load_environment_state(working_copy_path)
            
            # Execute each action sequentially
            for i, action in enumerate(actions):
                print(f"执行action {i+1}/{len(actions)}: {action.get('name', 'unknown')}")
                success, result = self._execute_single_action(action, working_state)
                if not success:
                    print(f"Action {i+1} 失败: {action.get('name', 'unknown')}, 错误: {result}")
                    
                    # Clean up
                    shutil.rmtree(working_copy_path, ignore_errors=True)
                    return False, {}
            
            # Save final state
            self._save_environment_state(working_copy_path, working_state)
            
            # Load final state for comparison
            final_state = self._load_environment_state(working_copy_path)
            final_state_hash = self._calculate_state_hash(final_state)
            
            print(f"模拟完成，最终状态Hash: {final_state_hash}")
            
            result = {
                'state': final_state,
                'hash': final_state_hash,
                'working_copy_path': str(working_copy_path),
                'action_count': len(actions),
                'simulation_success': True
            }
            
            # Clean up (保留副本用于调试时可注释掉)
            shutil.rmtree(working_copy_path, ignore_errors=True)
            
            return True, result
            
        except Exception as e:
            print(f"环境模拟异常: {str(e)}")
            # Clean up on error
            shutil.rmtree(working_copy_path, ignore_errors=True)
            return False, {}
    
    def compare_with_agent_output(self, simulated_state: Dict, agent_state: Dict) -> Dict[str, Any]:
        """Compare simulated state with agent's actual output state."""
        simulated_hash = self._calculate_state_hash(simulated_state)
        agent_hash = self._calculate_state_hash(agent_state)
        
        comparison = {
            'hash_match': simulated_hash == agent_hash,
            'simulated_hash': simulated_hash,
            'agent_hash': agent_hash,
            'match_percentage': 0.0,
            'differences': [],
            'file_comparisons': {}
        }
        
        if simulated_hash == agent_hash:
            comparison['match_percentage'] = 100.0
            comparison['message'] = "状态完全匹配"
            return comparison
        
        print(f"Hash不匹配: 模拟={simulated_hash}, Agent={agent_hash}")
        
        # If hashes don't match, do detailed comparison
        comparison['match_percentage'] = self._calculate_state_similarity(simulated_state, agent_state)
        
        # Find specific differences
        self._find_state_differences(simulated_state, agent_state, comparison['differences'])
        
        # 详细文件比较
        comparison['file_comparisons'] = self._compare_files_in_detail(simulated_state, agent_state)
        
        comparison['message'] = f"状态不匹配，相似度: {comparison['match_percentage']:.1f}%"
        
        return comparison
    
    def _calculate_state_hash(self, state: Dict) -> str:
        """Calculate hash of environment state."""
        # Sort keys for consistent hashing
        sorted_state = json.dumps(state, sort_keys=True, default=str)
        return hashlib.md5(sorted_state.encode()).hexdigest()
    
    def _calculate_state_similarity(self, state1: Dict, state2: Dict) -> float:
        """Calculate similarity percentage between two states."""
        if not state1 or not state2:
            return 0.0
        
        all_keys = set(state1.keys()) | set(state2.keys())
        if not all_keys:
            return 100.0
        
        matching_keys = 0
        for key in all_keys:
            val1 = state1.get(key)
            val2 = state2.get(key)
            
            if val1 == val2:
                matching_keys += 1
            elif isinstance(val1, (list, dict)) and isinstance(val2, (list, dict)):
                # Compare JSON strings for complex structures
                try:
                    if json.dumps(val1, sort_keys=True) == json.dumps(val2, sort_keys=True):
                        matching_keys += 1
                except:
                    pass
        
        return (matching_keys / len(all_keys)) * 100.0
    
    def _find_state_differences(self, state1: Dict, state2: Dict, differences: List[str]):
        """Find specific differences between states."""
        all_keys = set(state1.keys()) | set(state2.keys())
        
        for key in all_keys:
            val1 = state1.get(key)
            val2 = state2.get(key)
            
            if val1 is None and val2 is not None:
                differences.append(f"Key '{key}' 在模拟状态中缺失")
            elif val2 is None and val1 is not None:
                differences.append(f"Key '{key}' 在Agent状态中缺失")
            elif isinstance(val1, (list, dict)) and isinstance(val2, (list, dict)):
                try:
                    if json.dumps(val1, sort_keys=True) != json.dumps(val2, sort_keys=True):
                        differences.append(f"Key '{key}' 内容不同")
                except:
                    differences.append(f"Key '{key}' 无法比较")
            elif val1 != val2:
                differences.append(f"Key '{key}' 值不同: {val1} vs {val2}")
    
    def _compare_files_in_detail(self, state1: Dict, state2: Dict) -> Dict[str, Any]:
        """Compare files in detail."""
        comparisons = {}
        
        all_keys = set(state1.keys()) | set(state2.keys())
        
        for key in all_keys:
            val1 = state1.get(key)
            val2 = state2.get(key)
            
            if val1 is None or val2 is None:
                comparisons[key] = {"status": "missing", "message": "一方缺失"}
                continue
            
            if isinstance(val1, list) and isinstance(val2, list):
                comparisons[key] = self._compare_lists(key, val1, val2)
            elif isinstance(val1, dict) and isinstance(val2, dict):
                comparisons[key] = self._compare_dicts(key, val1, val2)
            else:
                comparisons[key] = {
                    "status": "different" if val1 != val2 else "same",
                    "type": "simple_value"
                }
        
        return comparisons
    
    def _compare_lists(self, key: str, list1: List, list2: List) -> Dict[str, Any]:
        """Compare two lists."""
        if len(list1) != len(list2):
            return {
                "status": "different",
                "message": f"长度不同: {len(list1)} vs {len(list2)}",
                "list1_length": len(list1),
                "list2_length": len(list2)
            }
        
        differences = []
        for i, (item1, item2) in enumerate(zip(list1, list2)):
            if item1 != item2:
                differences.append(f"索引 {i}: {item1} != {item2}")
        
        return {
            "status": "same" if not differences else "different",
            "differences": differences[:10],  # 限制数量
            "total_differences": len(differences)
        }
    
    def _compare_dicts(self, key: str, dict1: Dict, dict2: Dict) -> Dict[str, Any]:
        """Compare two dictionaries."""
        all_keys = set(dict1.keys()) | set(dict2.keys())
        differences = []
        
        for k in all_keys:
            v1 = dict1.get(k)
            v2 = dict2.get(k)
            
            if v1 != v2:
                differences.append(f"键 '{k}': {v1} != {v2}")
        
        return {
            "status": "same" if not differences else "different",
            "differences": differences[:10],  # 限制数量
            "total_differences": len(differences)
        }
    
    def _execute_single_action(self, action: Dict, state: Dict) -> Tuple[bool, Any]:
        """Execute a single action and update environment state."""
        action_name = action.get('name', '')
        kwargs = action.get('kwargs', {})
        
        print(f"  Action: {action_name}, 参数: {kwargs}")
        
        try:
            if self.domain == "airline":
                return self._execute_airline_action(action_name, kwargs, state)
            elif self.domain == "retail":
                return self._execute_retail_action(action_name, kwargs, state)
            else:
                return False, f"未知领域: {self.domain}"
        except Exception as e:
            return False, f"Action执行错误: {str(e)}"
    
    def _execute_airline_action(self, action_name: str, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Execute airline domain actions."""
        if action_name == 'tau_book_reservation':
            return self._simulate_book_reservation(kwargs, state)
        elif action_name == 'tau_cancel_reservation':
            return self._simulate_cancel_reservation(kwargs, state)
        elif action_name == 'tau_update_reservation_flights':
            return self._simulate_update_flights(kwargs, state)
        elif action_name == 'tau_update_reservation_baggages':
            return self._simulate_update_baggages(kwargs, state)
        elif action_name == 'tau_update_reservation_passengers':
            return self._simulate_update_passengers(kwargs, state)
        elif action_name == 'get_flight_info':
            return self._simulate_get_flight_info(kwargs, state)
        elif action_name == 'search_flights':
            return self._simulate_search_flights(kwargs, state)
        else:
            print(f"警告: 未知的airline action: {action_name}")
            return True, f"跳过未知action: {action_name}"  # 返回成功但不执行
    
    def _execute_retail_action(self, action_name: str, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Execute retail domain actions."""
        if action_name == 'find_user_id_by_name_zip':
            return self._simulate_find_user_id_by_name_zip(kwargs, state)
        elif action_name == 'get_product_details':
            return self._simulate_get_product_details(kwargs, state)
        elif action_name == 'list_all_product_types':
            return self._simulate_list_all_product_types(kwargs, state)
        elif action_name == 'get_user_details':
            return self._simulate_get_user_details(kwargs, state)
        elif action_name == 'get_order_details':
            return self._simulate_get_order_details(kwargs, state)
        elif action_name == 'modify_pending_order_items':
            return self._simulate_modify_pending_order_items(kwargs, state)
        elif action_name == 'return_delivered_order_items':
            return self._simulate_return_delivered_order_items(kwargs, state)
        elif action_name == 'exchange_delivered_order_items':
            return self._simulate_exchange_delivered_order_items(kwargs, state)
        else:
            print(f"警告: 未知的retail action: {action_name}")
            return True, f"跳过未知action: {action_name}"
    
    # Airline action implementations
    def _simulate_book_reservation(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Simulate booking reservation."""
        reservations_key = 'data/reservations.json'
        if reservations_key not in state:
            state[reservations_key] = []
        
        reservation_id = f"RES_{kwargs.get('user_id', 'unknown')}_{len(state[reservations_key]) + 1}"
        
        reservation = {
            'reservation_id': reservation_id,
            'user_id': kwargs.get('user_id'),
            'origin': kwargs.get('origin', ''),
            'destination': kwargs.get('destination', ''),
            'flight_type': kwargs.get('flight_type', 'one_way'),
            'cabin': kwargs.get('cabin', 'economy'),
            'flights': kwargs.get('flights', []),
            'passengers': kwargs.get('passengers', []),
            'payment_methods': kwargs.get('payment_methods', []),
            'total_baggages': kwargs.get('total_baggages', 0),
            'nonfree_baggages': kwargs.get('nonfree_baggages', 0),
            'insurance': kwargs.get('insurance', 'no'),
            'status': 'confirmed',
            'created_at': '2025-01-01T00:00:00Z'  # 模拟时间戳
        }
        
        state[reservations_key].append(reservation)
        print(f"  创建预订: {reservation_id}")
        return True, reservation_id
    
    def _simulate_cancel_reservation(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Simulate canceling reservation."""
        reservation_id = kwargs.get('reservation_id', '')
        
        reservations_key = 'data/reservations.json'
        if reservations_key not in state:
            return False, "未找到预订数据"
        
        for reservation in state[reservations_key]:
            if reservation.get('reservation_id') == reservation_id:
                reservation['status'] = 'cancelled'
                reservation['cancelled_at'] = '2025-01-01T00:00:00Z'  # 模拟时间戳
                print(f"  取消预订: {reservation_id}")
                return True, f"预订 {reservation_id} 已取消"
        
        return False, f"未找到预订: {reservation_id}"
    
    def _simulate_update_flights(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Simulate updating flights."""
        reservation_id = kwargs.get('reservation_id', '')
        new_flights = kwargs.get('flights', [])
        
        reservations_key = 'data/reservations.json'
        if reservations_key not in state:
            return False, "未找到预订数据"
        
        for reservation in state[reservations_key]:
            if reservation.get('reservation_id') == reservation_id:
                reservation['flights'] = new_flights
                print(f"  更新航班: {reservation_id}, 新航班数: {len(new_flights)}")
                return True, f"为 {reservation_id} 更新航班"
        
        return False, f"未找到预订: {reservation_id}"
    
    def _simulate_update_baggages(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Simulate updating baggage information."""
        reservation_id = kwargs.get('reservation_id', '')
        total_baggages = kwargs.get('total_baggages', 0)
        nonfree_baggages = kwargs.get('nonfree_baggages', 0)
        
        reservations_key = 'data/reservations.json'
        if reservations_key not in state:
            return False, "未找到预订数据"
        
        for reservation in state[reservations_key]:
            if reservation.get('reservation_id') == reservation_id:
                reservation['total_baggages'] = total_baggages
                reservation['nonfree_baggages'] = nonfree_baggages
                print(f"  更新行李: {reservation_id}, 总行李: {total_baggages}, 付费行李: {nonfree_baggages}")
                return True, f"为 {reservation_id} 更新行李信息"
        
        return False, f"未找到预订: {reservation_id}"
    
    def _simulate_update_passengers(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Simulate updating passenger information."""
        reservation_id = kwargs.get('reservation_id', '')
        passengers = kwargs.get('passengers', [])
        
        reservations_key = 'data/reservations.json'
        if reservations_key not in state:
            return False, "未找到预订数据"
        
        for reservation in state[reservations_key]:
            if reservation.get('reservation_id') == reservation_id:
                reservation['passengers'] = passengers
                print(f"  更新乘客: {reservation_id}, 乘客数: {len(passengers)}")
                return True, f"为 {reservation_id} 更新乘客信息"
        
        return False, f"未找到预订: {reservation_id}"
    
    def _simulate_get_flight_info(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Simulate getting flight information."""
        flight_id = kwargs.get('flight_id', '')
        
        flights_key = 'data/flights.csv'
        if flights_key not in state:
            return False, "未找到航班数据"
        
        for flight in state[flights_key]:
            if str(flight.get('flight_id', '')) == str(flight_id):
                print(f"  查询航班: {flight_id}")
                return True, flight
        
        return False, f"未找到航班: {flight_id}"
    
    def _simulate_search_flights(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Simulate searching flights."""
        origin = kwargs.get('origin', '')
        destination = kwargs.get('destination', '')
        date = kwargs.get('date', '')
        
        flights_key = 'data/flights.csv'
        if flights_key not in state:
            return False, "未找到航班数据"
        
        matching_flights = []
        for flight in state[flights_key]:
            if (flight.get('origin', '') == origin and 
                flight.get('destination', '') == destination):
                matching_flights.append(flight)
        
        print(f"  搜索航班: {origin}->{destination}, 找到 {len(matching_flights)} 个航班")
        return True, matching_flights
    
    # Retail action implementations
    def _simulate_find_user_id_by_name_zip(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Find user ID by name and zip."""
        first_name = kwargs.get('first_name', '').lower()
        last_name = kwargs.get('last_name', '').lower()
        zip_code = str(kwargs.get('zip', ''))
        
        users_key = 'data/users.csv'
        if users_key not in state:
            return False, "未找到用户数据"
        
        for user in state[users_key]:
            if (user.get('first_name', '').lower() == first_name and
                user.get('last_name', '').lower() == last_name and
                str(user.get('zip', '')) == zip_code):
                print(f"  查找用户: {first_name} {last_name}, zip: {zip_code}, 找到ID: {user.get('user_id', '')}")
                return True, user.get('user_id', '')
        
        return False, f"未找到用户: {first_name} {last_name}, zip: {zip_code}"
    
    def _simulate_get_product_details(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Get product details."""
        product_id = str(kwargs.get('product_id', ''))
        
        products_key = 'data/products.csv'
        if products_key not in state:
            return False, "未找到产品数据"
        
        for product in state[products_key]:
            if str(product.get('product_id', '')) == product_id:
                print(f"  查询产品: {product_id}")
                return True, product
        
        return False, f"未找到产品: {product_id}"
    
    def _simulate_list_all_product_types(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """List all product types."""
        products_key = 'data/products.csv'
        if products_key not in state:
            return False, "未找到产品数据"
        
        product_types = set()
        for product in state[products_key]:
            product_type = product.get('product_type', '')
            if product_type:
                product_types.add(product_type)
        
        print(f"  列出产品类型，找到 {len(product_types)} 种类型")
        return True, list(product_types)
    
    def _simulate_get_user_details(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Get user details."""
        user_id = str(kwargs.get('user_id', ''))
        
        users_key = 'data/users.csv'
        if users_key not in state:
            return False, "未找到用户数据"
        
        for user in state[users_key]:
            if str(user.get('user_id', '')) == user_id:
                print(f"  查询用户: {user_id}")
                return True, user
        
        return False, f"未找到用户: {user_id}"
    
    def _simulate_get_order_details(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Get order details."""
        order_id = str(kwargs.get('order_id', ''))
        
        orders_key = 'data/orders.csv'
        if orders_key not in state:
            return False, "未找到订单数据"
        
        for order in state[orders_key]:
            if str(order.get('order_id', '')) == order_id:
                print(f"  查询订单: {order_id}")
                return True, order
        
        return False, f"未找到订单: {order_id}"
    
    def _simulate_modify_pending_order_items(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Modify pending order items."""
        order_id = kwargs.get('order_id', '')
        item_ids = kwargs.get('item_ids', [])
        new_item_ids = kwargs.get('new_item_ids', [])
        
        orders_key = 'data/orders.csv'
        if orders_key not in state:
            return False, "未找到订单数据"
        
        for order in state[orders_key]:
            if str(order.get('order_id', '')) == order_id:
                if order.get('status', '') != 'pending':
                    return False, f"订单 {order_id} 不是待处理状态"
                
                # 简化修改逻辑
                current_items = order.get('items', '').split(',') if order.get('items') else []
                
                # 移除旧项目，添加新项目
                updated_items = [item for item in current_items if item not in item_ids]
                updated_items.extend(new_item_ids)
                
                order['items'] = ','.join(updated_items)
                order['status'] = 'modified'
                
                print(f"  修改订单项目: {order_id}, 新项目数: {len(updated_items)}")
                return True, f"订单 {order_id} 已修改"
        
        return False, f"未找到订单: {order_id}"
    
    def _simulate_return_delivered_order_items(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Return delivered order items."""
        order_id = kwargs.get('order_id', '')
        item_ids = kwargs.get('item_ids', [])
        
        orders_key = 'data/orders.csv'
        if orders_key not in state:
            return False, "未找到订单数据"
        
        for order in state[orders_key]:
            if str(order.get('order_id', '')) == order_id:
                if order.get('status', '') != 'delivered':
                    return False, f"订单 {order_id} 不是已送达状态"
                
                # 标记项目为已退回
                if 'returned_items' not in order:
                    order['returned_items'] = ''
                
                current_returns = order['returned_items'].split(',') if order['returned_items'] else []
                current_returns.extend(item_ids)
                order['returned_items'] = ','.join(current_returns)
                order['status'] = 'return_processed'
                
                print(f"  退回订单项目: {order_id}, 退回项目数: {len(item_ids)}")
                return True, f"订单 {order_id} 退回处理完成"
        
        return False, f"未找到订单: {order_id}"
    
    def _simulate_exchange_delivered_order_items(self, kwargs: Dict, state: Dict) -> Tuple[bool, Any]:
        """Exchange delivered order items."""
        order_id = kwargs.get('order_id', '')
        item_ids = kwargs.get('item_ids', [])
        new_item_ids = kwargs.get('new_item_ids', [])
        payment_method_id = kwargs.get('payment_method_id', '')
        
        orders_key = 'data/orders.csv'
        if orders_key not in state:
            return False, "未找到订单数据"
        
        for order in state[orders_key]:
            if str(order.get('order_id', '')) == order_id:
                if order.get('status', '') != 'delivered':
                    return False, f"订单 {order_id} 不是已送达状态"
                
                # 简化换货逻辑
                current_items = order.get('items', '').split(',') if order.get('items') else []
                
                # 移除旧项目，添加新项目
                updated_items = [item for item in current_items if item not in item_ids]
                updated_items.extend(new_item_ids)
                
                order['items'] = ','.join(updated_items)
                order['status'] = 'exchanged'
                order['exchange_payment_method'] = payment_method_id
                
                print(f"  换货处理: {order_id}, 新项目数: {len(updated_items)}")
                return True, f"订单 {order_id} 换货处理完成"
        
        return False, f"未找到订单: {order_id}"
    
    def _load_environment_state(self, env_path: Path) -> Dict:
        """Load environment state from directory."""
        state = {}
        
        try:
            # Load all files recursively
            for file_path in env_path.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(env_path))
                    
                    try:
                        if file_path.suffix == '.csv':
                            df = pd.read_csv(file_path)
                            state[rel_path] = df.to_dict('records')
                        elif file_path.suffix == '.json':
                            with file_path.open('r', encoding='utf-8') as f:
                                state[rel_path] = json.load(f)
                        elif file_path.suffix in ['.txt', '.md']:
                            with file_path.open('r', encoding='utf-8') as f:
                                state[rel_path] = f.read()
                        else:
                            # 其他文件类型
                            with file_path.open('r', encoding='utf-8') as f:
                                state[rel_path] = f.read()
                    except Exception as e:
                        print(f"  警告: 无法读取文件 {rel_path}: {str(e)}")
                        state[rel_path] = f"ERROR_LOADING: {str(e)}"
                            
        except Exception as e:
            print(f"Error loading environment state from {env_path}: {str(e)}")
        
        print(f"加载环境状态，共 {len(state)} 个文件")
        return state
    
    def _save_environment_state(self, env_path: Path, state: Dict):
        """Save environment state to directory."""
        for rel_path, data in state.items():
            file_path = env_path / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                    # Save as CSV if it looks like tabular data
                    if rel_path.endswith('.csv'):
                        df = pd.DataFrame(data)
                        df.to_csv(file_path, index=False)
                    else:
                        # Save as JSON
                        with file_path.open('w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                elif isinstance(data, (dict, list)):
                    with file_path.open('w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    with file_path.open('w', encoding='utf-8') as f:
                        f.write(str(data))
            except Exception as e:
                print(f"  警告: 无法保存文件 {rel_path}: {str(e)}")
    
    def get_original_state_hash(self) -> str:
        """Get hash of original environment state."""
        return self.original_state_hash or ""
    
    def get_action_history(self) -> List[Dict]:
        """Get action execution history."""
        return self.action_history
    
    def validate_action_format(self, action: Dict) -> Tuple[bool, str]:
        """Validate action format."""
        if not isinstance(action, dict):
            return False, "Action必须是字典"
        
        if 'name' not in action:
            return False, "Action缺少'name'字段"
        
        if 'kwargs' not in action:
            return False, "Action缺少'kwargs'字段"
        
        if not isinstance(action['kwargs'], dict):
            return False, "'kwargs'必须是字典"
        
        return True, "Action格式正确"
