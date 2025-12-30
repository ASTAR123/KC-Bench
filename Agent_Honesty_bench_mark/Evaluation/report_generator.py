# file: report_generator.py
"""Report generation module."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class ReportGenerator:
    """Generates evaluation reports and summaries."""
    
    @staticmethod
    def generate_evaluation_report(
        task_completion: Dict[str, Any],
        resource_consumption: Dict[str, Any],
        data_sources: Dict[str, str]
    ) -> Dict[str, Any]:
        """Generate comprehensive evaluation report."""
        return {
            'evaluation_summary': {
                'title': 'Comprehensive Agent Evaluation Report',
                'timestamp': datetime.now().isoformat(),
                'evaluation_framework': 'Hybrid (Environment Simulation + LLM Judge)',
                'data_sources': data_sources
            },
            'task_completion_analysis': task_completion,
            'resource_consumption_analysis': resource_consumption
        }
    
    @staticmethod
    def save_report(report: Dict[str, Any], output_path: str):
        """Save report to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open('w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Generate executive summary
        summary_path = output_path.with_name(f"{output_path.stem}_executive_summary.txt")
        ReportGenerator._generate_executive_summary(report, summary_path)
        
        print(f"Report saved to {output_path}")
        print(f"Executive summary saved to {summary_path}")
    
    @staticmethod
    def _generate_executive_summary(report: Dict[str, Any], output_path: Path):
        """Generate executive summary text file."""
        completion = report['task_completion_analysis']
        resources = report['resource_consumption_analysis']
        
        # 添加评估方法统计
        evaluation_methods = ""
        if 'evaluation_methods_used' in completion and completion['evaluation_methods_used']:
            evaluation_methods = "\n评估方法使用统计:\n"
            for method, count in completion['evaluation_methods_used'].items():
                evaluation_methods += f"  - {method}: {count}\n"
        
        # 添加hash比对统计
        hash_comparison_stats = ""
        if 'hash_comparison_results' in completion and completion['hash_comparison_results']:
            total_comparisons = len(completion['hash_comparison_results'])
            exact_matches = sum(1 for comp in completion['hash_comparison_results'].values() 
                              if comp.get('hash_match', False))
            good_matches = sum(1 for comp in completion['hash_comparison_results'].values() 
                             if comp.get('match_percentage', 0) > 90)
            
            hash_comparison_stats = f"""
    HASHComparison statistics:
    =============
    Total number of comparisons: {total_comparisons}
    exact match: {exact_matches}
    good_matches (>90%): {good_matches}
    Success rate of environmental simulation assessment: {(good_matches/total_comparisons*100 if total_comparisons > 0 else 0):.1f}%
    
    """
        
        summary = f"""
    COMPREHENSIVE AGENT EVALUATION REPORT - EXECUTIVE SUMMARY
    Generated: {report['evaluation_summary']['timestamp']}
    Evaluation Method: Hybrid (Environment Simulation + LLM Judge)

    OVERVIEW
    ========
    Total Tasks Evaluated: {completion.get('total_tasks', 0)}
    Overall Success Rate: {completion.get('success_rate', 0):.2%}
    Successful Tasks: {completion.get('successful_tasks', 0)}
    Failed Tasks: {completion.get('failed_tasks', 0)}
    {evaluation_methods}
    {hash_comparison_stats}
    RESOURCE CONSUMPTION
    ====================
    Average Steps: {resources.get('step_analysis', {}).get('avg_steps', 0):.2f}
    Average Tokens: {resources.get('token_analysis', {}).get('avg_tokens', 0):.2f}
    Average Time: {resources.get('time_analysis', {}).get('avg_time', 0):.2f} seconds

    FAILURE ANALYSIS
    ================
    """
        if 'failure_categories' in completion and completion['failure_categories']:
            for error_type, count in completion['failure_categories'].items():
                summary += f"  - {error_type}: {count}\n"
        else:
            summary += "  No failure analysis available\n"
        
        # Write summary to file
        with output_path.open('w', encoding='utf-8') as f:
            f.write(summary)
