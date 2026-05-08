"""Toolkit for the conflict benchmark domain."""

import json
from typing import Any, Dict, List

from kc.domains.knowledge_conflict.data_model import (
    GiftCard,
    ConflictBenchmarkDB,
    Order,
    OrderPayment,
    PaymentMethod,
    Product,
    User,
    UserAddress,
    Variant,
)
from kc.environment.toolkit import ToolKitBase, ToolType, is_tool

class ConflictTools(ToolKitBase):
    """Combined tools for knowledge_conflict + tbb1 + tbb2."""

    db: ConflictBenchmarkDB

    def __init__(self, db: ConflictBenchmarkDB) -> None:
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





    # Travel
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

























    # ---------------- Retail tools (from tbb1) ----------------
    def _get_order(self, order_id: str) -> Order:
        """Get the order from the database.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.

        Returns:
            The order.

        Raises:
            ValueError: If the order is not found.
        """
        if order_id not in self.db.orders:
            raise ValueError("Order not found")
        return self.db.orders[order_id]

    def _get_user(self, user_id: str) -> User:
        """Get the user from the database.

        Args:
            user_id: The user id, such as 'sara_doe_496'.

        Returns:
            The user.

        Raises:
            ValueError: If the user is not found.
        """
        if user_id not in self.db.users:
            raise ValueError("User not found")
        return self.db.users[user_id]

    def _get_product(self, product_id: str) -> Product:
        """Get the product from the database.

        Args:
            product_id: The product id, such as '6086499569'. Be careful the product id is different from the item id.

        Returns:
            The product.

        Raises:
            ValueError: If the product is not found.
        """
        if product_id not in self.db.products:
            raise ValueError("Product not found")
        return self.db.products[product_id]

    def _get_variant(self, product_id: str, variant_id: str) -> Variant:
        """Get the variant from the database.

        Args:
            product_id: The product id, such as '6086499569'. Be careful the product id is different from the item id.
            variant_id: The variant id, such as '1008292230'.

        Returns:
            The variant.

        Raises:
            ValueError: If the variant is not found.
        """
        product = self._get_product(product_id)
        if variant_id not in product.variants:
            raise ValueError("Variant not found")
        return product.variants[variant_id]

    def _get_payment_method(self, user_id: str, payment_method_id: str) -> PaymentMethod:
        """Get the payment method from the database.

        Args:
            payment_method_id: The payment method id, such as 'gift_card_0000000' or 'credit_card_0000000'.

        Returns:
            The payment method.

        Raises:
            ValueError: If the payment method is not found.
        """
        user = self._get_user(user_id)
        if payment_method_id not in user.payment_methods:
            raise ValueError("Payment method not found")
        return user.payment_methods[payment_method_id]

    def _is_pending_order(self, order: Order) -> bool:
        """Check if the order is pending. This is not a strict check, and not meant to be used for modify_items in pending orders.

        Args:
            order: The order.
        """
        return "pending" in order.status

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

    @is_tool(ToolType.WRITE)
    def cancel_pending_order(self, order_id: str, reason: str) -> Order:
        """Cancel a pending order. If the order is already processed or delivered,
        it cannot be cancelled. The agent needs to explain the cancellation detail
        and ask for explicit user confirmation (yes/no) to proceed. If the user confirms,
        the order status will be changed to 'cancelled' and the payment will be refunded.
        The refund will be added to the user's gift card balance immediately if the payment
        was made using a gift card, otherwise the refund would take 5-7 business days to process.
        The function returns the order details after the cancellation.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            reason: The reason for cancellation, which should be either 'no longer needed' or 'ordered by mistake'.

        Returns:
            Order: The order details after the cancellation.
        """
        order = self._get_order(order_id)
        if order.status != "pending":
            raise ValueError("Non-pending order cannot be cancelled")
        if reason not in {"no longer needed", "ordered by mistake"}:
            raise ValueError("Invalid reason")

        refunds = []
        for payment in order.payment_history:
            payment_id = payment.payment_method_id
            refund = OrderPayment(
                transaction_type="refund",
                amount=payment.amount,
                payment_method_id=payment_id,
            )
            refunds.append(refund)
            user = self._get_user(order.user_id)
            payment_method = self._get_payment_method(user.user_id, payment_id)
            if isinstance(payment_method, GiftCard):
                payment_method.balance += payment.amount
                payment_method.balance = round(payment_method.balance, 2)

        order.status = "cancelled"
        order.cancel_reason = reason
        order.payment_history.extend(refunds)
        return order

    @is_tool(ToolType.WRITE)
    def exchange_delivered_order_items(
        self,
        order_id: str,
        item_ids: List[str],
        new_item_ids: List[str],
        payment_method_id: str,
    ) -> Order:
        """Exchange items in a delivered order to new items of the same product type.
        For a delivered order, return or exchange can be only done once by the agent.
        The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            item_ids: The item ids to be exchanged, each such as '1008292230'. There could be duplicate items in the list.
            new_item_ids: The item ids to be exchanged for, each such as '1008292230'.
                         There could be duplicate items in the list. Each new item id should match the item id
                         in the same position and be of the same product.
            payment_method_id: The payment method id to pay or receive refund for the item price difference,
                             such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up
                             from the user or order details.

        Returns:
            Order: The order details after the exchange.

        Raises:
            ValueError: If the order is not delivered.
            ValueError: If the items to be exchanged do not exist.
            ValueError: If the new items do not exist or do not match the old items.
            ValueError: If the number of items to be exchanged does not match.
        """
        order = self._get_order(order_id)
        if order.status != "delivered":
            raise ValueError("Non-delivered order cannot be exchanged")

        all_item_ids = [item.item_id for item in order.items]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                raise ValueError(f"Number of {item_id} not found.")

        if len(item_ids) != len(new_item_ids):
            raise ValueError("The number of items to be exchanged should match.")

        diff_price = 0
        for item_id, new_item_id in zip(item_ids, new_item_ids):
            item = next((item for item in order.items if item.item_id == item_id), None)
            if item is None:
                raise ValueError(f"Item {item_id} not found")
            variant = self._get_variant(item.product_id, new_item_id)
            if not variant.available:
                raise ValueError(f"New item {new_item_id} not found or available")
            diff_price += variant.price - item.price

        diff_price = round(diff_price, 2)
        payment_method = self._get_payment_method(order.user_id, payment_method_id)
        if isinstance(payment_method, GiftCard) and payment_method.balance < diff_price:
            raise ValueError("Insufficient gift card balance to pay for the price difference")

        order.status = "exchange requested"
        order.exchange_items = sorted(item_ids)
        order.exchange_new_items = sorted(new_item_ids)
        order.exchange_payment_method_id = payment_method_id
        order.exchange_price_difference = diff_price
        return order

    @is_tool(ToolType.READ)
    def find_user_id_by_name_zip(self, first_name: str, last_name: str, zip: str) -> str:
        """Find user id by first name, last name, and zip code. If the user is not found, the function
        will return an error message. By default, find user id by email, and only call this function
        if the user is not found by email or cannot remember email.

        Args:
            first_name: The first name of the customer, such as 'John'.
            last_name: The last name of the customer, such as 'Doe'.
            zip: The zip code of the customer, such as '12345'.

        Returns:
            str: The user id if found, otherwise an error message.

        Raises:
            ValueError: If the user is not found.
        """
        for user_id, user in self.db.users.items():
            if (
                user.name.first_name.lower() == first_name.lower()
                and user.name.last_name.lower() == last_name.lower()
                and user.address.zip == zip
            ):
                return user_id
        raise ValueError("User not found")

    @is_tool(ToolType.READ)
    def find_user_id_by_email(self, email: str) -> str:
        """Find user id by email. If the user is not found, the function will return an error message.

        Args:
            email: The email of the user, such as 'something@example.com'.

        Returns:
            str: The user id if found, otherwise an error message.

        Raises:
            ValueError: If the user is not found.
        """
        for user_id, user in self.db.users.items():
            if user.email.lower() == email.lower():
                return user_id
        raise ValueError("User not found")

    @is_tool(ToolType.READ)
    def get_order_details(self, order_id: str) -> Order:
        """Get the status and details of an order.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.

        Returns:
            Order: The order details.

        Raises:
            ValueError: If the order is not found.
        """
        return self._get_order(order_id)

    @is_tool(ToolType.READ)
    def get_product_details(self, product_id: str) -> Product:
        """Get the inventory details of a product.

        Args:
            product_id: The product id, such as '6086499569'. Be careful the product id is different from the item id.

        Returns:
            Product: The product details.

        Raises:
            ValueError: If the product is not found.
        """
        return self._get_product(product_id)

    @is_tool(ToolType.READ)
    def get_user_details(self, user_id: str) -> User:
        """Get the details of a user, including their orders.

        Args:
            user_id: The user id, such as 'sara_doe_496'.

        Returns:
            User: The user details.

        Raises:
            ValueError: If the user is not found.
        """
        return self._get_user(user_id)

    @is_tool(ToolType.READ)
    def list_all_product_types(self) -> str:
        """List the name and product id of all product types.
        Each product type has a variety of different items with unique item ids and options.
        There are only 50 product types in the store.

        Returns:
            str: A JSON string mapping product names to their product IDs, sorted alphabetically by name.
        """
        product_dict = {
            product.name: product.product_id for product in self.db.products.values()
        }
        return json.dumps(product_dict, sort_keys=True)

    @is_tool(ToolType.WRITE)
    def modify_pending_order_address(
        self,
        order_id: str,
        address1: str,
        address2: str,
        city: str,
        state: str,
        country: str,
        zip: str,
    ) -> Order:
        """Modify the shipping address of a pending order. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            address1: The first line of the address, such as '123 Main St'.
            address2: The second line of the address, such as 'Apt 1' or ''.
            city: The city, such as 'San Francisco'.
            state: The state, such as 'CA'.
            country: The country, such as 'USA'.
            zip: The zip code, such as '12345'.

        Returns:
            Order: The order details after the modification.

        Raises:
            ValueError: If the order is not pending.
        """
        order = self._get_order(order_id)
        if not self._is_pending_order(order):
            raise ValueError("Non-pending order cannot be modified")
        order.address = UserAddress(
            address1=address1,
            address2=address2,
            city=city,
            state=state,
            country=country,
            zip=zip,
        )
        return order

    @is_tool(ToolType.WRITE)
    def modify_pending_order_items(
        self,
        order_id: str,
        item_ids: List[str],
        new_item_ids: List[str],
        payment_method_id: str,
    ) -> Order:
        """Modify items in a pending order to new items of the same product type. For a pending order, this function can only be called once. The agent needs to explain the exchange detail and ask for explicit user confirmation (yes/no) to proceed.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            item_ids: The item ids to be modified, each such as '1008292230'. There could be duplicate items in the list.
            new_item_ids: The item ids to be modified for, each such as '1008292230'. There could be duplicate items in the list. Each new item id should match the item id in the same position and be of the same product.
            payment_method_id: The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details.

        Returns:
            Order: The order details after the modification.

        Raises:
            ValueError: If the order is not pending.
            ValueError: If the items to be modified do not exist.
            ValueError: If the new items do not exist or do not match the old items.
            ValueError: If the number of items to be modified does not match.
        """
        order = self._get_order(order_id)
        if order.status != "pending":
            raise ValueError("Non-pending order cannot be modified")

        all_item_ids = [item.item_id for item in order.items]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                raise ValueError(f"{item_id} not found")

        if len(item_ids) != len(new_item_ids):
            raise ValueError("The number of items to be exchanged should match")

        diff_price = 0
        variant_map: dict[str, Variant] = {}
        for item_id, new_item_id in zip(item_ids, new_item_ids):
            if item_id == new_item_id:
                raise ValueError("The new item id should be different from the old item id")
            item = next((item for item in order.items if item.item_id == item_id), None)
            if item is None:
                raise ValueError(f"Item {item_id} not found")
            variant = self._get_variant(item.product_id, new_item_id)
            if not variant.available:
                raise ValueError(f"New item {new_item_id} not found or available")
            diff_price += variant.price - item.price
            variant_map[new_item_id] = variant

        payment_method = self._get_payment_method(order.user_id, payment_method_id)
        if isinstance(payment_method, GiftCard) and payment_method.balance < diff_price:
            raise ValueError("Insufficient gift card balance to pay for the new item")

        order.payment_history.append(
            OrderPayment(
                transaction_type="payment" if diff_price > 0 else "refund",
                amount=abs(diff_price),
                payment_method_id=payment_method_id,
            )
        )
        if isinstance(payment_method, GiftCard):
            payment_method.balance -= diff_price
            payment_method.balance = round(payment_method.balance, 2)

        for item_id, new_item_id in zip(item_ids, new_item_ids):
            item = next((item for item in order.items if item.item_id == item_id), None)
            if item is None:
                raise ValueError(f"Item {item_id} not found")
            variant = variant_map[new_item_id]
            item.item_id = new_item_id
            item.price = variant.price
            item.options = variant.options
        order.status = "pending (item modified)"
        return order

    @is_tool(ToolType.WRITE)
    def modify_pending_order_payment(self, order_id: str, payment_method_id: str) -> Order:
        """Modify the payment method of a pending order. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            payment_method_id: The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order details.

        Returns:
            Order: The order details after the modification.

        Raises:
            ValueError: If the order is not pending.
            ValueError: If the payment method does not exist.
            ValueError: If the payment history has more than one payment.
            ValueError: If the new payment method is the same as the current one.
        """
        order = self._get_order(order_id)
        if not self._is_pending_order(order):
            raise ValueError("Non-pending order cannot be modified")

        payment_method = self._get_payment_method(order.user_id, payment_method_id)
        if (
            len(order.payment_history) != 1
            or order.payment_history[0].transaction_type != "payment"
        ):
            raise ValueError("There should be exactly one payment for a pending order")
        if order.payment_history[0].payment_method_id == payment_method_id:
            raise ValueError("The new payment method should be different from the current one")

        amount = order.payment_history[0].amount
        if isinstance(payment_method, GiftCard) and payment_method.balance < amount:
            raise ValueError("Insufficient gift card balance to pay for the order")

        order.payment_history.extend(
            [
                OrderPayment(
                    transaction_type="payment",
                    amount=amount,
                    payment_method_id=payment_method_id,
                ),
                OrderPayment(
                    transaction_type="refund",
                    amount=amount,
                    payment_method_id=order.payment_history[0].payment_method_id,
                ),
            ]
        )

        if isinstance(payment_method, GiftCard):
            payment_method.balance -= amount
            payment_method.balance = round(payment_method.balance, 2)

        old_payment_method = self._get_payment_method(
            order.user_id, order.payment_history[0].payment_method_id
        )
        if isinstance(old_payment_method, GiftCard):
            old_payment_method.balance += amount
            old_payment_method.balance = round(old_payment_method.balance, 2)

        return order

    @is_tool(ToolType.WRITE)
    def modify_user_address(
        self,
        user_id: str,
        address1: str,
        address2: str,
        city: str,
        state: str,
        country: str,
        zip: str,
    ) -> User:
        """Modify the default address of a user. The agent needs to explain the modification detail and ask for explicit user confirmation (yes/no) to proceed.

        Args:
            user_id: The user id, such as 'sara_doe_496'.
            address1: The first line of the address, such as '123 Main St'.
            address2: The second line of the address, such as 'Apt 1' or ''.
            city: The city, such as 'San Francisco'.
            state: The state, such as 'CA'.
            country: The country, such as 'USA'.
            zip: The zip code, such as '12345'.

        Returns:
            User: The user details after the modification.

        Raises:
            ValueError: If the user is not found.
        """
        user = self._get_user(user_id)
        user.address = UserAddress(
            address1=address1,
            address2=address2,
            city=city,
            state=state,
            country=country,
            zip=zip,
        )
        return user

    @is_tool(ToolType.WRITE)
    def return_delivered_order_items(
        self,
        order_id: str,
        item_ids: List[str],
        payment_method_id: str,
    ) -> Order:
        """Return some items of a delivered order.
        The order status will be changed to 'return requested'.
        The agent needs to explain the return detail and ask for explicit user confirmation (yes/no) to proceed.
        The user will receive follow-up email for how and where to return the item.

        Args:
            order_id: The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the order id.
            item_ids: The item ids to be returned, each such as '1008292230'. There could be duplicate items in the list.
            payment_method_id: The payment method id to pay or receive refund for the item price difference, such as 'gift_card_0000000' or 'credit_card_0000000'.
                             These can be looked up from the user or order details.

        Returns:
            Order: The order details after requesting the return.

        Raises:
            ValueError: If the order is not delivered.
            ValueError: If the payment method is not the original payment method or a gift card.
            ValueError: If the items to be returned do not exist.
        """
        order = self._get_order(order_id)
        if order.status != "delivered":
            raise ValueError("Non-delivered order cannot be returned")

        user = self._get_user(order.user_id)
        payment_method = self._get_payment_method(user.user_id, payment_method_id)
        if (
            not isinstance(payment_method, GiftCard)
            and payment_method_id != order.payment_history[0].payment_method_id
        ):
            raise ValueError("Payment method should be the original payment method")

        all_item_ids = [item.item_id for item in order.items]
        for item_id in item_ids:
            if item_ids.count(item_id) > all_item_ids.count(item_id):
                raise ValueError("Some item not found")

        order.status = "return requested"
        order.return_items = sorted(item_ids)
        order.return_payment_method_id = payment_method_id
        return order



















    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> str:
        """
        Transfer the user to a human agent, with a summary of the user's issue.
        Only transfer if
         -  the user explicitly asks for a human agent
         -  given the policy and the available tools, you cannot solve the user's issue.

        Args:
            summary: A summary of the user's issue.

        Returns:
            A message indicating the user has been transferred to a human agent.
        """
        return "Transfer successful"

















































    # ---------------- Personal assistant tools (from tbb2) ----------------
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

















if __name__ == "__main__":
    from kc.domains.knowledge_conflict.utils import KNOWLEDGE_CONFLICT_DB_PATH

    print(f"Loading DB from {KNOWLEDGE_CONFLICT_DB_PATH}")
    db = ConflictBenchmarkDB.load(KNOWLEDGE_CONFLICT_DB_PATH)
    tools = ConflictTools(db)
    print("Tools initialized successfully.")
    print(tools.calculate_shipping("Paris"))
