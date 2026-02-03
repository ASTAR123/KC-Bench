from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from tau2.domains.personalAssistant.utils import PERSONALASSISTANT_DB_PATH
from tau2.environment.db import DB

class PhoneNumber(BaseModel):
    """Represents a phone number with default flag."""
    
    number: str = Field(description="Phone number string")
    is_default: bool = Field(
        default=False,
        description="Whether this is the default phone number for the contact"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description for this phone number (e.g., 'mobile', 'work')"
    )


class EmailAddress(BaseModel):
    """Represents an email address with default flag."""
    
    address: str = Field(description="Email address string")
    is_default: bool = Field(
        default=False,
        description="Whether this is the default email address for the contact"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description for this email address (e.g., 'personal', 'work')"
    )


class ContactDescription(BaseModel):
    """Represents an additional description for a contact."""
    
    text: str = Field(description="Description text")


class ContactHistory(BaseModel):
    """Represents a historical interaction with a contact."""
    
    date: str = Field(description="Date of the interaction in YYYY-MM-DD format")
    action: str = Field(description="Type of action: 'made a call' or 'sent an email'")
    target: str = Field(description="Name of the contact involved")
    notes: str = Field(description="Additional notes about the interaction")


class Contact(BaseModel):
    """Represents a contact with their information."""
    
    name: str = Field(description="Contact's full name (required)")
    phone_numbers: List[PhoneNumber] = Field(description="List of phone numbers (at least one required)")
    email: List[EmailAddress] = Field(default_factory=list,description="List of email addresses (optional)")
    description: str = Field(description="Additional description for the contact (optional)")

    class Config:
        validate_assignment = True

class PersonalAssistantDB(DB):
    """Database for the Personal Assistant domain."""
    
    contacts: Dict[str, Contact] = Field(
        default_factory=dict,
        description="Dictionary of contacts indexed by contact name"
    )
    contact_history: List[ContactHistory] = Field(
        default_factory=list,
        description="Historical record of interactions with contacts"
    )

def get_db():
    return PersonalAssistantDB.load(PERSONALASSISTANT_DB_PATH)


if __name__ == "__main__":
    db = get_db()
    print(db.get_statistics())