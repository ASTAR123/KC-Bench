import json
import os

def _extract_task_description(task):
    """Extract and format the task description based on the benchmark type"""
    user_scenario = task.get("user_scenario", {})
    
    # 确保user_scenario是字典类型
    if not isinstance(user_scenario, dict):
        return "**Instructions**: N/A"
    
    instructions = user_scenario.get("instructions", {})
    
    # 确保instructions是字典类型
    if not isinstance(instructions, dict):
        return "**Instructions**: N/A"
    
    parts = []
    parts.append("**Instructions**:")
    
    # Domain
    domain = instructions.get("domain", "")
    if domain:
        parts.append(f"- **Domain**: {domain}")
    
    # Reason for call
    reason = instructions.get("reason_for_call", "")
    if reason:
        parts.append(f"- **Reason for call**: {reason}")
    
    # Known info
    known_info = instructions.get("known_info", "")
    if known_info:
        parts.append(f"- **Known info**: {known_info}")
    
    # Unknown info
    unknown_info = instructions.get("unknown_info")
    parts.append(f"- **Unknown info**: {unknown_info if unknown_info else 'null'}")
    
    # Task instructions
    task_instructions = instructions.get("task_instructions", "")
    if task_instructions:
        parts.append(f"- **Task instructions**: {task_instructions}")
    
    return "\n\n".join(parts)

def transform_entity(entity, split):
    """转换单个实体的格式"""
    # 创建新的实体,按照指定顺序添加字段
    new_entity = {
        "task_id": entity.get("id"),
        "benchmark_suite": "tau2-bench",
        "domain": "telecom",
        "split": split,
        "instruction": _extract_task_description(entity),
        "environment_paths": ["Environment/Tau2Bench/telecom/data"]
    }
    
    # 复制其他字段(除了id)
    for key, value in entity.items():
        if key == "id":
            continue
        elif key == "description":
            new_entity["Task_description"] = value
        else:
            new_entity[key] = value
    
    return new_entity

def process_file(input_file, output_file, split):
    """读取JSON文件(数组)，转换格式，并写入JSONL文件"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(current_dir, input_file)
    output_path = os.path.join(current_dir, output_file)
    
    if not os.path.exists(input_path):
        print(f"警告: 文件不存在 - {input_path}\n")
        return
    
    try:
        # 读取JSON文件 (数组格式)
        with open(input_path, 'r', encoding='utf-8') as f_in:
            data = json.load(f_in)
            
        if not isinstance(data, list):
            print(f"错误: {input_file} 不是JSON数组格式")
            return

        transformed_count = 0
        
        # 写入JSONL文件
        with open(output_path, 'w', encoding='utf-8') as f_out:
            for idx, entity in enumerate(data):
                try:
                    transformed_entity = transform_entity(entity, split)
                    f_out.write(json.dumps(transformed_entity, ensure_ascii=False) + '\n')
                    transformed_count += 1
                except Exception as e:
                    print(f"警告: 处理第 {idx} 条记录时出错: {str(e)}")
                    continue
        
        print(f"已转换 {input_file} -> {output_file}")
        print(f"共转换 {transformed_count} 条记录\n")
        
    except json.JSONDecodeError as e:
        print(f"错误: {input_file} JSON解析失败: {str(e)}")
    except Exception as e:
        print(f"处理 {input_file} 时发生错误: {str(e)}")

def split_jsonl_by_config():
    """按照split_tasks.json将转换后的jsonl文件拆分成训练集和测试集"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 读取split_tasks.json
    split_file = os.path.join(current_dir, 'split_tasks.json')
    if not os.path.exists(split_file):
        print(f"警告: split_tasks.json 不存在，跳过拆分步骤\n")
        return
    
    with open(split_file, 'r', encoding='utf-8') as f:
        split_config = json.load(f)
    
    # 读取转换后的tasks.jsonl
    tasks_jsonl = os.path.join(current_dir, 'tasks.jsonl')
    if not os.path.exists(tasks_jsonl):
        print(f"警告: tasks.jsonl 不存在，无法进行拆分\n")
        return
    
    # 读取所有任务
    all_tasks = {}
    with open(tasks_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                task = json.loads(line)
                all_tasks[task['task_id']] = task
    
    # 拆分训练集
    train_output = os.path.join(current_dir, 'train_tasks.jsonl')
    train_count = 0
    with open(train_output, 'w', encoding='utf-8') as f:
        for task_id in split_config.get('train', []):
            if task_id in all_tasks:
                f.write(json.dumps(all_tasks[task_id], ensure_ascii=False) + '\n')
                train_count += 1
    
    # 拆分测试集
    test_output = os.path.join(current_dir, 'test_tasks.jsonl')
    test_count = 0
    with open(test_output, 'w', encoding='utf-8') as f:
        for task_id in split_config.get('test', []):
            if task_id in all_tasks:
                f.write(json.dumps(all_tasks[task_id], ensure_ascii=False) + '\n')
                test_count += 1
    
    print(f"数据拆分完成！")
    print(f"训练集: {train_output} ({train_count} 条记录)")
    print(f"测试集: {test_output} ({test_count} 条记录)\n")

def main():
    """主函数"""
    # 定义需要转换的文件
    # 输入是json(数组), 输出是jsonl
    files_to_transform = [
        ('train_tasks.json', 'train_tasks.jsonl', 'train'),
        ('test_tasks.json', 'test_tasks.jsonl', 'test'),
        ('tasks.json', 'tasks.jsonl', 'all')
    ]
    
    for input_file, output_file, split in files_to_transform:
        process_file(input_file, output_file, split)
    
    print("所有文件转换完成!")
    
    # 执行数据拆分
    split_jsonl_by_config()

if __name__ == '__main__':
    main()