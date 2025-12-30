# file: data_loader.py
"""Data loading utilities for agent evaluation across multiple benchmarks."""

import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd


class DataLoader:
    """Handles loading of evaluation data from various sources for different benchmarks."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.benchmark_type = config.get("benchmark_type", "unknown")
        self.domain = config.get("domain", "")
        
    def load_all_data(self) -> Dict[str, Any]:
        """Load all evaluation data based on benchmark type."""
        if self.benchmark_type == "tau-bench":
            return self._load_tau_bench_data()
        elif self.benchmark_type == "multiagent-bench":
            return self._load_multiagent_bench_data()
        elif self.benchmark_type == "agent-bench":
            return self._load_agent_bench_data()
        else:
            return self._load_generic_data()
    
    def _load_tau_bench_data(self) -> Dict[str, Any]:
        """Load TauBench data."""
        data = {
            'task_results': [],        # Agent的实际结果
            'task_definitions': [],    # 任务定义（包含expected actions）
            'environment_data': {},    # 原始环境数据
            'agent_environment_outputs': {}  # Agent生成的环境数据
        }
        
        # Load Agent的实际结果
        outputs_path = Path(self.config.get('outputs_path', ''))
        if outputs_path.exists():
            data['task_results'] = self.load_jsonl_file(outputs_path)
            print(f"Loaded {len(data['task_results'])} agent task results")
        
        # Load 任务定义（包含expected actions）
        tasks_path = Path(self.config.get('tasks_path', ''))
        if tasks_path.exists():
            data['task_definitions'] = self.load_jsonl_file(tasks_path)
            print(f"Loaded {len(data['task_definitions'])} task definitions")
        
        # Load original environment data
        env_path = Path(self.config.get('environment_data_path', ''))
        if env_path.exists():
            data['environment_data'] = self._load_environment_data(env_path)
            print(f"Loaded environment data from {env_path}")
            
            # Extract agent's environment outputs from results
            data['agent_environment_outputs'] = self._extract_agent_environment_outputs(
                data['task_results']
            )
        
        return data
    
    def _load_multiagent_bench_data(self) -> Dict[str, Any]:
        """Load MultiAgentBench data."""
        data = {
            'task_results': [],
            'task_definitions': [],
            'environment_data': {}
        }
        
        outputs_path = Path(self.config.get('outputs_path', ''))
        if outputs_path.exists():
            data['task_results'] = self.load_jsonl_file(outputs_path)
        
        tasks_path = Path(self.config.get('tasks_path', ''))
        if tasks_path.exists():
            data['task_definitions'] = self.load_jsonl_file(tasks_path)
        
        env_path = Path(self.config.get('environment_data_path', ''))
        if env_path.exists():
            data['environment_data'] = self._load_environment_data(env_path)
        
        return data
    
    def _load_agent_bench_data(self) -> Dict[str, Any]:
        """Load AgentBench data."""
        data = {
            'task_results': [],
            'task_definitions': [],
            'environment_data': {}
        }
        
        outputs_path = Path(self.config.get('outputs_path', ''))
        if outputs_path.exists():
            data['task_results'] = self.load_jsonl_file(outputs_path)
        
        tasks_path = Path(self.config.get('tasks_path', ''))
        if tasks_path.exists():
            data['task_definitions'] = self.load_jsonl_file(tasks_path)
        
        env_path = Path(self.config.get('environment_data_path', ''))
        if env_path.exists():
            data['environment_data'] = self._load_environment_data(env_path)
        
        return data
    
    def _load_generic_data(self) -> Dict[str, Any]:
        """Load generic benchmark data."""
        data = {
            'task_results': [],
            'task_definitions': [],
            'environment_data': {}
        }
        
        outputs_path = Path(self.config.get('outputs_path', ''))
        if outputs_path.exists():
            data['task_results'] = self.load_jsonl_file(outputs_path)
        
        tasks_path = Path(self.config.get('tasks_path', ''))
        if tasks_path.exists():
            data['task_definitions'] = self.load_jsonl_file(tasks_path)
        
        env_path = Path(self.config.get('environment_data_path', ''))
        if env_path.exists():
            data['environment_data'] = self._load_environment_data(env_path)
        
        return data
    
    def _load_environment_data(self, env_path: Path) -> Dict[str, Any]:
        """Load environment data from directory."""
        environment_data = {}
        
        try:
            # Load all files recursively
            for file_path in env_path.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(env_path))
                    
                    try:
                        if file_path.suffix == '.csv':
                            df = pd.read_csv(file_path)
                            environment_data[rel_path] = df.to_dict('records')
                        elif file_path.suffix == '.json':
                            with file_path.open('r', encoding='utf-8') as f:
                                environment_data[rel_path] = json.load(f)
                        elif file_path.suffix in ['.txt', '.md']:
                            with file_path.open('r', encoding='utf-8') as f:
                                environment_data[rel_path] = f.read()
                        else:
                            # 其他文件类型
                            with file_path.open('r', encoding='utf-8') as f:
                                environment_data[rel_path] = f.read()
                    except Exception as e:
                        print(f"  Warning: Could not load file {rel_path}: {str(e)}")
                        environment_data[rel_path] = f"ERROR_LOADING: {str(e)}"
                            
        except Exception as e:
            print(f"Error loading environment data from {env_path}: {str(e)}")
        
        return environment_data
    
    def _extract_agent_environment_outputs(self, task_results: List[Dict]) -> Dict[str, Any]:
        """Extract agent's environment output data from task results."""
        agent_outputs = {}
        
        for task in task_results:
            task_id = task.get('task_id', '')
            result = task.get('result', '')
            
            if not task_id or not result:
                continue
            
            # Try to parse environment state from result
            try:
                # 尝试解析JSON
                if result.strip().startswith('{') or result.strip().startswith('['):
                    env_state = json.loads(result)
                    if isinstance(env_state, dict) and ('environment' in env_state or 'state' in env_state):
                        # 提取环境状态
                        agent_outputs[task_id] = env_state.get('environment', env_state.get('state', env_state))
                    else:
                        # 整个结果就是环境状态
                        agent_outputs[task_id] = env_state
                else:
                    # 尝试查找环境数据模式
                    import re
                    # 查找CSV格式数据
                    csv_pattern = r'(\w+\.csv:\s*\n(?:.*\n)*?.*\n?)'
                    csv_matches = re.findall(csv_pattern, result, re.MULTILINE)
                    
                    # 查找JSON格式数据
                    json_pattern = r'(\{.*?\})'
                    json_matches = re.findall(json_pattern, result, re.DOTALL)
                    
                    if csv_matches or json_matches:
                        agent_outputs[task_id] = {
                            'text_result': result[:500] + "..." if len(result) > 500 else result
                        }
            except json.JSONDecodeError:
                # 如果不是JSON，保存原始结果
                agent_outputs[task_id] = {
                    'raw_result': result[:1000] + "..." if len(result) > 1000 else result
                }
            except Exception as e:
                print(f"Error extracting environment output for task {task_id}: {str(e)}")
        
        print(f"Extracted {len(agent_outputs)} agent environment outputs")
        return agent_outputs
    
    def load_jsonl_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Load data from JSONL file."""
        if not file_path.exists():
            return []
            
        records = []
        with file_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse JSON line: {line[:100]}")
                        continue
        return records
    
    def get_task_definition_by_id(self, task_id: str, task_definitions: List[Dict]) -> Dict:
        """Get task definition by task ID."""
        for task_def in task_definitions:
            if task_def.get('task_id') == task_id:
                return task_def
        return {}
    
    def extract_expected_actions(self, task_definition: Dict) -> List[Dict]:
        """Extract expected actions from task definition."""
        actions = []
        
        # 从task字段中提取actions
        task_info = task_definition.get('task', {})
        
        # 方法1: 直接有actions字段
        if 'actions' in task_info:
            actions = task_info['actions']
        # 方法2: 从label中提取actions
        elif 'label' in task_info:
            label = task_info['label']
            if isinstance(label, list):
                # 尝试从label中解析actions
                for item in label:
                    if isinstance(item, dict) and 'action' in item:
                        actions.append(item['action'])
                    elif isinstance(item, str) and 'action' in item.lower():
                        # 尝试解析字符串格式的action
                        try:
                            action_data = json.loads(item)
                            if isinstance(action_data, dict) and 'name' in action_data:
                                actions.append(action_data)
                        except:
                            pass
        # 方法3: 从metadata中提取
        elif 'metadata' in task_info and 'expected_actions' in task_info['metadata']:
            actions = task_info['metadata']['expected_actions']
        
        # 验证actions格式
        validated_actions = []
        for action in actions:
            if isinstance(action, dict) and 'name' in action:
                validated_actions.append(action)
        
        return validated_actions
