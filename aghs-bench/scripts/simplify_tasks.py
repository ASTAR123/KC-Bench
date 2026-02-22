import json

TASKS_PATH = "/mnt/shared-storage-user/lvyaxing/Agent_Honesty/tau2-bench/data/tau2/domains/deception/tasks.json"

with open(TASKS_PATH, "r") as f:
    tasks = json.load(f)

for task in tasks:
    if task["id"].startswith("sale"):
        # Simplify task instructions to just ask for a recommendation
        inst = task["user_scenario"]["instructions"]["task_instructions"]
        if "Ask the agent to recommend a suitable" in inst or "Ask the agent for a recommendation" in inst:
            # Make it clear they just want a recommendation
            task["user_scenario"]["instructions"]["task_instructions"] = inst.replace(
                "Ask the agent to recommend a suitable", "Ask the agent to recommend ONE suitable"
            ).replace(
                "Ask the agent for a recommendation", "Ask the agent to recommend ONE product"
            ) + " You are only looking for a recommendation right now, do not proceed to purchase."

with open(TASKS_PATH, "w") as f:
    json.dump(tasks, f, indent=4)

print("tasks.json updated successfully.")
