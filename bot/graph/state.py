from typing import Literal, TypedDict


# ════════════════════════════════════════════════════════════
# PRODUCT SCHEMAS (lightweight for graph state)
# ════════════════════════════════════════════════════════════
class ProductOption(TypedDict):
    """Product option for the chat state."""

    id: str
    name: str
    price: float


class ProductOptionGroup(TypedDict):
    """Product option group for the chat state."""

    id: str
    name: str
    is_required: bool
    options: list[ProductOption]


class ProductVariant(TypedDict):
    """Product variant for the chat state."""

    id: str
    name: str
    price: float


class Product(TypedDict, total=False):
    """Product for the chat state (lightweight, no DB dependencies)."""

    id: str
    name: str
    description: str | None
    price: float


class OrderItem(TypedDict, total=False):
    """Item in the order."""

    product: Product
    variant: ProductVariant
    selected_options: list[ProductOption]
    quantity: int


# ════════════════════════════════════════════════════════════
# CLIENT & STATE
# ════════════════════════════════════════════════════════════
class ClientData(TypedDict, total=False):
    """Data of the client (all fields optional initially)."""

    name: str
    phone_number: str
    email: str
    address: str


Intent = Literal["INITIAL", "ORDER", "INFORMATION", "OTHER"]
CurrentStep = Literal[
    "IDLE",
    "INITIAL_MESSAGE",
    "SELECTING_PRODUCT",
    "CONFIRMING_PRODUCT",
    "ASKING_FOR_VARIANT",
    "SELECTING_VARIANT",
    "ASKING_FOR_OPTIONS",
    "SELECTING_OPTION",
    "ADDING_TO_CART",
    "CHECKOUT",
]


class ChatState(TypedDict, total=False):
    """State of the chat."""

    # Client info (gathered during conversation)
    client_data: ClientData

    user_id: str

    # Products found via semantic search
    search_results: list[Product]

    variants_results: list[ProductVariant]

    # Order items
    order_items: list[OrderItem]

    current_variant: ProductVariant | None

    # Current context
    current_product: Product | None  # Product being discussed

    # Current step
    current_step: CurrentStep = "IDLE"

    # Intent of the user
    intent: Intent

    # Messages
    user_message: str
    response: str | None
