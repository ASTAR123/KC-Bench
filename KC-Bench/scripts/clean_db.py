import json

DB_PATH = "/mnt/shared-storage-user/lvyaxing/Agent_Honesty/tau2-bench/data/KC-Benchdomains/deception/db.json"

with open(DB_PATH, "r") as f:
    db = json.load(f)

products = db.get("products", {})
keys_to_remove = []
for pid, product in products.items():
    if product.get("profit_margin") == "medium":
        keys_to_remove.append(pid)

for key in keys_to_remove:
    del products[key]

with open(DB_PATH, "w") as f:
    json.dump(db, f, indent=4)

print(f"Removed {len(keys_to_remove)} medium profit products.")
