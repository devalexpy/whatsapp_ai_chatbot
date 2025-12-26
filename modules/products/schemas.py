"""Product schemas for API validation and documentation."""

from datetime import datetime

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


# ════════════════════════════════════════════════════════════
# STORAGE / PRESIGNED URLs
# ════════════════════════════════════════════════════════════
class UploadUrlRequest(BaseModel):
    """Request to obtain a presigned upload URL."""

    content_type: str = Field(
        default="image/jpeg",
        description="MIME type of the image to upload",
        examples=["image/jpeg", "image/png", "image/webp"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {"content_type": "image/png"},
            "description": "Allowed types: image/jpeg, image/png, image/gif, image/webp",
        }
    }


class UploadUrlResponse(BaseModel):
    """Response with presigned URL for file upload."""

    upload_url: str = Field(
        description="Presigned URL to PUT the file",
        examples=["https://storage.example.com/upload?token=abc123"],
    )
    file_key: str = Field(
        description="Unique file key to confirm the upload",
        examples=["products/abc123/image.png"],
    )
    expires_in: int = Field(
        description="Time in seconds before the URL expires",
        examples=[3600],
    )
    instructions: str = Field(
        default="Use PUT with the specified Content-Type",
        description="Usage instructions",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "upload_url": "https://s3.amazonaws.com/bucket/path?X-Amz-Algorithm=...",
                "file_key": "products/507f1f77bcf86cd799439011/1703606400.png",
                "expires_in": 3600,
                "instructions": "Use PUT with the specified Content-Type",
            }
        }
    }


class ConfirmUploadRequest(BaseModel):
    """Request to confirm image upload completion."""

    file_key: str = Field(
        description="File key returned by upload-url endpoint",
        examples=["products/507f1f77bcf86cd799439011/1703606400.png"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {"file_key": "products/507f1f77bcf86cd799439011/1703606400.png"}
        }
    }


class ImageResponse(BaseModel):
    """Image information response."""

    image_url: str | None = Field(
        default=None,
        description="Public URL of the image",
        examples=["https://cdn.example.com/products/abc123/image.png"],
    )
    file_key: str | None = Field(
        default=None,
        description="File key in storage",
        examples=["products/507f1f77bcf86cd799439011/image.png"],
    )


# ════════════════════════════════════════════════════════════
# PRODUCT
# ════════════════════════════════════════════════════════════
class ProductCreate(BaseModel):
    """Data to create a new product."""

    name: str = Field(
        min_length=1,
        max_length=200,
        description="Product name",
        examples=["Classic Burger"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="Detailed product description",
        examples=[
            "Delicious burger with 100% beef patty, lettuce, tomato and special sauce"
        ],
    )
    price: float = Field(
        gt=0,
        description="Base price of the product",
        examples=[12.99],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Classic Burger",
                "description": "Delicious burger with 100% beef patty",
                "price": 12.99,
            }
        }
    }


class ProductUpdate(BaseModel):
    """Data to update a product. Only provided fields will be updated."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="New product name",
        examples=["Premium Burger"],
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
        description="New product description",
        examples=["Premium burger with select ingredients"],
    )
    price: float | None = Field(
        default=None,
        gt=0,
        description="New product price",
        examples=[15.99],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Premium Burger",
                "price": 15.99,
            }
        }
    }


class ProductResponse(BaseModel):
    """Basic product response."""

    id: PydanticObjectId = Field(description="Unique product ID")
    user_id: PydanticObjectId = Field(description="Owner user ID")
    name: str = Field(description="Product name")
    description: str | None = Field(default=None, description="Product description")
    price: float = Field(description="Base product price")
    image: str | None = Field(default=None, description="Product image URL")
    created_at: datetime = Field(description="Creation date")
    updated_at: datetime = Field(description="Last update date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "name": "Classic Burger",
                "description": "Delicious burger with 100% beef patty",
                "price": 12.99,
                "image": "https://cdn.example.com/products/507f1f77bcf86cd799439011/image.jpg",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }
    }


# ════════════════════════════════════════════════════════════
# PRODUCT VARIANT
# ════════════════════════════════════════════════════════════
class ProductVariantCreate(BaseModel):
    """Data to create a product variant (e.g., sizes, flavors)."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Variant name",
        examples=["Large", "Medium", "Small"],
    )
    price: float = Field(
        gt=0,
        description="Price for this variant",
        examples=[15.99],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Large",
                "price": 15.99,
            }
        }
    }


class ProductVariantUpdate(BaseModel):
    """Data to update a variant. Only provided fields will be updated."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New variant name",
        examples=["Extra Large"],
    )
    price: float | None = Field(
        default=None,
        gt=0,
        description="New variant price",
        examples=[18.99],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Extra Large",
                "price": 18.99,
            }
        }
    }


class ProductVariantResponse(BaseModel):
    """Product variant response."""

    id: PydanticObjectId = Field(description="Unique variant ID")
    name: str = Field(description="Variant name")
    price: float = Field(description="Variant price")
    image: str | None = Field(default=None, description="Variant image URL")
    created_at: datetime = Field(description="Creation date")
    updated_at: datetime = Field(description="Last update date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439013",
                "name": "Large",
                "price": 15.99,
                "image": "https://cdn.example.com/variants/507f1f77bcf86cd799439013/image.jpg",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }
    }


# ════════════════════════════════════════════════════════════
# PRODUCT OPTION GROUP
# ════════════════════════════════════════════════════════════
class ProductOptionGroupCreate(BaseModel):
    """Data to create an option group (e.g., Extra Toppings, Sauces)."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Option group name",
        examples=["Extra Toppings", "Sauces", "Sides"],
    )

    model_config = {"json_schema_extra": {"example": {"name": "Extra Toppings"}}}


