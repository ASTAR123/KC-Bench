import json
import os

def _extract_task_description(task):
    """Extract and format the task description based on the benchmark type"""
    user_scenario = task.get("user_scenario", {})
    instructions = user_scenario.get("instructions", {})
    
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

def _build_label(entity):
    """
    构建 label 字段:
    - 开头: Task_description: <Task_description内容>
    - 若 communicate_info 非空: The communication information between the user and the Assistant must include <内容>
    - 若 nl_assertions 非空: expectedOutcomes: 逐条换行
    - 若 annotations 非空: annotations: <annotations内容>
    - 若 communicate_info 和 nl_assertions 都为空，返回空字符串
    """
    eval_criteria = entity.get("evaluation_criteria", {}) or {}
    communicate_info = eval_criteria.get("communicate_info") or []
    nl_assertions = eval_criteria.get("nl_assertions") or []
    annotations = eval_criteria.get("annotations")
    
    # 如果 communicate_info、nl_assertions 和 annotations 都为空，返回空字符串
    if not communicate_info and not nl_assertions and annotations is None:
        return ""
    
    label_parts = []

    task_desc = entity.get("Task_description")
    # 将 Task_description 原样嵌入为 JSON 字符串，避免信息丢失
    task_desc_str = json.dumps(task_desc, ensure_ascii=False) if task_desc is not None else "null"
    label_parts.append(f"Task_description: {task_desc_str}")

    if communicate_info:
        ci_str = ", ".join(str(x) for x in communicate_info)
        label_parts.append(f"The communication information between the user and the Assistant must include {ci_str}")

    if nl_assertions:
        # 先加入标题，再逐条换行
        label_parts.append("expectedOutcomes:")
        na_str = "\n".join(str(x) for x in nl_assertions)
        label_parts.append(na_str)

    if annotations is not None:
        annotations_str = json.dumps(annotations, ensure_ascii=False) if annotations else "null"
        label_parts.append(f"annotations: {annotations_str}")

    return "\n".join(label_parts)

def transform_entity(entity, split):
    """转换单个实体的格式"""
    new_entity = dict(entity)

    eval_criteria = entity.get("evaluation_criteria", {}) or {}
    new_entity["actions"] = eval_criteria.get("actions", []) or []
    new_entity["label"] = _build_label(new_entity)

    # 删除原始的三个字段
    new_entity.pop("Task_description", None)
    new_entity.pop("user_scenario", None)
    new_entity.pop("evaluation_criteria", None)

    return new_entity

def transform_jsonl_file(input_file, output_file, split):
    """转换JSONL文件"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(current_dir, input_file)
    output_path = os.path.join(current_dir, output_file)
    
    if not os.path.exists(input_path):
        print(f"警告: 文件不存在 - {input_path}\n")
        return
    
    transformed_count = 0
    
    with open(input_path, 'r', encoding='utf-8') as f_in, \
         open(output_path, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            if line.strip():  # 跳过空行
                entity = json.loads(line)
                transformed_entity = transform_entity(entity, split)
                f_out.write(json.dumps(transformed_entity, ensure_ascii=False) + '\n')
                transformed_count += 1
    
    print(f"已转换 {input_file} -> {output_file}")
    print(f"共转换 {transformed_count} 条记录\n")

def main():
    """主函数"""
    # 定义需要转换的文件
    files_to_transform = [
        ('train_tasks.jsonl', 'train_tasks_transformed.jsonl', 'train'),
        ('test_tasks.jsonl', 'test_tasks_transformed.jsonl', 'test'),
        ('tasks.jsonl', 'tasks_transformed.jsonl', 'all')
    ]
    
    for input_file, output_file, split in files_to_transform:
        transform_jsonl_file(input_file, output_file, split)
    
    print("所有文件转换完成!")

if __name__ == '__main__':
    main()