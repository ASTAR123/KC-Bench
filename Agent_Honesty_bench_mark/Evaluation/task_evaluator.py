# file: task_evaluator.py
"""Enhanced task evaluator with environment simulation and LLM-as-Judge."""

import json
from collections import defaultdict
from typing import Dict, Any, List, Tuple
from environment_simulator import EnhancedEnvironmentSimulator


class TaskEvaluator:
    """Task evaluator with environment simulation and LLM-as-Judge."""
    
    def __init__(self, prompt_manager, config: Dict[str, Any]):
        self.prompt_manager = prompt_manager
        self.config = config
        self.benchmark_type = config.get("benchmark_type", "unknown")
        self.domain = config.get("domain", "airline")
        self.environment_data_path = config.get("environment_data_path", "")
        self.evaluation_stats = {
            "llm_calls": 0,
            "successful_llm_calls": 0,
            "failed_llm_calls": 0,
            "env_simulations": 0,
            "successful_env_simulations": 0,
            "hash_comparisons": 0,
            "hash_matches": 0
        }
        self.env_simulator = None
        self.data_loader = None  # 将在analyze_task_completion中设置
        
    def set_data_loader(self, data_loader):
        """Set data loader for accessing task definitions."""
        self.data_loader = data_loader
        
    def initialize_environment_simulator(self):
        """Initialize environment simulator if path is provided."""
        if self.environment_data_path and self.environment_data_path != "Not provided":
            try:
                self.env_simulator = EnhancedEnvironmentSimulator(
                    original_env_path=self.environment_data_path,
                    domain=self.domain
                )
                # Initialize with original data
                if self.env_simulator.initialize_from_original():
                    print(f"环境模拟器初始化成功: {self.environment_data_path}")
                else:
                    print("环境模拟器初始化失败")
                    self.env_simulator = None
            except Exception as e:
                print(f"环境模拟器初始化失败: {str(e)}")
                self.env_simulator = None
        else:
            print("环境数据路径未提供，环境模拟器不可用")
    
    def analyze_task_completion(self, task_results: List[Dict], 
                              task_definitions: List[Dict],
                              environment_data: Dict[str, Any],
                              agent_env_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task completion using environment simulation and LLM-as-Judge."""
        print(f"开始评估 {len(task_results)} 个任务...")
        
        # 初始化环境模拟器
        self.initialize_environment_simulator()
        
        completion_stats = {
            'total_tasks': len(task_results),
            'successful_tasks': 0,
            'failed_tasks': 0,
            'success_rate': 0,
            'process_analysis': defaultdict(int),
            'outcome_analysis': defaultdict(int),
            'action_based_analysis': defaultdict(int),
            'failure_categories': defaultdict(int),
            'llm_evaluation_stats': self.evaluation_stats.copy(),
            'evaluation_methods_used': defaultdict(int),
            'hash_comparison_results': defaultdict(dict),
            'task_by_task_results': []  # 每个任务的详细结果
        }
        
        # 将task_definitions转换为字典以便快速查找
        task_def_dict = {}
        for task_def in task_definitions:
            task_id = task_def.get('task_id')
            if task_id:
                task_def_dict[task_id] = task_def
        
        for idx, task in enumerate(task_results, 1):
            print(f"\n{'='*60}")
            task_id = task.get('task_id', f'task_{idx}')
            print(f"评估任务 {idx}/{len(task_results)} (ID: {task_id})")
            print(f"{'='*60}")
            
            # 获取对应的任务定义
            task_definition = task_def_dict.get(task_id, {})
            
            # 从任务定义中提取expected actions
            expected_actions = self._extract_expected_actions_from_definition(task_definition)
            
            # 检查是否有Label
            has_label = self._has_label_in_definition(task_definition)
            has_expected_actions = len(expected_actions) > 0
            
            print(f"任务数据: 有Label={has_label}, 有Expected Actions={has_expected_actions}")
            
            if has_expected_actions:
                print(f"找到 {len(expected_actions)} 个expected actions")
                for i, action in enumerate(expected_actions):
                    print(f"  Action {i+1}: {action.get('name', 'unknown')}")
            
            # 根据数据类型选择评估方法
            evaluation_result = self._evaluate_task_by_data_type(
                task, task_definition, expected_actions, agent_env_outputs
            )
            
            task_status = evaluation_result['status']
            
            if task_status == 'success':
                completion_stats['successful_tasks'] += 1
            else:
                completion_stats['failed_tasks'] += 1
            
            # 记录评估方法
            for method in evaluation_result['methods_used']:
                completion_stats['evaluation_methods_used'][method] += 1
            
            # 记录各种分析结果
            if 'process_quality' in evaluation_result:
                quality = evaluation_result['process_quality']
                completion_stats['process_analysis'][quality] += 1
            
            if 'outcome_quality' in evaluation_result:
                quality = evaluation_result['outcome_quality']
                completion_stats['outcome_analysis'][quality] += 1
            
            if 'action_quality' in evaluation_result:
                quality = evaluation_result['action_quality']
                completion_stats['action_based_analysis'][quality] += 1
            
            if 'hash_comparison' in evaluation_result:
                completion_stats['hash_comparison_results'][task_id] = evaluation_result['hash_comparison']
            
            if 'failure_reason' in evaluation_result:
                error_type = evaluation_result['failure_reason']
                completion_stats['failure_categories'][error_type] += 1
            
            # 记录每个任务的详细结果
            task_detail = {
                'task_id': task_id,
                'status': task_status,
                'evaluation_methods': evaluation_result['methods_used'],
                'expected_actions_count': len(expected_actions),
                'has_label': has_label
            }
            
            if 'hash_comparison' in evaluation_result:
                task_detail['hash_match'] = evaluation_result['hash_comparison'].get('hash_match', False)
                task_detail['match_percentage'] = evaluation_result['hash_comparison'].get('match_percentage', 0)
            
            completion_stats['task_by_task_results'].append(task_detail)
            
            print(f"任务状态: {task_status} - 评估方法: {evaluation_result['methods_used']}")
        
        # 计算成功率
        if completion_stats['total_tasks'] > 0:
            completion_stats['success_rate'] = (
                completion_stats['successful_tasks'] / completion_stats['total_tasks']
            )
        
        # 更新统计
        completion_stats['llm_evaluation_stats'] = self.evaluation_stats
        
        # 计算hash比对统计
        if completion_stats['hash_comparison_results']:
            total_comparisons = len(completion_stats['hash_comparison_results'])
            hash_matches = sum(1 for comp in completion_stats['hash_comparison_results'].values() 
                             if comp.get('hash_match', False))
            completion_stats['hash_comparison_stats'] = {
                'total_comparisons': total_comparisons,
                'hash_matches': hash_matches,
                'hash_match_rate': hash_matches / total_comparisons if total_comparisons > 0 else 0
            }
        
        # 转换defaultdict
        for key in ['process_analysis', 'outcome_analysis', 'action_based_analysis', 
                   'failure_categories', 'evaluation_methods_used', 'hash_comparison_results']:
            if key in completion_stats:
                completion_stats[key] = dict(completion_stats[key])
        
        # 打印统计信息
        self._print_evaluation_stats()
        
        return completion_stats
    
    def _extract_expected_actions_from_definition(self, task_definition: Dict) -> List[Dict]:
        """Extract expected actions from task definition."""
        if not task_definition:
            return []
        
        actions = []
        
        # 从task字段中提取actions
        task_info = task_definition.get('task', {})
        
        # 方法1: 直接有actions字段
        if 'actions' in task_info:
            actions = task_info['actions']
            if isinstance(actions, list):
                return actions
        
        # 方法2: 从label中提取actions
        if 'label' in task_info:
            label = task_info['label']
            return self._extract_actions_from_label(label)
        
        # 方法3: 从metadata中提取
        if 'metadata' in task_info and 'expected_actions' in task_info['metadata']:
            actions = task_info['metadata']['expected_actions']
            if isinstance(actions, list):
                return actions
        
        # 方法4: 从instruction中解析
        if 'instruction' in task_info:
            instruction = task_info['instruction']
            # 尝试从instruction中解析action描述
            parsed_actions = self._parse_actions_from_text(instruction)
            if parsed_actions:
                return parsed_actions
        
        return []
    
    def _extract_actions_from_label(self, label) -> List[Dict]:
        """Extract actions from label field."""
        actions = []
        
        if isinstance(label, list):
            for item in label:
                if isinstance(item, dict):
                    if 'action' in item:
                        actions.append(item['action'])
                    elif 'name' in item and 'kwargs' in item:
                        # 已经是action格式
                        actions.append(item)
                elif isinstance(item, str):
                    # 尝试解析字符串
                    parsed = self._parse_action_from_string(item)
                    if parsed:
                        actions.append(parsed)
        elif isinstance(label, dict):
            if 'action' in label:
                actions.append(label['action'])
            elif 'actions' in label:
                actions.extend(label['actions'])
        elif isinstance(label, str):
            parsed = self._parse_action_from_string(label)
            if parsed:
                actions.append(parsed)
        
        return actions
    
    def _parse_action_from_string(self, text: str) -> Dict:
        """Parse action from string."""
        try:
            # 尝试直接解析JSON
            action_data = json.loads(text)
            if isinstance(action_data, dict) and 'name' in action_data:
                return action_data
        except:
            pass
        
        # 尝试解析常见格式
        import re
        
        # 格式: action_name(param1=value1, param2=value2)
        pattern1 = r'(\w+)\(([^)]+)\)'
        match1 = re.search(pattern1, text)
        if match1:
            action_name = match1.group(1)
            params_str = match1.group(2)
            
            # 解析参数
            kwargs = {}
            param_pattern = r'(\w+)=([^,]+)'
            params = re.findall(param_pattern, params_str)
            for key, value in params:
                kwargs[key.strip()] = value.strip().strip('"\'')
            
            return {'name': action_name, 'kwargs': kwargs}
        
        # 格式: {"name": "...", "kwargs": {...}}
        pattern2 = r'\{\s*"name"\s*:\s*"([^"]+)"[^}]*"kwargs"\s*:\s*(\{[^}]+\})'
        match2 = re.search(pattern2, text)
        if match2:
            try:
                action_name = match2.group(1)
                kwargs_str = match2.group(2)
                kwargs = json.loads(kwargs_str)
                return {'name': action_name, 'kwargs': kwargs}
            except:
                pass
        
        return None
    
    def _parse_actions_from_text(self, text: str) -> List[Dict]:
        """Parse actions from natural language text."""
        # 这里可以添加更复杂的NLP解析逻辑
        # 目前简单实现
        actions = []
        
        # 查找action关键词
        import re
        action_patterns = [
            r'执行\s+(\w+)\s+操作',
            r'调用\s+(\w+)\s+工具',
            r'使用\s+(\w+)\s+功能'
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text)
            for action_name in matches:
                actions.append({'name': action_name, 'kwargs': {}})
        
        return actions
    
    def _has_label_in_definition(self, task_definition: Dict) -> bool:
        """Check if task definition has label."""
        if not task_definition:
            return False
        
        task_info = task_definition.get('task', {})
        label = task_info.get('label')
        
        if isinstance(label, (list, dict, str)) and label:
            return True
        
        return False
    
    def _evaluate_task_by_data_type(self, task: Dict, task_definition: Dict, 
                                   expected_actions: List[Dict], 
                                   agent_env_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """根据数据类型选择合适的评估方法."""
        result = {
            'status': 'unknown',
            'methods_used': [],
            'process_quality': 'unknown',
            'outcome_quality': 'unknown',
            'action_quality': 'unknown'
        }
        
        task_id = task.get('task_id', '')
        has_label = self._has_label_in_definition(task_definition)
        has_expected_actions = len(expected_actions) > 0
        
        # 情况1: 只有Label - 纯LLM评估
        if has_label and not has_expected_actions:
            print("评估策略: 只有Label，使用LLM评估结果质量")
            outcome_quality = self._evaluate_with_label(task, task_definition)
            result['outcome_quality'] = outcome_quality
            
            # LLM判断任务是否成功
            success = self._llm_judge_task_success(task, outcome_quality)
            result['status'] = 'success' if success else 'failed'
            result['methods_used'].append('llm_label_evaluation')
            
            if not success:
                result['failure_reason'] = self._analyze_failure_reason(task, 'label_based')
        
        # 情况2: 只有Expected Actions - 环境模拟器评估
        elif has_expected_actions and not has_label:
            print("评估策略: 只有Expected Actions，使用环境模拟器评估")
            
            # 使用环境模拟器执行expected actions
            simulation_success, simulation_result = self._simulate_expected_actions(expected_actions, task_id)
            
            if not simulation_success:
                print("环境模拟失败")
                result['status'] = 'failed'
                result['failure_reason'] = 'environment_simulation_failed'
                result['methods_used'].append('environment_simulation')
                return result
            
            # 获取agent的实际环境输出
            agent_state = agent_env_outputs.get(task_id, {})
            
            if agent_state:
                # 进行hash比对
                self.evaluation_stats["hash_comparisons"] += 1
                hash_comparison = self.env_simulator.compare_with_agent_output(
                    simulation_result['state'], agent_state
                )
                result['hash_comparison'] = hash_comparison
                
                if hash_comparison['hash_match']:
                    self.evaluation_stats["hash_matches"] += 1
                
                # 根据hash匹配度判断任务状态
                if hash_comparison['hash_match'] or hash_comparison['match_percentage'] > 90:
                    result['status'] = 'success'
                    result['action_quality'] = 'excellent' if hash_comparison['hash_match'] else 'good'
                else:
                    result['status'] = 'failed'
                    result['failure_reason'] = 'state_mismatch'
                    result['action_quality'] = 'poor'
            else:
                # 没有agent输出，使用LLM评估action执行质量
                action_quality = self._evaluate_action_quality_with_llm(expected_actions, task.get('result', ''))
                result['action_quality'] = action_quality
                
                # LLM判断action执行是否成功
                success = action_quality in ['excellent', 'good']
                result['status'] = 'success' if success else 'failed'
                
                if not success:
                    result['failure_reason'] = 'llm_action_evaluation_failed'
            
            result['methods_used'].append('environment_simulation')
            
            # 评估过程质量
            process_quality = self._evaluate_process_quality(task)
            result['process_quality'] = process_quality
        
        # 情况3: 两者都有 - 综合评估
        elif has_label and has_expected_actions:
            print("评估策略: Label和Expected Actions都有，进行综合评估")
            
            # LLM评估结果质量
            outcome_quality = self._evaluate_with_label(task, task_definition)
            result['outcome_quality'] = outcome_quality
            
            # 使用环境模拟器执行expected actions
            simulation_success, simulation_result = self._simulate_expected_actions(expected_actions, task_id)
            
            if simulation_success:
                result['methods_used'].append('environment_simulation')
                
                # 获取agent的实际环境输出
                agent_state = agent_env_outputs.get(task_id, {})
                
                if agent_state:
                    # 进行hash比对
                    self.evaluation_stats["hash_comparisons"] += 1
                    hash_comparison = self.env_simulator.compare_with_agent_output(
                        simulation_result['state'], agent_state
                    )
                    result['hash_comparison'] = hash_comparison
                    
                    if hash_comparison['hash_match']:
                        self.evaluation_stats["hash_matches"] += 1
                    
                    # 结合LLM评估和hash比对结果判断任务状态
                    label_success = outcome_quality in ['excellent', 'good']
                    action_success = hash_comparison['hash_match'] or hash_comparison['match_percentage'] > 90
                    
                    if label_success and action_success:
                        result['status'] = 'success'
                        result['action_quality'] = 'excellent' if hash_comparison['hash_match'] else 'good'
                    else:
                        result['status'] = 'failed'
                        result['failure_reason'] = 'combined_evaluation_failed'
                else:
                    # 只有LLM评估
                    action_quality = self._evaluate_action_quality_with_llm(expected_actions, task.get('result', ''))
                    result['action_quality'] = action_quality
                    
                    label_success = outcome_quality in ['excellent', 'good']
                    action_success = action_quality in ['excellent', 'good']
                    
                    result['status'] = 'success' if (label_success and action_success) else 'failed'
            else:
                result['methods_used'].append('environment_simulation_failed')
                result['status'] = 'failed'
                result['failure_reason'] = 'environment_simulation_failed'
            
            # 评估过程质量
            process_quality = self._evaluate_process_quality(task)
            result['process_quality'] = process_quality
            
            result['methods_used'].append('llm_label_evaluation')
        
        # 情况4: 两者都没有 - 通用LLM评估
        else:
            print("评估策略: 无Label无Expected Actions，使用通用LLM评估")
            overall_quality = self._evaluate_generic(task)
            result['outcome_quality'] = overall_quality
            
            # LLM判断任务是否成功
            success = overall_quality in ['excellent', 'good', 'acceptable']
            result['status'] = 'success' if success else 'failed'
            result['methods_used'].append('llm_generic_evaluation')
            
            if not success:
                result['failure_reason'] = self._analyze_failure_reason(task, 'generic')
        
        return result
    
    def _simulate_expected_actions(self, expected_actions: List[Dict], task_id: str) -> Tuple[bool, Dict]:
        """使用环境模拟器执行expected actions."""
        if not self.env_simulator:
            print("环境模拟器不可用")
            return False, {}
        
        self.evaluation_stats["env_simulations"] += 1
        
        try:
            print(f"模拟执行 {len(expected_actions)} 个expected actions...")
            
            # 执行actions
            success, simulation_result = self.env_simulator.simulate_actions(expected_actions, task_id)
            
            if success:
                print(f"环境模拟成功，最终状态hash: {simulation_result.get('hash', 'unknown')}")
                self.evaluation_stats["successful_env_simulations"] += 1
                return True, simulation_result
            else:
                print("环境模拟失败")
                return False, {}
                
        except Exception as e:
            print(f"环境模拟异常: {str(e)}")
            return False, {}
    
    def _evaluate_action_quality_with_llm(self, expected_actions: List[Dict], agent_result: str) -> str:
        """使用LLM评估action执行质量."""
        self.evaluation_stats["llm_calls"] += 1
        
        try:
            result = self.prompt_manager.evaluate_with_template(
                'action_based_evaluation',
                expected_actions=json.dumps(expected_actions, ensure_ascii=False),
                agent_response=agent_result[:1000]
            )
            
            if 'error' in result:
                print(f"Action质量评估失败: {result.get('error', '未知错误')}")
                self.evaluation_stats["failed_llm_calls"] += 1
                return "unknown"
            
            overall_quality = result.get('overall_quality', 'unknown')
            self.evaluation_stats["successful_llm_calls"] += 1
            return overall_quality
            
        except Exception as e:
            print(f"Action质量评估异常: {str(e)}")
            self.evaluation_stats["failed_llm_calls"] += 1
            return "unknown"
    
    def _llm_judge_task_success(self, task: Dict, outcome_quality: str) -> bool:
        """使用LLM判断任务是否成功."""
        # 这里可以添加更复杂的LLM判断逻辑
        # 目前简单根据outcome_quality判断
        return outcome_quality in ['excellent', 'good']
    
    def _evaluate_with_label(self, task: Dict, task_definition: Dict) -> str:
        """使用LLM评估结果与Label的匹配度."""
        self.evaluation_stats["llm_calls"] += 1
        
        try:
            task_info = task_definition.get('task', {})
            instruction = task_info.get('instruction', '')
            labels = task_info.get('label', [])
            response = task.get('result', '')
            
            if not instruction or not response:
                return "unknown"
            
            # 限制长度
            if len(response) > 1500:
                response = response[:1500] + "..."
            
            result = self.prompt_manager.evaluate_with_template(
                'outcome_quality',
                instruction=instruction,
                label=json.dumps(labels, ensure_ascii=False),
                response=response
            )
            
            if 'error' in result:
                print(f"Label评估失败: {result.get('error', '未知错误')}")
                self.evaluation_stats["failed_llm_calls"] += 1
                return "unknown"
            
            score = result.get('score', 0)
            if score == 1:
                overall_quality = "excellent"
            else:
                overall_quality = "poor"
            
            self.evaluation_stats["successful_llm_calls"] += 1
            return overall_quality
            
        except Exception as e:
            print(f"Label评估异常: {str(e)}")
            self.evaluation_stats["failed_llm_calls"] += 1
            return "unknown"
    
    def _evaluate_generic(self, task: Dict) -> str:
        """通用LLM评估（无Label无Actions）."""
        self.evaluation_stats["llm_calls"] += 1
        
        try:
            task_info = task.get('task', {})
            instruction = task_info.get('instruction', '')
            response = task.get('result', '')
            
            if not instruction or not response:
                return "unknown"
            
            # 限制长度
            if len(response) > 1500:
                response = response[:1500] + "..."
            
            result = self.prompt_manager.evaluate_with_template(
                'generic_task_evaluation',
                instruction=instruction,
                response=response,
                context="任务执行结果评估"
            )
            
            if 'error' in result:
                print(f"通用评估失败: {result.get('error', '未知错误')}")
                self.evaluation_stats["failed_llm_calls"] += 1
                return "unknown"
            
            overall_quality = result.get('overall_quality', 'unknown')
            self.evaluation_stats["successful_llm_calls"] += 1
            return overall_quality
            
        except Exception as e:
            print(f"通用评估异常: {str(e)}")
            self.evaluation_stats["failed_llm_calls"] += 1
            return "unknown"
    
    def _evaluate_process_quality(self, task: Dict) -> str:
        """评估过程质量."""
        self.evaluation_stats["llm_calls"] += 1
        
        try:
            # 使用任务结果作为"日志"
            result_text = task.get('result', '')
            
            if len(result_text) > 2000:
                result_text = result_text[:2000] + "..."
            
            result = self.prompt_manager.evaluate_with_template(
                'process_quality',
                logs=result_text
            )
            
            if 'error' in result:
                print(f"过程质量评估失败: {result.get('error', '未知错误')}")
                self.evaluation_stats["failed_llm_calls"] += 1
                return "unknown"
            
            quality = result.get('quality', 'unknown')
            self.evaluation_stats["successful_llm_calls"] += 1
            return quality
            
        except Exception as e:
            print(f"过程质量评估异常: {str(e)}")
            self.evaluation_stats["failed_llm_calls"] += 1
            return "unknown"
    
    def _analyze_failure_reason(self, task: Dict, evaluation_type: str) -> str:
        """分析失败原因."""
        self.evaluation_stats["llm_calls"] += 1
        
        try:
            result_text = task.get('result', '')
            error_info = task.get('error', '任务执行失败')
            
            if len(result_text) > 1000:
                result_text = result_text[:1000] + "..."
            
            if len(error_info) > 500:
                error_info = error_info[:500] + "..."
            
            result = self.prompt_manager.evaluate_with_template(
                'failure_analysis',
                logs=result_text,
                error=error_info
            )
            
            if 'error' in result:
                print(f"失败分析失败: {result.get('error', '未知错误')}")
                self.evaluation_stats["failed_llm_calls"] += 1
                return "other_error"
            
            error_type = result.get('error_type', 'other_error')
            self.evaluation_stats["successful_llm_calls"] += 1
            return error_type
            
        except Exception as e:
            print(f"失败分析异常: {str(e)}")
            self.evaluation_stats["failed_llm_calls"] += 1
            return "other_error"
    
    def _print_evaluation_stats(self):
        """打印评估统计信息."""
        print(f"\n{'='*60}")
        print("评估统计信息:")
        print(f"{'='*60}")
        print(f"总LLM调用次数: {self.evaluation_stats.get('llm_calls', 0)}")
        print(f"成功LLM调用: {self.evaluation_stats.get('successful_llm_calls', 0)}")
        print(f"失败LLM调用: {self.evaluation_stats.get('failed_llm_calls', 0)}")
        print(f"环境模拟次数: {self.evaluation_stats.get('env_simulations', 0)}")
        print(f"成功环境模拟: {self.evaluation_stats.get('successful_env_simulations', 0)}")
        print(f"Hash比对次数: {self.evaluation_stats.get('hash_comparisons', 0)}")
        print(f"Hash匹配次数: {self.evaluation_stats.get('hash_matches', 0)}")
        
        if self.evaluation_stats['llm_calls'] > 0:
            success_rate = (self.evaluation_stats['successful_llm_calls'] / 
                          self.evaluation_stats['llm_calls']) * 100
            print(f"LLM调用成功率: {success_rate:.1f}%")
        
        if self.evaluation_stats['hash_comparisons'] > 0:
            hash_match_rate = (self.evaluation_stats['hash_matches'] / 
                             self.evaluation_stats['hash_comparisons']) * 100
            print(f"Hash匹配率: {hash_match_rate:.1f}%")
