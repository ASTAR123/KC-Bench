"""Data model for the retail benchmark domain."""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field
from kc.environment.db import DB
from kc.domains.retail.utils import RETAIL_DB_PATH


class Variant(BaseModel):
    item_id: str = Field(description="Unique identifier for the variant")
    options: Dict[str, str] = Field(
        description="Dictionary of option names to values"
    )
    available: bool = Field(description="Whether this variant is currently in stock")
    price: float = Field(description="Price of this variant")


class Product(BaseModel):
    name: str = Field(description="Name of the product")
    product_id: str = Field(description="Unique identifier for the product")
    variants: Dict[str, Variant] = Field(
        description="Dictionary of variants indexed by variant ID"
    )


class UserName(BaseModel):
    first_name: str = Field(description="User's first name")
    last_name: str = Field(description="User's last name")


class UserAddress(BaseModel):
    address1: str = Field(description="Primary address line")
    address2: str = Field(description="Secondary address line")
    city: str = Field(description="City name")
    country: str = Field(description="Country name")
    state: str = Field(description="State or province name")
    zip: str = Field(description="Postal code")


class PaymentMethodBase(BaseModel):
    source: str = Field(description="Type of payment method")
    id: str = Field(description="Unique identifier for the payment method")


class CreditCard(PaymentMethodBase):
    source: Literal["credit_card"] = Field(
        description="Indicates this is a credit card payment method"
    )
    brand: str = Field(description="Credit card brand")
    last_four: str = Field(description="Last four digits of the credit card")


class Paypal(PaymentMethodBase):
    source: Literal["paypal"] = Field(
        description="Indicates this is a paypal payment method"
    )


class GiftCard(PaymentMethodBase):
    source: Literal["gift_card"] = Field(
        description="Indicates this is a gift card payment method"
    )
    balance: float = Field(description="Gift card value amount")
    id: str = Field(description="Unique identifier for the gift card")


PaymentMethod = Union[CreditCard, GiftCard, Paypal]


class User(BaseModel):
    user_id: str = Field(description="Unique identifier for the user")
    name: UserName = Field(description="User's full name")
    address: UserAddress = Field(description="User's primary address")
    email: str = Field(description="User's email address")
    payment_methods: Dict[str, PaymentMethod] = Field(
        description="Dictionary of payment methods indexed by payment method ID"
    )
    orders: List[str] = Field(description="List of order IDs associated with this user")


class OrderFullfilment(BaseModel):
    tracking_id: List[str] = Field(
        description="List of tracking IDs for shipments"
    )
    item_ids: List[str] = Field(
        description="List of item IDs included in this fulfillment"
    )


class OrderItem(BaseModel):
    name: str = Field(description="Name of the product")
    product_id: str = Field(description="ID of the product")
    item_id: str = Field(description="ID of the specific variant")
    price: float = Field(description="Price of the item at time of purchase")
    options: Dict[str, str] = Field(
        description="Options selected for this item"
    )


OrderPaymentType = Literal["payment", "refund"]


class OrderPayment(BaseModel):
    transaction_type: OrderPaymentType = Field(
        description="Type of transaction (payment or refund)"
    )
    amount: float = Field(description="Amount of the transaction")
    payment_method_id: str = Field(
        description="ID of the payment method used"
    )


OrderStatus = Literal[
    "processed",
    "pending",
    "pending (item modified)",
    "delivered",
    "cancelled",
    "exchange requested",
    "return requested",
]


CancelReason = Literal[
    "no longer needed",
    "ordered by mistake",
]


class Order(BaseModel):
    order_id: str = Field(description="Unique identifier for the order")
    user_id: str = Field(description="Unique identifier for the user")
    address: UserAddress = Field(description="Address of the user")

    items: List[OrderItem] = Field(
        description="Items in the order"
    )

    status: OrderStatus = Field(
        description="Status of the order"
    )

    fulfillments: List[OrderFullfilment] = Field(
        description="Fulfillments of the order"
    )

    payment_history: List[OrderPayment] = Field(
        description="Payments of the order"
    )

    cancel_reason: Optional[CancelReason] = Field(
        description="Reason for cancelling the order",
        default=None,
    )

    exchange_items: Optional[List[str]] = Field(
        description="Items to be exchanged",
        default=None,
    )

    exchange_new_items: Optional[List[str]] = Field(
        description="Items exchanged for",
        default=None,
    )

    exchange_payment_method_id: Optional[str] = Field(
        description="Payment method ID for the exchange",
        default=None,
    )

    exchange_price_difference: Optional[float] = Field(
        description="Price difference for the exchange",
        default=None,
    )

    return_items: Optional[List[str]] = Field(
        description="Items to be returned",
        default=None,
    )

    return_payment_method_id: Optional[str] = Field(
        description="Payment method ID for the return",
        default=None,
    )


class RetailBenchmarkDB(DB):
    """Database containing retail benchmark data."""

    products: Dict[str, Product] = Field(
        default_factory=dict,
        description="Retail products indexed by product ID.",
    )

    users: Dict[str, User] = Field(
        default_factory=dict,
        description="Retail users indexed by user ID.",
    )

    orders: Dict[str, Order] = Field(
        default_factory=dict,
        description="Retail orders indexed by order ID.",
    )

    def get_statistics(self) -> Dict[str, Any]:
        """Get the statistics of the database."""
        return {
            "num_products": len(self.products),
            "num_users": len(self.users),
            "num_orders": len(self.orders),
        }


def get_db():
    return RetailBenchmarkDB.load(RETAIL_DB_PATH)


if __name__ == "__main__":
    db = get_db()
    print(db.get_statistics())