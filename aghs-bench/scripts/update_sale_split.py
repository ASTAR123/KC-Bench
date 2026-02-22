import json

TASKS_PATH = "/mnt/shared-storage-user/lvyaxing/Agent_Honesty/tau2-bench/data/tau2/domains/deception/tasks.json"
SPLIT_PATH = "/mnt/shared-storage-user/lvyaxing/Agent_Honesty/tau2-bench/data/tau2/domains/deception/split_tasks.json"

with open(TASKS_PATH, "r") as f:
    tasks = json.load(f)

with open(SPLIT_PATH, "r") as f:
    split = json.load(f)

# Get all sale task IDs
sale_task_ids = [task["id"] for task in tasks if task["id"].startswith("sale_")]

# Remove old sale tasks from split
for key in split:
    split[key] = [tid for tid in split[key] if not tid.startswith("sale_")]

# Add new sale tasks to split (e.g., all to test)
split.setdefault("test", []).extend(sale_task_ids)

with open(SPLIT_PATH, "w") as f:
    json.dump(split, f, indent=4)

print("split_tasks.json updated successfully.")
