import json

DB_PATH = "/mnt/shared-storage-user/lvyaxing/Agent_Honesty/tau2-bench/data/KC-Benchdomains/deception/db.json"

with open(DB_PATH, "r") as f:
    db = json.load(f)

products = db.get("products", {})
print(f"Total products: {len(products)}")
for pid, p in products.items():
    print(f"- {pid}: {p['name']} (${p['price']}) - Margin: {p.get('profit_margin', 'None')} - Defects: {len(p.get('active_defect_reports', []))}")
