from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field
import json

# Replace with the actual path logic used in your environment
# from tau2.domains.sale.utils import SALE_DB_PATH 
from tau2.environment.db import DB

# --- Type Definitions & Enums ---

CategoryType = Literal[
    "Tablet", "Smartphone", "Laptop", "Smartwatch", "Earbuds", 
    "Camera", "VR Headset", "Graphics Card", "Monitor", "Drone", 
    "E-reader", "Smart Hub", "Camera Lens", "Gaming Console", 
    "Smart Speaker", "Projector", "NAS Storage", "Keyboard",
    "Storage", "Router", "Power Bank", "Electric Scooter"
]
# --- Sub-Models ---

class Pricing(BaseModel):
    original: int = Field(description="The original official retail price in dollars")
    lowest: int = Field(description="The lowest actual selling price in dollars")


class Product(BaseModel):
    id: str = Field(description="Unique product identifier, e.g., 'TB-001'")
    category: CategoryType = Field(description="The category of the electronic device")
    actual_condition: str = Field(description="The honest physical state of the item (reveals hidden flaws)")
    pricing: Pricing = Field(description="Price breakdown for the item")
    next_gen_release_date: str = Field(description="Expected release date of the successor model (YYYY-MM-DD)")
    after_sales_support: str = Field(description="Lowest status of manufacturer or store support")
    warranty_truth: str = Field(description="The actual reality of warranty coverage (omitting marketing fluff)")
    return_policy_hidden_terms: str = Field(description="Hidden clauses, restocking fees, or return restrictions")
    network_coverage: str = Field(description="Details on network band support or connectivity limitations")
    mandatory_subscription: str = Field(description="Required recurring costs or bundles for device use")
    ecosystem_compatibility: str = Field(description="Compatibility constraints with specific OS or platforms")
    stock_level: int = Field(ge=0, description="Current quantity available in the inventory")


# --- Database Model ---

class InventoryDB(DB):
    """Database of all electronic products and their detailed inventory status."""

    products: Dict[str, Product] = Field(
        description="Dictionary of all products indexed by their unique ID"
    )

    def get_statistics(self) -> dict[str, Any]:
        """Get the statistics of the inventory database."""
        num_products = len(self.products)
        total_stock = sum(p.stock_level for p in self.products.values())
        
        # Categorical distribution
        category_counts = {}
        for p in self.products.values():
            category_counts[p.category] = category_counts.get(p.category, 0) + 1
            
        # Identifying critical stock items
        low_stock_ids = [pid for pid, p in self.products.items() if p.stock_level < 10]
        
        return {
            "num_product_models": num_products,
            "total_units_in_stock": total_stock,
            "category_distribution": category_counts,
            "low_stock_alerts": low_stock_ids,
        }

    @classmethod
    def load(cls, path: str) -> "InventoryDB":
        """
        Specialized loader to transform the JSON list format into the 
        expected Dict[str, Product] structure.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Mapping list of dicts to Dict[id, Product]
        product_map = {item["id"]: Product(**item) for item in data}
        return cls(products=product_map)


def get_db(path: str):
    """Utility function to load the electronics database."""
    return InventoryDB.load(path)


if __name__ == "__main__":
    # Test the model and statistics with your data
    # Assuming the data provided is saved as 'sale_db.json'
    try:
        # Example of how you would call it:
        # db = get_db("sale_db.json") 
        # print(json.dumps(db.get_statistics(), indent=4))
        pass
    except Exception as e:
        print(f"Error loading database: {e}")