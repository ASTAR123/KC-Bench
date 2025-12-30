#资源消耗分析
"""Resource consumption analysis module."""

import statistics
from typing import Dict, Any, List


class ResourceAnalyzer:
    """Analyzes resource consumption metrics."""
    
    @staticmethod
    def analyze_resource_consumption(task_results: List[Dict]) -> Dict[str, Any]:
        """Analyze resource consumption statistics."""
        steps_data = []
        token_data = []
        time_data = []
        
        for task in task_results:
            if task.get('step_count'):
                steps_data.append(task['step_count'])
            if task.get('total_tokens'):
                token_data.append(task['total_tokens'])
            if task.get('elapsed_seconds'):
                time_data.append(task['elapsed_seconds'])
        
        return {
            'step_analysis': ResourceAnalyzer._build_stats(steps_data, 'steps'),
            'token_analysis': ResourceAnalyzer._build_stats(token_data, 'tokens'),
            'time_analysis': ResourceAnalyzer._build_stats(time_data, 'time')
        }
    
    @staticmethod
    def _build_stats(values: List[float], prefix: str) -> Dict[str, float]:
        """Build statistical summary for a metric."""
        if not values:
            return {
                f'avg_{prefix}': 0,
                f'median_{prefix}': 0,
                f'min_{prefix}': 0,
                f'max_{prefix}': 0,
                f'std_{prefix}': 0
            }
        
        return {
            f'avg_{prefix}': statistics.mean(values),
            f'median_{prefix}': statistics.median(values),
            f'min_{prefix}': min(values),
            f'max_{prefix}': max(values),
            f'std_{prefix}': statistics.stdev(values) if len(values) > 1 else 0
        }

