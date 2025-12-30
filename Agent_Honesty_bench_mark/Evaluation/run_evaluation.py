# file: run_evaluation.py
import os
import sys
import time
from pathlib import Path
from datetime import datetime


# 添加当前目录到路径，确保可以导入模块
sys.path.append(str(Path(__file__).parent))

from comprehensive_evaluation_system import ComprehensiveEvaluationSystem

def run_evaluation_with_retry(config, max_retries=3):
    """运行评估并自动重试失败的任务."""
    for attempt in range(max_retries):
        try:
            print(f"\n{'='*60}")
            print(f"评估尝试 {attempt + 1}/{max_retries}")
            print(f"{'='*60}")
            
            # 使用更稳定的模型
            evaluator = ComprehensiveEvaluationSystem(
                config=config,
                prompt_template_path="evaluation_prompts.yaml",
                judge_model="gpt-3.5-turbo"  # 使用标准模型
            )
            
            print("加载数据...")
            evaluator.load_data()
            
            print("运行评估...")
            report = evaluator.run_evaluation()
            
            return evaluator, report
            
        except Exception as e:
            print(f"评估尝试 {attempt + 1} 失败: {str(e)}")
            if attempt < max_retries - 1:
                wait_time = 5 * (attempt + 1)
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                raise
    
    return None, None

def main():
    # 1. 设置API密钥
    api_key = "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"
    os.environ["OPENAI_API_KEY"] = api_key
    
    print(f"设置API密钥: {api_key[:15]}...")
    
    # 2. 检查数据文件是否存在
    print("检查数据文件...")
    result_file = Path("results_20251126_192126.jsonl")
    tasks_file = Path("tasks_test.jsonl")
    env_data_dir = Path("environment_data/airline")
    
    if not result_file.exists():
        print(f"错误: Agent结果文件不存在: {result_file}")
        return
    
    if not tasks_file.exists():
        print(f"错误: 任务定义文件不存在: {tasks_file}")
        return
    
    if not env_data_dir.exists():
        print(f"警告: 环境数据目录不存在: {env_data_dir}")
        print("将仅使用LLM评估，环境模拟不可用")
    
    # 3. 配置
    config = {
        "benchmark_type": "tau-bench",
        "outputs_path": str(result_file),
        "tasks_path": str(tasks_file),
        "domain": "airline",
        "environment_data_path": str(env_data_dir) if env_data_dir.exists() else ""
    }
    
    # 4. 运行评估（带重试）
    try:
        evaluator, report = run_evaluation_with_retry(config, max_retries=3)
        
        if not report:
            print("评估失败，所有重试都失败了")
            return
        
        # 5. 输出结果
        print("\n" + "="*60)
        print("评估结果摘要:")
        print("="*60)
        
        completion = report.get('task_completion_analysis', {})
        print(f"总任务数: {completion.get('total_tasks', 0)}")
        print(f"成功任务数: {completion.get('successful_tasks', 0)}")
        print(f"失败任务数: {completion.get('failed_tasks', 0)}")
        print(f"成功率: {completion.get('success_rate', 0):.2%}")
        
        # 打印评估方法统计
        if 'evaluation_methods_used' in completion and completion['evaluation_methods_used']:
            print("\n评估方法使用统计:")
            for method, count in completion['evaluation_methods_used'].items():
                print(f"  - {method}: {count}")
        
        # 打印hash比对结果
        if 'hash_comparison_stats' in completion:
            print("\nHash比对统计:")
            stats = completion['hash_comparison_stats']
            print(f"  - 总比对次数: {stats.get('total_comparisons', 0)}")
            print(f"  - Hash匹配次数: {stats.get('hash_matches', 0)}")
            print(f"  - Hash匹配率: {stats.get('hash_match_rate', 0):.2%}")
        
        # 打印详细hash比对结果
        if 'hash_comparison_results' in completion and completion['hash_comparison_results']:
            print("\n详细Hash比对结果:")
            for task_id, comparison in completion['hash_comparison_results'].items():
                if comparison.get('hash_match'):
                    print(f"  - {task_id}: ✓ Hash完全匹配")
                else:
                    match_percent = comparison.get('match_percentage', 0)
                    if match_percent > 90:
                        print(f"  - {task_id}: ✓ Hash高度匹配 ({match_percent:.1f}%)")
                    else:
                        print(f"  - {task_id}: ✗ Hash不匹配 ({match_percent:.1f}%)")
        
        # 打印LLM统计
        if 'llm_evaluation_stats' in completion:
            print("\nLLM评估统计:")
            stats = completion['llm_evaluation_stats']
            print(f"  - 总LLM调用: {stats.get('llm_calls', 0)}")
            print(f"  - 成功LLM调用: {stats.get('successful_llm_calls', 0)}")
            print(f"  - 失败LLM调用: {stats.get('failed_llm_calls', 0)}")
            
            if stats.get('llm_calls', 0) > 0:
                success_rate = (stats.get('successful_llm_calls', 0) / 
                              stats.get('llm_calls', 0)) * 100
                print(f"  - LLM调用成功率: {success_rate:.1f}%")
        
        # 打印详细分析
        if 'process_analysis' in completion and completion['process_analysis']:
            print("\n过程质量分析:")
            for quality, count in completion['process_analysis'].items():
                print(f"  - {quality}: {count}")
        
        if 'outcome_analysis' in completion and completion['outcome_analysis']:
            print("\n结果质量分析:")
            for quality, count in completion['outcome_analysis'].items():
                print(f"  - {quality}: {count}")
        
        if 'action_based_analysis' in completion and completion['action_based_analysis']:
            print("\nAction执行质量分析:")
            for quality, count in completion['action_based_analysis'].items():
                print(f"  - {quality}: {count}")
        
        if 'failure_categories' in completion and completion['failure_categories']:
            print("\n失败原因分类:")
            for error_type, count in completion['failure_categories'].items():
                print(f"  - {error_type}: {count}")
        
        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"evaluation_report_{timestamp}.json"
        evaluator.save_report(report, output_file)
        print(f"\n详细报告已保存到: {output_file}")
        
               
    except Exception as e:
        print(f"评估过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
