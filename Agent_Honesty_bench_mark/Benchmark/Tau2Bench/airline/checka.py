import json
import re

def check_communicate_info_in_assertions(jsonl_path):
    """
    检查 tasks.jsonl 中每个 entity 的 evaluation_criteria.communicate_info 
    中的字符串是否都在 nl_assertions 中出现
    """
    total_checked = 0
    total_matched = 0
    total_missing = 0
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            task = json.loads(line.strip())
            task_id = task.get('task_id', 'unknown')
            
            eval_criteria = task.get('evaluation_criteria', {})
            communicate_info = eval_criteria.get('communicate_info', [])
            nl_assertions = eval_criteria.get('nl_assertions', [])
            
            # 如果 communicate_info 或 nl_assertions 为空，跳过检查
            if not communicate_info or not nl_assertions:
                continue
            
            total_checked += 1
            
            # 将所有 nl_assertions 合并成一个字符串用于搜索
            assertions_text = ' '.join(nl_assertions)
            
            # 检查每个 communicate_info 中的字符串
            matched_info = []
            missing_info = []
            
            for info in communicate_info:
                info_str = str(info)
                # 移除可能的格式字符（如逗号、美元符号）进行更灵活的匹配
                info_pattern = re.escape(info_str).replace(r'\,', r',?')
                # 检查是否在 assertions 中出现（可能带有格式化字符）
                if re.search(info_pattern, assertions_text) or info_str in assertions_text:
                    matched_info.append(info)
                else:
                    missing_info.append(info)
            
            # 打印检查结果
            if matched_info or missing_info:
                print(f"Task ID {task_id} (Line {line_num}):")
                if matched_info:
                    print(f"  ✓ Matched: {matched_info}")
                    total_matched += len(matched_info)
                if missing_info:
                    print(f"  ✗ Missing: {missing_info}")
                    total_missing += len(missing_info)
                print(f"  communicate_info: {communicate_info}")
                print(f"  nl_assertions: {nl_assertions}")
                print()
    
    print(f"\n=== 统计结果 ===")
    print(f"检查的任务数: {total_checked}")
    print(f"匹配的项数: {total_matched}")
    print(f"缺失的项数: {total_missing}")

if __name__ == '__main__':
    jsonl_path = '/mnt/shared-storage-user/lvyaxing/Agent-Sandbox-and-Evaluation/Benchmark/Tau2Bench/airline/tasks.jsonl'
    print("检查 communicate_info 是否在 nl_assertions 中...\n")
    check_communicate_info_in_assertions(jsonl_path)
    print("检查完成!")
