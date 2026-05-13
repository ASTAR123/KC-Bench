"""Toolkit for the conflict benchmark domain personal assistant."""
import json
from typing import Any, Dict, List

from kc.domains.personalAssistant.data_model import (
    PersonalAssistantDB,
)
from kc.environment.toolkit import ToolKitBase, ToolType, is_tool


class PersonalAssistantTools(ToolKitBase):
    """Tools for the personal assistant domain (contacts, calls, messages)."""

    db: PersonalAssistantDB

    def __init__(self, db: PersonalAssistantDB) -> None:
        super().__init__(db)

    def _find_contact_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Find contacts by full name or partial name match (case-insensitive).
        
        Args:
            name: Full name or partial name to search for.
            
        Returns:
            List of matching contacts.
        """
        name_lower = name.lower()
        results = []
        for contact in self.db.contacts.values():
            contact_name = str(contact.get("name", ""))
            if name_lower in contact_name.lower():
                results.append(contact)
        return results

    def _find_contact_by_phone(self, phone_number: str) -> Dict[str, Any]:
        """Find contact by phone number.
        
        Args:
            phone_number: The phone number to search for.
            
        Returns:
            The contact.
            
        Raises:
            ValueError: If no contact is found with the phone number.
        """
        for contact in self.db.contacts.values():
            for phone in contact.get("phone_numbers", []):
                if phone.get("number") == phone_number:
                    return contact
        raise ValueError(f"No contact found with phone number: {phone_number}")

    def _find_contact_by_email(self, email_address: str) -> Dict[str, Any]:
        """Find contact by email address.
        
        Args:
            email_address: The email address to search for.
            
        Returns:
            The contact.
            
        Raises:
            ValueError: If no contact is found with the email address.
        """
        for contact in self.db.contacts.values():
            for email in contact.get("email", []):
                if email.get("address") == email_address:
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
            phones_info = []
            for phone in contact.get("phone_numbers", []):
                phones_info.append({
                    "number": phone.get("number"),
                    "is_default": phone.get("is_default", False),
                    "remark": phone.get("remark") or "",
                })
            emails_info = []
            for email in contact.get("email", []):
                emails_info.append({
                    "address": email.get("address"),
                    "is_default": email.get("is_default", False),
                    "remark": email.get("remark") or "",
                })
            contacts_info.append({
                "name": contact.get("name"),
                "phones": phones_info,
                "emails": emails_info,
                "remark": contact.get("remark", ""),
            })
        return json.dumps(contacts_info, indent=2)

    @is_tool(ToolType.READ)
    def list_all_contacts(self) -> str:
        """List all names and remarks of contacts in the contact list.
        
        Returns:
            str: A JSON string of contact names and remarks.
        """
        contacts_summary = {}
        for name, contact in self.db.contacts.items():
            contacts_summary[name] = {"remark": contact.get("remark", "")}
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
        for phone in contact.get("phone_numbers", []):
            if phone.get("number") == identifier and phone.get("remark"):
                phone_desc = f" ({phone.get('remark')})"
                break
        return f"Calling {contact.get('name')} at {identifier}{phone_desc}..."

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
        for phone in contact.get("phone_numbers", []):
            if phone.get("number") == identifier and phone.get("remark"):
                phone_desc = f" ({phone.get('remark')})"
                break
        return f"Sending a message to {contact.get('name')} at {identifier}{phone_desc}..."

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
        for email in contact.get("email", []):
            if email.get("address") == identifier and email.get("remark"):
                email_desc = f" ({email.get('remark')})"
                break
        return f"Email sent to {contact.get('name')} at {identifier}{email_desc}. Subject: {subject}"

    @is_tool(ToolType.READ)
    def search_contact_history(
        self,
        keyword: str,
        search_in_notes: bool = True,
        search_in_action: bool = True,
        search_in_target: bool = True,
    ) -> str:
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
            notes = str(record.get("notes", "")).lower()
            action = str(record.get("action", "")).lower()
            target = str(record.get("target", "")).lower()
            match = (
                (search_in_notes and keyword_lower in notes)
                or (search_in_action and keyword_lower in action)
                or (search_in_target and keyword_lower in target)
            )
            if match:
                results.append(
                    {
                        "date": record.get("date"),
                        "action": record.get("action"),
                        "target": record.get("target"),
                        "notes": record.get("notes"),
                    }
                )

        if not results:
            raise ValueError(f"No historical records found containing keyword: '{keyword}'")

        return json.dumps(results, indent=2)
