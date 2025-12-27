from datetime import datetime, timezone
from typing import TYPE_CHECKING

from beanie import Document, Indexed, Link
from pydantic import Field

if TYPE_CHECKING:
    from modules.users.models import User


def utc_now() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(timezone.utc)


class Product(Document):
    """Product model."""

    user_id: Link["User"]  # Product owner
    name: Indexed(str)  # type: ignore
    description: str | None = None
    price: float
    image: str | None = None  # MinIO file_key
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "products"


class ProductVariant(Document):
    """Product variant (e.g., size, color)."""

    product_id: Link[Product]
    name: str
    price: float
    image: str | None = None  # MinIO file_key
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "product_variants"


class ProductOptionGroup(Document):
    """Product option group (e.g., Extras, Ingredients)."""

    product_id: Link[Product]
    name: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "product_option_groups"


class ProductOption(Document):
    """Product option within a group (e.g., Extra cheese)."""

    option_group_id: Link[ProductOptionGroup]
    name: str
    price: float
    image: str | None = None
    is_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "product_options"
