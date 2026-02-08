"""Toolkit for the personal assistant domain."""

import json
from typing import List, Optional

from tau2.domains.personalAssistant.data_model import (
    Contact,
    PersonalAssistantDB,
)
from tau2.domains.personalAssistant.utils import PERSONALASSISTANT_DB_PATH
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool

class PersonalAssistantTools(ToolKitBase):
    """All the tools for the personal assistant domain."""

    db: PersonalAssistantDB

    def __init__(self, db: PersonalAssistantDB) -> None:
        super().__init__(db)
    
    def _find_contact_by_name(self, name: str) -> List[Contact]:
        """Find contacts by full name or partial name match (case-insensitive).
        
        Args:
            name: Full name or partial name to search for.
            
        Returns:
            List of matching contacts.
        """
        name = name.lower()
        results = []
        for contact in self.db.contacts.values():
            if name in contact.name.lower():
                results.append(contact)
        return results
    
    def _find_contact_by_phone(self, phone_number: str) -> Contact:
        """Find contact by phone number.
        
        Args:
            phone_number: The phone number to search for.
            
        Returns:
            The contact.
            
        Raises:
            ValueError: If no contact is found with the phone number.
        """
        for contact in self.db.contacts.values():
            for phone in contact.phone_numbers:
                if phone.number == phone_number:
                    return contact
        raise ValueError(f"No contact found with phone number: {phone_number}")


    def _find_contact_by_email(self, email_address: str) -> Contact:
        """Find contact by email address.
        
        Args:
            email_address: The email address to search for.
            
        Returns:
            The contact.
            
        Raises:
            ValueError: If no contact is found with the email address.
        """
        for contact in self.db.contacts.values():
            for email in contact.email:
                if email.address == email_address:
                    return contact
        raise ValueError(f"No contact found with email address: {email_address}")

    @is_tool(ToolType.READ)
    def find_contact_by_name(self, name: str) -> str:
        """Find contacts by full name (preferred) or partial name (case-insensitive).
        
        Args:
            name: Full name or partial name to search for.
            
        Returns:
            str: JSON string of matching contacts with their phone numbers and emails.
        """
        results = self._find_contact_by_name(name)
        if not results:
            raise ValueError(f"No contacts found matching '{name}'")
        
        contacts_info = []
        for contact in results:
            phones = [p.number for p in contact.phone_numbers]
            emails = [e.address for e in contact.email]
            contacts_info.append({
                "name": contact.name,
                "phones": phones,
                "emails": emails,
                "description": contact.description
            })
        
        return json.dumps(contacts_info, indent=2)

    @is_tool(ToolType.READ)
    def list_all_contacts(self) -> str:
        """List all contacts in the contact list.
        
        Returns:
            str: A JSON string of contact names and basic info.
        """
        contacts_summary = {}
        for name, contact in self.db.contacts.items():
            default_phone = next((p.number for p in contact.phone_numbers if p.is_default), 
                               contact.phone_numbers[0].number if contact.phone_numbers else "No phone")
            default_email = next((e.address for e in contact.email if e.is_default), 
                               contact.email[0].address if contact.email else "No email")
            
            contacts_summary[name] = {
                "default_phone": default_phone,
                "default_email": default_email,
                "description": contact.description
            }
        return json.dumps(contacts_summary, indent=2)

    @is_tool(ToolType.WRITE)
    def make_call(self, identifier: str) -> str:
        """Make a call to a contact.
        
        Args:
            identifier: A phone number.
            
        Returns:
            str: Confirmation message of the call.
            
        Raises:
            ValueError: If phone number not in contact list.
        """

        contact = self._find_contact_by_phone(identifier)
        
        phone_desc = ""
        for phone in contact.phone_numbers:
            if phone.number == identifier:
                if phone.description:
                    phone_desc = f" ({phone.description})"
                break
        
        return f"Calling {contact.name} at {identifier}{phone_desc}..."
    
    @is_tool(ToolType.WRITE)
    def send_message(self, identifier: str) -> str:
        """Send a text message to a contact.
        
        Args:
            identifier: A phone number.
            
        Returns:
            str: Confirmation message of the sent message.
            
        Raises:
            ValueError: If phone number not in contact list.
        """
        
        contact = self._find_contact_by_phone(identifier)
        
        phone_desc = ""
        for phone in contact.phone_numbers:
            if phone.number == identifier:
                if phone.description:
                    phone_desc = f" ({phone.description})"
                break
        
        return f"Sending a message to {contact.name} at {identifier}{phone_desc}..."

    @is_tool(ToolType.WRITE)
    def send_email(self, identifier: str, subject: str) -> str:
        """Send an email to a contact.
        
        Args:
            identifier: An email address.
            subject: Email subject.
            
        Returns:
            str: Confirmation message of the email.
            
        Raises:
            ValueError: If email address not in contact list.
        """  
        contact = self._find_contact_by_email(identifier)
        
        email_desc = ""
        for email in contact.email:
                if email.description:
                    email_desc = f" ({email.description})"
                break
        
        return f"Email sent to {contact.name} at {identifier}{email_desc}. Subject: {subject}"

    @is_tool(ToolType.READ)
    def search_contact_history(self, keyword: str, search_in_notes: bool = True, 
                      search_in_action: bool = True, search_in_target: bool = True) -> str:
        """Search historical records by keyword with customizable search fields. To search with name as the keyword, full name is preferred.
        
        Args:
            keyword: Keyword to search for.
            search_in_notes: Search in notes field (default: True).
            search_in_action: Search in action field (default: True).
            search_in_target: Search in target field (default: True).
            
        Returns:
            str: JSON string of matching historical interactions.
            
        Raises:
            ValueError: If no matching records found.
        """
        keyword_lower = keyword.lower()
        results = []
        
        for record in self.db.contact_history:
            match = False
            
            if search_in_notes and keyword_lower in record.notes.lower():
                match = True
            elif search_in_action and keyword_lower in record.action.lower():
                match = True
            elif search_in_target and keyword_lower in record.target.lower():
                match = True
            
            if match:
                results.append({
                    "date": record.date,
                    "action": record.action,
                    "target": record.target,
                    "notes": record.notes
                })
        
        if not results:
            raise ValueError(f"No historical records found containing keyword: '{keyword}'")
        
        return json.dumps(results, indent=2)

    @is_tool(ToolType.GENERIC)
    def calculate(self, expression: str) -> str:
        """
        Calculate the result of a mathematical expression.

        Args:
            expression: The mathematical expression to calculate, such as '2 + 2'. The expression can contain numbers, operators (+, -, *, /), parentheses, and spaces.

        Returns:
            The result of the mathematical expression.

        Raises:
            ValueError: If the expression is invalid.
        """
        if not all(char in "0123456789+-*/(). " for char in expression):
            raise ValueError("Invalid characters in expression")
        return str(round(float(eval(expression, {"__builtins__": None}, {})), 2))
    
    # @is_tool(ToolType.THINK)
    # def think(self, thought: str) -> str:
    #     """
    #     Use the tool to think about something.
    #     It will not obtain new information or change the database, but just append the thought to the log.
    #     Use it when complex reasoning or some cache memory is needed.

    #     Args:
    #         thought: A thought to think about.

    #     Returns:
    #         Empty string
    #     """
    #     return ""

if __name__ == "__main__":
    from tau2.domains.personalAssistant.utils import PERSONALASSISTANT_DB_PATH

    personalAssistant = PersonalAssistantTools(PersonalAssistantDB.load(PERSONALASSISTANT_DB_PATH))
    print(personalAssistant.get_statistics())