import sys
import os
sys.path.append("/mnt/shared-storage-user/lvyaxing/Agent_Honesty/tau2-bench/src")

from kc.domains.deception.tools import DeceptionTools
from kc.domains.deception.data_model import FlightDB
from kc.domains.deception.utils import Deception_DB_PATH

db = FlightDB.load(Deception_DB_PATH)
tools = DeceptionTools(db)

print("Testing 'wireless headset microphone' under 300:")
results = tools.search_products(query="wireless headset microphone", max_price=300, category="audio", in_stock_only=True)
for r in results:
    print(f"- {r['name']} (${r['price']})")

