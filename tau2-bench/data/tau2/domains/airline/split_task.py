import json
import os

def split_tasks():
    """按照split_tasks.json将tasks.json拆分成训练集和测试集"""
    
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 读取split_tasks.json
    split_file = os.path.join(current_dir, 'split_tasks.json')
    with open(split_file, 'r', encoding='utf-8') as f:
        split_config = json.load(f)
    
    # 读取tasks.json
    tasks_file = os.path.join(current_dir, 'tasks.json')
    with open(tasks_file, 'r', encoding='utf-8') as f:
        all_tasks = json.load(f)
    
    # 创建ID到任务的映射
    task_dict = {task['id']: task for task in all_tasks}
    
    # 根据split_config筛选train和test任务
    train_tasks = [task_dict[task_id] for task_id in split_config['train'] if task_id in task_dict]
    test_tasks = [task_dict[task_id] for task_id in split_config['test'] if task_id in task_dict]
    
    # 写入train_tasks.json
    train_file = os.path.join(current_dir, 'train_tasks.json')
    with open(train_file, 'w', encoding='utf-8') as f:
        json.dump(train_tasks, f, indent=4, ensure_ascii=False)
    
    # 写入test_tasks.json
    test_file = os.path.join(current_dir, 'test_tasks.json')
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_tasks, f, indent=4, ensure_ascii=False)
    
    print(f"拆分完成！")
    print(f"训练集任务数: {len(train_tasks)}")
    print(f"测试集任务数: {len(test_tasks)}")
    print(f"训练集文件: {train_file}")
    print(f"测试集文件: {test_file}")

if __name__ == '__main__':
    split_tasks()
