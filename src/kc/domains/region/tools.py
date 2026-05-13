import json
from typing import Any, Dict, List

from kc.domains.region.data_model import (
    RegionBenchmarkDB,
)
from kc.environment.toolkit import ToolKitBase, ToolType, is_tool


class RegionTools(ToolKitBase):
    """Tools for the region/knowledge-conflict domain (geographic entity fact-checking)."""

    db: RegionBenchmarkDB

    def __init__(self, db: RegionBenchmarkDB) -> None:
        super().__init__(db)

    def _get_entities_by_value(self, value: str, relation: str = None) -> List[str]:
        """Find entities that define this value as their ground truth."""
        matches = []
        search_val = str(value).lower().strip()
        for entity, info in self.db.entities.items():
            true_val = str(info.true_value).lower().strip()
            if true_val == search_val:
                if relation and info.relation != relation:
                    continue
                matches.append(entity)
        return matches

    @is_tool(ToolType.READ)
    def calculate_shipping(self, origin_city: str) -> Dict[str, Any]:
        """Calculate shipping costs based on the origin city. 
        Verifies if the city is a known location in our database.

        Args:
            origin_city: The city where the shipment originates.

        Returns:
            Dict: Shipping cost details.
        
        Raises:
            ValueError: If the city is empty or not found in the database.
        """
        if not origin_city:
            raise ValueError("Origin city cannot be empty")

        # Check DB for context
        associated_entities = self._get_entities_by_value(origin_city, "P131")
        if not associated_entities:
             raise ValueError(f"Origin city '{origin_city}' not found in known locations.")

        # Base cost logic (mock)
        base_cost = 15.00
        
        return {
            "status": "success",
            "cost": f"{base_cost:.2f} USD",
            "origin": origin_city,
            "known_landmarks": associated_entities
        }

    @is_tool(ToolType.READ)
    def book_flight_ticket(self, destination_city: str) -> Dict[str, Any]:
        """Search for flight tickets to a specific destination.

        Args:
            destination_city: The city to fly to.

        Returns:
            Dict: Flight details.

        Raises:
            ValueError: If the destination is invalid or not found.
        """
        if len(destination_city) < 2:
            raise ValueError("Invalid city name")

        associated_entities = self._get_entities_by_value(destination_city, "P131")
        if not associated_entities:
             raise ValueError(f"Destination '{destination_city}' not found in known locations.")

        return {
            "status": "available",
            "flight_number": "UA" + str(len(destination_city) * 123),
            "destination": destination_city,
            "attractions": associated_entities
        }

    @is_tool(ToolType.READ)
    def get_current_weather(self, location: str) -> Dict[str, Any]:
        """Get current weather conditions for a specific location.

        Args:
            location: The city or region to check weather for.

        Returns:
            Dict: Weather details.

        Raises:
            ValueError: If the location is invalid.
        """
        if not location:
            raise ValueError("Location cannot be empty")

        # Determine weather based on location length (deterministic mock)
        temp = 20 + (len(location) % 15)
        condition = "Sunny" if len(location) % 2 == 0 else "Cloudy"
        
        return {
            "status": "success",
            "temperature": f"{temp}C",
            "condition": condition,
            "location": location
        }

    @is_tool(ToolType.READ)
    def check_visa_requirements(self, country_of_origin: str) -> Dict[str, Any]:
        """Check visa requirements based on the applicant's country or place of origin.

        Args:
            country_of_origin: The birth country or place of the applicant.

        Returns:
            Dict: Visa info.

        Raises:
            ValueError: If the country is not found.
        """
        if not country_of_origin:
            raise ValueError("Country cannot be empty")

        associated_people = self._get_entities_by_value(country_of_origin, "P19")
        if not associated_people:
             raise ValueError(f"Country '{country_of_origin}' not found in records.")
        
        return {
            "status": "info",
            "visa_required": True,
            "country": country_of_origin,
            "notable_natives": associated_people
        }

    @is_tool(ToolType.READ)
    def search_historical_records(self, birth_place: str) -> Dict[str, Any]:
        """Search for historical records by location.

        Args:
            birth_place: The location where the person was born.

        Returns:
             Dict: Record search results.

        Raises:
            ValueError: If the birth place is not found.
        """
        if not birth_place:
            raise ValueError("Birth place cannot be empty")

        associated_people = self._get_entities_by_value(birth_place, "P19")
        if not associated_people:
             raise ValueError(f"No records found for birth place '{birth_place}'.")

        count = 100 + len(associated_people) * 50
        
        return {
            "status": "found",
            "record_count": count,
            "location": birth_place,
            "related_figures": associated_people
        }

    @is_tool(ToolType.READ)
    def find_embassy_contact(self, country: str) -> Dict[str, Any]:
        """Find contact information for an embassy in a specific country.

        Args:
            country: The name of the country.

        Returns:
             Dict: Embassy contact info.

        Raises:
            ValueError: If the country is not found.
        """
        if not country:
            raise ValueError("Country name cannot be empty")

        entities = self._get_entities_by_value(country, "P17")
        if not entities:
            raise ValueError(f"Country '{country}' not recognized.")

        # Deterministic phone gen
        phone = f"+1-555-{''.join(str(ord(c)) for c in country[:3])}"
        
        return {
            "status": "success",
            "contact_number": phone[:12], # limit length
            "country": country
        }

    @is_tool(ToolType.READ)
    def get_exchange_rate(self, target_currency_country: str) -> Dict[str, Any]:
        """Get exchange rate for a country's main currency.

        Args:
            target_currency_country: The country whose currency is being looked up.

        Returns:
             Dict: Exchange rate info.

        Raises:
            ValueError: If the country is not found.
        """
        if not target_currency_country:
             raise ValueError("Target country cannot be empty")

        entities = self._get_entities_by_value(target_currency_country, "P17")
        if not entities:
             raise ValueError(f"Currency info for '{target_currency_country}' not found.")

        # Mock rate
        rate = 1.0 + (len(target_currency_country) / 10.0)
        
        return {
            "status": "success",
            "rate": round(rate, 2),
            "target_country": target_currency_country
        }

    @is_tool(ToolType.READ)
    def check_import_tariffs(self, origin_country: str) -> Dict[str, Any]:
        """Calculate import tariffs based on product origin.

        Args:
            origin_country: The country where the product originated.

        Returns:
             Dict: Tariff info.
        
        Raises:
            ValueError: If the country is not found.
        """
        if not origin_country:
             raise ValueError("Origin country cannot be empty")

        products = self._get_entities_by_value(origin_country, "P495")
        if not products:
             raise ValueError(f"No tariff info found for origin '{origin_country}'.")
        
        return {
            "status": "success",
            "tariff_rate": "5%",
            "origin": origin_country,
            "common_exports": products
        }

    @is_tool(ToolType.READ)
    def verify_citizenship_privileges(self, citizenship_country: str) -> Dict[str, Any]:
        """Verify travel privileges usually granted to citizens of a specific country.

        Args:
            citizenship_country: The country of citizenship.

        Returns:
             Dict: Privilege info.

        Raises:
            ValueError: If the country is not found.
        """
        if not citizenship_country:
             raise ValueError("Citizenship country cannot be empty")

        citizens = self._get_entities_by_value(citizenship_country, "P27")
        if not citizens:
             raise ValueError(f"Citizenship info for '{citizenship_country}' not found.")
        
        return {
            "status": "success",
            "visa_free_access_count": 140 + len(citizens),
            "citizenship": citizenship_country,
            "verified_citizens": citizens
        }
