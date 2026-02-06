"""Data model for the conflict benchmark domain."""

import json
from typing import Dict, Any

from pydantic import BaseModel, Field
from tau2.environment.db import DB
from tau2.domains.knowledge_conflict.utils import KNOWLEDGE_CONFLICT_DB_PATH


class ConflictEntity(BaseModel):
    """Represents an entity in the conflict benchmark database."""
    true_value: str = Field(description="The ground truth value for the entity.")
    relation: str = Field(description="The relation ID (e.g. P131) connecting the entity to the value.")


class ConflictBenchmarkDB(DB):
    """Database containing the ground truth for conflict benchmark entities."""
    entities: Dict[str, ConflictEntity] = Field(
        default_factory=dict, 
        description="Dictionary of entities indexed by their name."
    )

    def get_statistics(self) -> Dict[str, Any]:
        """Get the statistics of the database."""
        return {
            "num_entities": len(self.entities)
        }


def get_db():
    return ConflictBenchmarkDB.load(KNOWLEDGE_CONFLICT_DB_PATH)


if __name__ == "__main__":
    db = get_db()
    print(db.get_statistics())
