# file: comprehensive_evaluation_system.py
"""Main comprehensive evaluation system that orchestrates all components."""

import json
from pathlib import Path
from typing import Dict, Any
from data_loader import DataLoader
from prompt_manager import PromptManager
from task_evaluator import TaskEvaluator
from resource_analyzer import ResourceAnalyzer
from report_generator import ReportGenerator


class ComprehensiveEvaluationSystem:
    """Orchestrates the complete evaluation pipeline for multiple benchmarks."""
    
    def __init__(
        self, 
        config: Dict[str, Any],
        prompt_template_path: str = "evaluation_prompts.yaml",
        judge_model: str = "gpt-4",
    ):
        """
        Initialize evaluation system with configuration.
        
        Args:
            config: Configuration dict with benchmark-specific settings
            prompt_template_path: Path to prompt templates
            judge_model: Model to use for evaluation
        """
        self.config = config
        self.benchmark_type = config.get("benchmark_type", "unknown")
        self.data_loader = DataLoader(config)
        self.prompt_manager = PromptManager(
                prompt_template_path=prompt_template_path,
                judge_model=judge_model,
            )
        self.task_evaluator = TaskEvaluator(self.prompt_manager, config)
        self.data = None
    
    def load_data(self):
        """Load all evaluation data based on benchmark type."""
        self.data = self.data_loader.load_all_data()
        
        print(f"数据加载完成:")
        print(f"  - Agent任务结果: {len(self.data.get('task_results', []))} 个")
        print(f"  - 任务定义: {len(self.data.get('task_definitions', []))} 个")
        print(f"  - 环境数据文件: {len(self.data.get('environment_data', {}))} 个")
        print(f"  - Agent环境输出: {len(self.data.get('agent_environment_outputs', {}))} 个")
        
        # 设置data_loader到task_evaluator
        self.task_evaluator.set_data_loader(self.data_loader)
    
    def run_evaluation(self) -> Dict[str, Any]:
        """Run complete evaluation pipeline for the configured benchmark."""
        if not self.data:
            self.load_data()
        
        if self.benchmark_type == "tau-bench":
            return self._run_tau_bench_evaluation()
        elif self.benchmark_type == "multiagent-bench":
            return self._run_multiagent_bench_evaluation()
        elif self.benchmark_type == "agent-bench":
            return self._run_agent_bench_evaluation()
        else:
            return self._run_generic_evaluation()
    
    def _run_tau_bench_evaluation(self) -> Dict[str, Any]:
        """Run evaluation for TauBench (action-based tasks)."""
        task_completion = self.task_evaluator.analyze_task_completion(
            self.data['task_results'], 
            self.data['task_definitions'],
            self.data.get('environment_data', {}),
            self.data.get('agent_environment_outputs', {})
        )
        
        resource_consumption = ResourceAnalyzer.analyze_resource_consumption(
            self.data['task_results']
        )
        
        # Generate report
        data_sources = {
            'benchmark_type': 'tau-bench',
            'outputs_path': self.config.get('outputs_path', 'Not provided'),
            'tasks_path': self.config.get('tasks_path', 'Not provided'),
            'environment_data_path': self.config.get('environment_data_path', 'Not provided'),
            'domain': self.config.get('domain', ''),
            'evaluation_strategy': 'Hybrid (Environment Simulation + LLM Judge)',
            'evaluation_logic': 'Based on data type selection evaluation method: 1) Only Label uses LLM, 2) Only Expected Actions uses environment simulator, 3) Both are evaluated comprehensively'
        }
        
        report = ReportGenerator.generate_evaluation_report(
            task_completion,
            resource_consumption,
            data_sources
        )
        
        return report
    
    def _run_multiagent_bench_evaluation(self) -> Dict[str, Any]:
        """Run evaluation for MultiAgentBench."""
        task_results = self.data['task_results']
        task_definitions = self.data['task_definitions']
        
        # Use task evaluator for multiagent tasks
        task_completion = self.task_evaluator.analyze_task_completion(
            task_results,
            task_definitions,
            self.data.get('environment_data', {}),
            {}
        )
        
        resource_consumption = ResourceAnalyzer.analyze_resource_consumption(task_results)
        
        data_sources = {
            'benchmark_type': 'multiagent-bench',
            'outputs_path': self.config.get('outputs_path', 'Not provided'),
            'tasks_path': self.config.get('tasks_path', 'Not provided'),
            'environment_data_path': self.config.get('environment_data_path', 'Not provided'),
            'evaluation_strategy': 'LLM Judge + Environment Simulation'
        }
        
        report = ReportGenerator.generate_evaluation_report(
            task_completion,
            resource_consumption,
            data_sources
        )
        
        return report
    
    def _run_agent_bench_evaluation(self) -> Dict[str, Any]:
        """Run evaluation for AgentBench."""
        task_results = self.data['task_results']
        task_definitions = self.data['task_definitions']
        
        # Use task evaluator for agent bench tasks
        task_completion = self.task_evaluator.analyze_task_completion(
            task_results,
            task_definitions,
            self.data.get('environment_data', {}),
            {}
        )
        
        resource_consumption = ResourceAnalyzer.analyze_resource_consumption(task_results)
        
        data_sources = {
            'benchmark_type': 'agent-bench',
            'outputs_path': self.config.get('outputs_path', 'Not provided'),
            'tasks_path': self.config.get('tasks_path', 'Not provided'),
            'environment_data_path': self.config.get('environment_data_path', 'Not provided'),
            'evaluation_strategy': 'LLM Judge + Environment Simulation'
        }
        
        report = ReportGenerator.generate_evaluation_report(
            task_completion,
            resource_consumption,
            data_sources
        )
        
        return report
    
    def _run_generic_evaluation(self) -> Dict[str, Any]:
        """Run generic evaluation for unknown benchmark types."""
        task_results = self.data['task_results']
        task_definitions = self.data['task_definitions']
        
        # Use task evaluator for generic tasks
        task_completion = self.task_evaluator.analyze_task_completion(
            task_results,
            task_definitions,
            self.data.get('environment_data', {}),
            {}
        )
        
        resource_consumption = ResourceAnalyzer.analyze_resource_consumption(task_results)
        
        data_sources = {
            'benchmark_type': 'generic',
            'outputs_path': self.config.get('outputs_path', 'Not provided'),
            'tasks_path': self.config.get('tasks_path', 'Not provided'),
            'environment_data_path': self.config.get('environment_data_path', 'Not provided'),
            'evaluation_strategy': 'LLM Judge'
        }
        
        report = ReportGenerator.generate_evaluation_report(
            task_completion,
            resource_consumption,
            data_sources
        )
        
        return report
    
    def save_report(self, report: Dict[str, Any], output_path: str):
        """Save evaluation report."""
        ReportGenerator.save_report(report, output_path)


# Usage examples for different benchmarks
if __name__ == "__main__":
    # Example 1: TauBench (Airline) with environment simulation
    tau_bench_config = {
        "benchmark_type": "tau-bench",
        "outputs_path": "results_20251126_192126.jsonl",
        "tasks_path": "tasks_test.jsonl",
        "domain": "airline",
        "environment_data_path": "environment_data/airline"
    }
    
    evaluator1 = ComprehensiveEvaluationSystem(
        config=tau_bench_config,
        prompt_template_path="evaluation_prompts.yaml",
        judge_model="gpt-3.5-turbo"
    )
    
    report1 = evaluator1.run_evaluation()
    evaluator1.save_report(report1, "tau_bench_airline_evaluation_report.json")