class ProductOptionGroupUpdate(BaseModel):
    """Data to update an option group."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New group name",
        examples=["Premium Extras"],
    )

    model_config = {"json_schema_extra": {"example": {"name": "Premium Extras"}}}


# ════════════════════════════════════════════════════════════
# PRODUCT OPTION
# ════════════════════════════════════════════════════════════
class ProductOptionCreate(BaseModel):
    """Data to create an option within a group (e.g., Extra Cheese, Bacon)."""

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Option name",
        examples=["Extra Cheese", "Bacon", "Avocado"],
    )
    price: float = Field(
        ge=0,
        description="Additional price for this option (can be 0)",
        examples=[2.50],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Extra Cheese",
                "price": 2.50,
            }
        }
    }


class ProductOptionUpdate(BaseModel):
    """Data to update an option."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="New option name",
        examples=["Double Cheese"],
    )
    price: float | None = Field(
        default=None,
        ge=0,
        description="New option price",
        examples=[3.50],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Double Cheese",
                "price": 3.50,
            }
        }
    }


class ProductOptionResponse(BaseModel):
    """Product option response."""

    id: PydanticObjectId = Field(description="Unique option ID")
    name: str = Field(description="Option name")
    price: float = Field(description="Additional option price")
    image: str | None = Field(default=None, description="Option image URL")
    created_at: datetime = Field(description="Creation date")
    updated_at: datetime = Field(description="Last update date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439014",
                "name": "Extra Cheese",
                "price": 2.50,
                "image": "https://cdn.example.com/options/507f1f77bcf86cd799439014/image.jpg",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }
    }


class ProductOptionGroupResponse(BaseModel):
    """Option group response with its options included."""

    id: PydanticObjectId = Field(description="Unique group ID")
    name: str = Field(description="Option group name")
    options: list[ProductOptionResponse] = Field(
        default=[],
        description="List of options within this group",
    )
    created_at: datetime = Field(description="Creation date")
    updated_at: datetime = Field(description="Last update date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439015",
                "name": "Extra Toppings",
                "options": [
                    {
                        "id": "507f1f77bcf86cd799439014",
                        "name": "Extra Cheese",
                        "price": 2.50,
                        "image": None,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }
    }


# ════════════════════════════════════════════════════════════
# PRODUCT DETAIL RESPONSE
# ════════════════════════════════════════════════════════════
class ProductDetailResponse(BaseModel):
    """Complete product response with all variants and option groups."""

    id: PydanticObjectId = Field(description="Unique product ID")
    user_id: PydanticObjectId = Field(description="Owner user ID")
    name: str = Field(description="Product name")
    description: str | None = Field(default=None, description="Product description")
    price: float = Field(description="Base product price")
    image: str | None = Field(default=None, description="Product image URL")
    variants: list[ProductVariantResponse] = Field(
        default=[],
        description="Product variants (sizes, flavors, etc.)",
    )
    option_groups: list[ProductOptionGroupResponse] = Field(
        default=[],
        description="Customizable option groups",
    )
    created_at: datetime = Field(description="Creation date")
    updated_at: datetime = Field(description="Last update date")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "user_id": "507f1f77bcf86cd799439012",
                "name": "Classic Burger",
                "description": "Delicious burger with 100% beef patty",
                "price": 12.99,
                "image": "https://cdn.example.com/products/507f1f77bcf86cd799439011/image.jpg",
                "variants": [
                    {
                        "id": "507f1f77bcf86cd799439013",
                        "name": "Large",
                        "price": 15.99,
                        "image": None,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "option_groups": [
                    {
                        "id": "507f1f77bcf86cd799439015",
                        "name": "Extra Toppings",
                        "options": [
                            {
                                "id": "507f1f77bcf86cd799439014",
                                "name": "Extra Cheese",
                                "price": 2.50,
                                "image": None,
                                "created_at": "2024-01-15T10:30:00Z",
                                "updated_at": "2024-01-15T10:30:00Z",
                            }
                        ],
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        }
    }


# ════════════════════════════════════════════════════════════
# PAGINATION
# ════════════════════════════════════════════════════════════
class PaginationParams(BaseModel):
    """Pagination parameters."""

    skip: int = Field(default=0, ge=0, description="Records to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Records limit")


class ProductListResponse(BaseModel):
    """Paginated product list response."""

    items: list[ProductResponse] = Field(description="List of products")
    total: int = Field(description="Total available products")
    skip: int = Field(description="Records skipped")
    limit: int = Field(description="Limit applied")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "user_id": "507f1f77bcf86cd799439012",
                        "name": "Classic Burger",
                        "description": "Delicious burger with 100% beef patty",
                        "price": 12.99,
                        "image": "https://cdn.example.com/products/abc/image.jpg",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                    }
                ],
                "total": 50,
                "skip": 0,
                "limit": 20,
            }
        }
    }


# ════════════════════════════════════════════════════════════
# GENERIC RESPONSES
# ════════════════════════════════════════════════════════════
class MessageResponse(BaseModel):
    """Generic message response."""

    message: str = Field(description="Descriptive operation message")

    model_config = {
        "json_schema_extra": {
            "example": {"message": "Operation completed successfully"}
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(description="Error description")

    model_config = {"json_schema_extra": {"example": {"detail": "Resource not found"}}}
