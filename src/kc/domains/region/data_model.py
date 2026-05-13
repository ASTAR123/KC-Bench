"""Data model for the conflict benchmark domain."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field
from kc.environment.db import DB
from kc.domains.region.utils import REGION_DB_PATH


class ConflictEntity(BaseModel):
    """Represents an entity in the conflict benchmark database."""
    true_value: str = Field(description="The ground truth value for the entity.")
    relation: str = Field(
        description="The relation ID (e.g. P131) connecting the entity to the value."
    )


class RegionBenchmarkDB(DB):
    """Database containing the ground truth for conflict benchmark entities."""

    entities: Dict[str, ConflictEntity] = Field(
        default_factory=dict,
        description="Dictionary of entities indexed by their name.",
    )

    def get_statistics(self) -> Dict[str, Any]:
        """Get the statistics of the database."""
        return {
            "num_entities": len(self.entities),
        }


def get_db():
    return RegionBenchmarkDB.load(REGION_DB_PATH)


if __name__ == "__main__":
    db = get_db()
    print(db.get_statistics())