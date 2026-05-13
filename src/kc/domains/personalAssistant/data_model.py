"""Data model for the personal assistant domain."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from kc.environment.db import DB
from kc.domains.personalAssistant.utils import PERSONALASSISTANT_DB_PATH


class PersonalAssistantDB(DB):
    """Database for the personal assistant domain."""

    contacts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Personal assistant contacts indexed by contact name."
    )

    contact_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of personal assistant interactions."
    )

    def get_statistics(self):
        """Get database statistics."""
        return {
            "num_contacts": len(self.contacts),
            "num_contact_history": len(self.contact_history),
        }


def get_db():
    return PersonalAssistantDB.load(PERSONALASSISTANT_DB_PATH)


if __name__ == "__main__":
    db = get_db()
    print(db.get_statistics())