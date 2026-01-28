"""Product router with REST CRUD endpoints.

This module contains all endpoints related to product management,
including variants, option groups, and individual options.

Image upload flow:
1. Get presigned URL: POST /{entity_id}/image/upload-url
2. Upload image: PUT to the returned URL with the specified Content-Type
3. Confirm upload: POST /{entity_id}/image/confirm
"""

from typing import Annotated, cast

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Path, Query, status

from modules.products import service
from modules.products.schemas import (
    ConfirmUploadRequest,
    ErrorResponse,
    MessageResponse,
    ProductCreate,
    ProductDetailResponse,
    ProductListResponse,
    ProductOptionCreate,
    ProductOptionGroupCreate,
    ProductOptionGroupResponse,
    ProductOptionGroupUpdate,
    ProductOptionResponse,
    ProductOptionUpdate,
    ProductResponse,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
    UploadUrlRequest,
    UploadUrlResponse,
)
from modules.products.storage import ALLOWED_CONTENT_TYPES, storage_service
from modules.users.dependencies import CurrentUser

# ════════════════════════════════════════════════════════════
# TYPE ALIASES FOR PATH PARAMETERS
# ════════════════════════════════════════════════════════════
ProductId = Annotated[
    str,
    Path(
        description="Unique product ID (MongoDB ObjectId)",
        examples=["507f1f77bcf86cd799439011"],
    ),
]
VariantId = Annotated[
    str,
    Path(
        description="Unique variant ID (MongoDB ObjectId)",
        examples=["507f1f77bcf86cd799439013"],
    ),
]
OptionGroupId = Annotated[
    str,
    Path(
        description="Unique option group ID (MongoDB ObjectId)",
        examples=["507f1f77bcf86cd799439015"],
    ),
]
OptionId = Annotated[
    str,
    Path(
        description="Unique option ID (MongoDB ObjectId)",
        examples=["507f1f77bcf86cd799439014"],
    ),
]


# ════════════════════════════════════════════════════════════
# COMMON RESPONSES
# ════════════════════════════════════════════════════════════
COMMON_RESPONSES = {
    401: {
        "description": "Unauthorized - Invalid or expired token",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {"detail": "Could not validate credentials"}
            }
        },
    },
    403: {
        "description": "Forbidden - No permission to access this resource",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {"detail": "Not authorized to access this resource"}
            }
        },
    },
}

NOT_FOUND_RESPONSE = {
    404: {
        "description": "Resource not found",
        "model": ErrorResponse,
        "content": {"application/json": {"example": {"detail": "Product not found"}}},
    },
}


# ════════════════════════════════════════════════════════════
# PRODUCTS ROUTER
# ════════════════════════════════════════════════════════════
products_router = APIRouter(
    prefix="/products",
    tags=["🛍️ Products"],
    responses=COMMON_RESPONSES,
)


# ────────────────────────────────────────────────────────────
# Products CRUD
# ────────────────────────────────────────────────────────────
@products_router.get(
    "",
    response_model=ProductListResponse,
    summary="List products",
    description="""
Gets all products for the authenticated user.

**Pagination:**
- Use `skip` to skip records (offset)
- Use `limit` to define how many products to return (max 100)

**Response:**
- `items`: Array of products
- `total`: Total available products (without pagination)
- `skip` and `limit`: Applied values
""",
    response_description="Paginated list of products",
)
async def list_products(
    current_user: CurrentUser,
    skip: int = Query(
        0, ge=0, description="Number of records to skip", examples=[0, 20, 40]
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Maximum number of records to return",
        examples=[10, 20, 50],
    ),
):
    products, total, variant_names_map = await service.get_products(
        current_user, skip=skip, limit=limit
    )
    return ProductListResponse(
        items=[
            ProductResponse(
                id=cast(PydanticObjectId, p.id),
                user_id=p.user.id,  # type: ignore[attr-defined]
                name=p.name,
                description=p.description,
                price=p.price,
                image=p.image,
                variant_names=variant_names_map.get(str(p.id), []),
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in products
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@products_router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description="""
Creates a new product for the authenticated user.

**Required fields:**
- `name`: Product name
- `price`: Base price (greater than 0)

**Optional field:**
- `description`: Detailed description

**Note:** To add an image, use the upload endpoint after creating the product.
""",
    response_description="Product created successfully",
    responses={
        201: {"description": "Product created successfully"},
        422: {
            "description": "Validation error - Invalid data",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "price"],
                                "msg": "Input should be greater than 0",
                                "type": "greater_than",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def create_product(current_user: CurrentUser, data: ProductCreate):
    product = await service.create_product(current_user, data)
    return ProductResponse(
        id=cast(PydanticObjectId, product.id),
        user_id=product.user.id,  # type: ignore[attr-defined]
        name=product.name,
        description=product.description,
        price=product.price,
        image=product.image,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@products_router.get(
    "/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get product with details",
    description="""
Gets a specific product with all related information:

**Includes:**
- Basic product data
- List of variants (sizes, flavors, etc.)
- Option groups with their options (extras, toppings, etc.)

**Ideal for:** Product detail view in the frontend.
""",
    response_description="Product with variants and options",
    responses=NOT_FOUND_RESPONSE,
)
async def get_product(current_user: CurrentUser, product_id: ProductId):
    product = await service.get_product_detail(product_id, current_user)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@products_router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
    description="""
Updates an existing product's data.

**Partial update:** Only fields sent in the body will be updated.
For example, to change only the price:

```json
{"price": 15.99}
```

**Updatable fields:**
- `name`: Product name
- `description`: Description
- `price`: Base price
""",
    response_description="Updated product",
    responses=NOT_FOUND_RESPONSE,
)
async def update_product(
    current_user: CurrentUser, product_id: ProductId, data: ProductUpdate
):
    product = await service.update_product(product_id, current_user, data)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductResponse(
        id=cast(PydanticObjectId, product.id),
        user_id=product.user.id,  # type: ignore[attr-defined]
        name=product.name,
        description=product.description,
        price=product.price,
        image=product.image,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@products_router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product",
    description="""
Deletes a product and **all** its related resources:

**Deleted:**
- ✓ The product
- ✓ All its variants
- ✓ All its option groups
- ✓ All options in each group
- ✓ Images for all elements

**⚠️ This action is irreversible.**
""",
    response_description="Product deleted (no content)",
    responses=NOT_FOUND_RESPONSE,
)
async def delete_product(current_user: CurrentUser, product_id: ProductId):
    deleted = await service.delete_product(product_id, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )


# ────────────────────────────────────────────────────────────
# Product Image (Presigned URLs)
# ────────────────────────────────────────────────────────────
@products_router.post(
    "/{product_id}/image/upload-url",
    response_model=UploadUrlResponse,
    summary="Get upload URL for image",
    description=f"""
Generates a presigned URL to upload the product image.

**Image upload flow:**

1️⃣ **Call this endpoint** with the image `content_type`

2️⃣ **Upload the image** by making a PUT request to the returned `upload_url`:
   ```
   PUT <upload_url>
   Content-Type: image/jpeg
   Body: <binary file>
   ```

3️⃣ **Confirm the upload** by calling `POST /products/{{product_id}}/image/confirm`
   with the returned `file_key`

**Allowed Content-Types:**
{", ".join(f"`{ct}`" for ct in ALLOWED_CONTENT_TYPES)}

**The URL expires** after the time indicated by `expires_in` (seconds).
""",
    response_description="Presigned URL and confirmation data",
    responses={
        **NOT_FOUND_RESPONSE,
        400: {
            "description": "Content-Type not allowed",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": f"Content-Type must be one of: {ALLOWED_CONTENT_TYPES}"
                    }
                }
            },
        },
    },
)
async def get_product_image_upload_url(
    current_user: CurrentUser, product_id: ProductId, request: UploadUrlRequest
):
    if request.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content-Type must be one of: {ALLOWED_CONTENT_TYPES}",
        )

    product = await service.get_product_by_id_for_user(product_id, current_user)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    result = storage_service.generate_upload_url(
        entity_type="products",
        entity_id=product_id,
        content_type=request.content_type,
    )
    return UploadUrlResponse(**result)


@products_router.post(
    "/{product_id}/image/confirm",
    response_model=MessageResponse,
    summary="Confirm image upload",
    description="""
Confirms that the image was uploaded successfully and associates it with the product.

**Prerequisites:**
1. Have obtained the upload URL with `POST /products/{product_id}/image/upload-url`
2. Have uploaded the file to the presigned URL

**Request:**
```json
{"file_key": "products/507f1f77bcf86cd799439011/1703606400.png"}
```

The `file_key` is returned by the get upload URL endpoint.
""",
    response_description="Image update confirmation",
    responses={
        **NOT_FOUND_RESPONSE,
        400: {
            "description": "File not found - Upload the image first",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "File not found. Make sure to upload first."}
                }
            },
        },
    },
)
async def confirm_product_image_upload(
    current_user: CurrentUser, product_id: ProductId, request: ConfirmUploadRequest
):
    if not storage_service.file_exists(request.file_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found. Make sure to upload first.",
        )

    product = await service.update_product_image(
        product_id, current_user, request.file_key
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return MessageResponse(message="Image updated successfully")


@products_router.delete(
    "/{product_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product image",
    description="""
Deletes the image associated with the product.

The image is removed from storage and the reference is cleared from the product.
""",
    response_description="Image deleted (no content)",
    responses={
        404: {
            "description": "Product or image not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "Product or image not found"}
                }
            },
        },
    },
)
async def delete_product_image(current_user: CurrentUser, product_id: ProductId):
    deleted = await service.delete_product_image(product_id, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product or image not found",
        )


# ────────────────────────────────────────────────────────────
# Product Variants (Sub-resource)
# ────────────────────────────────────────────────────────────
@products_router.get(
    "/{product_id}/variants",
    response_model=list[ProductVariantResponse],
    summary="List product variants",
    description="""
Gets all variants associated with a product.

**Variants** represent different versions of the same product:
- Sizes: Small, Medium, Large
- Flavors: Vanilla, Chocolate, Strawberry
- Presentations: Individual, Family

Each variant has its own price and optional image.
""",
    response_description="List of product variants",
    responses=NOT_FOUND_RESPONSE,
)
async def list_product_variants(current_user: CurrentUser, product_id: ProductId):
    product = await service.get_product_by_id_for_user(product_id, current_user)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    variants = await service.get_variants_by_product(product_id, current_user)
    return [
        ProductVariantResponse(
            id=cast(PydanticObjectId, v.id),
            name=v.name,
            price=v.price,
            image=v.image,
            created_at=v.created_at,
            updated_at=v.updated_at,
        )
        for v in variants
    ]


@products_router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product variant",
    description="""
Creates a new variant for the specified product.

**Example:** For a burger, create size variants:
```json
{"name": "Large", "price": 15.99}
```

The image can be added later using the variant upload endpoint.
""",
    response_description="Variant created successfully",
    responses=NOT_FOUND_RESPONSE,
)
async def create_product_variant(
    current_user: CurrentUser, product_id: ProductId, data: ProductVariantCreate
):
    variant = await service.create_variant(product_id, current_user, data)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductVariantResponse(
        id=cast(PydanticObjectId, variant.id),
        name=variant.name,
        price=variant.price,
        image=variant.image,
        created_at=variant.created_at,
        updated_at=variant.updated_at,
    )


# ────────────────────────────────────────────────────────────
# Product Option Groups (Sub-resource)
# ────────────────────────────────────────────────────────────
@products_router.get(
    "/{product_id}/option-groups",
    response_model=list[ProductOptionGroupResponse],
    summary="List product option groups",
    description="""
Gets all option groups for a product with their options.

**Option groups** organize product customizations:
- "Extra Toppings" → Cheese, Bacon, Avocado
- "Sauces" → BBQ, Mustard, Mayo
- "Sides" → Fries, Salad, Onion rings

Each group contains multiple options with additional prices.
""",
    response_description="Option groups with their options",
    responses=NOT_FOUND_RESPONSE,
)
async def list_product_option_groups(current_user: CurrentUser, product_id: ProductId):
    product = await service.get_product_by_id_for_user(product_id, current_user)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    groups = await service.get_option_groups_by_product(product_id, current_user)
    result = []
    for g in groups:
        options = await service.get_options_by_group(str(g.id), current_user)
        result.append(
            ProductOptionGroupResponse(
                id=cast(PydanticObjectId, g.id),
                name=g.name,
                options=[
                    ProductOptionResponse(
                        id=cast(PydanticObjectId, o.id),
                        name=o.name,
                        price=o.price,
                        is_default=o.is_default,
                        image=o.image,
                        created_at=o.created_at,
                        updated_at=o.updated_at,
                    )
                    for o in options
                ],
                created_at=g.created_at,
                updated_at=g.updated_at,
            )
        )
    return result


@products_router.post(
    "/{product_id}/option-groups",
    response_model=ProductOptionGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create option group",
    description="""
Creates a new option group for the product.

**Example:** Create "Extra Toppings" group:
```json
{"name": "Extra Toppings"}
```

After creating the group, use `POST /option-groups/{group_id}/options`
to add individual options.
""",
    response_description="Option group created",
    responses=NOT_FOUND_RESPONSE,
)
async def create_product_option_group(
    current_user: CurrentUser, product_id: ProductId, data: ProductOptionGroupCreate
):
    group = await service.create_option_group(product_id, current_user, data)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return ProductOptionGroupResponse(
        id=cast(PydanticObjectId, group.id),
        name=group.name,
        options=[],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


# ════════════════════════════════════════════════════════════
# VARIANTS ROUTER (Independent operations)
# ════════════════════════════════════════════════════════════
variants_router = APIRouter(
    prefix="/variants",
    tags=["📦 Product Variants"],
    responses=COMMON_RESPONSES,
)


@variants_router.get(
    "/{variant_id}",
    response_model=ProductVariantResponse,
    summary="Get variant by ID",
    description="Gets the details of a specific variant.",
    response_description="Variant data",
    responses={
        404: {
            "description": "Variant not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {"example": {"detail": "Variant not found"}}
            },
        },
    },
)
async def get_variant(current_user: CurrentUser, variant_id: VariantId):
    variant = await service.get_variant_by_id_for_user(variant_id, current_user)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )
    return ProductVariantResponse(
        id=cast(PydanticObjectId, variant.id),
        name=variant.name,
        price=variant.price,
        image=variant.image,
        created_at=variant.created_at,
        updated_at=variant.updated_at,
    )


@variants_router.patch(
    "/{variant_id}",
    response_model=ProductVariantResponse,
    summary="Update variant",
    description="""
Updates an existing variant's data.

**Partial update:** Only fields sent will be updated.

**Example:** Change only the name:
```json
{"name": "Extra Large"}
```
""",
    response_description="Updated variant",
    responses={
        404: {
            "description": "Variant not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {"example": {"detail": "Variant not found"}}
            },
        },
    },
)
async def update_variant(
    current_user: CurrentUser, variant_id: VariantId, data: ProductVariantUpdate
):
    variant = await service.update_variant(variant_id, current_user, data)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )
    return ProductVariantResponse(
        id=cast(PydanticObjectId, variant.id),
        name=variant.name,
        price=variant.price,
        image=variant.image,
        created_at=variant.created_at,
        updated_at=variant.updated_at,
    )


@variants_router.delete(
    "/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete variant",
    description="Deletes a variant and its associated image (if any).",
    response_description="Variant deleted (no content)",
    responses={
        404: {
            "description": "Variant not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {"example": {"detail": "Variant not found"}}
            },
        },
    },
)
async def delete_variant(current_user: CurrentUser, variant_id: VariantId):
    deleted = await service.delete_variant(variant_id, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )


# ────────────────────────────────────────────────────────────
# Variant Image (Presigned URLs)
# ────────────────────────────────────────────────────────────
@variants_router.post(
    "/{variant_id}/image/upload-url",
    response_model=UploadUrlResponse,
    summary="Get upload URL for variant image",
    description=f"""
Generates a presigned URL to upload a variant's image.

**Flow:** Same as for products:
1. Call this endpoint → get `upload_url` and `file_key`
2. PUT to `upload_url` with the image
3. Confirm with `POST /variants/{{variant_id}}/image/confirm`

**Allowed Content-Types:** {", ".join(f"`{ct}`" for ct in ALLOWED_CONTENT_TYPES)}
""",
    response_description="Presigned URL for upload",
    responses={
        400: {
            "description": "Content-Type not allowed",
            "model": ErrorResponse,
        },
        404: {
            "description": "Variant not found",
            "model": ErrorResponse,
        },
    },
)
async def get_variant_image_upload_url(
    current_user: CurrentUser, variant_id: VariantId, request: UploadUrlRequest
):
    if request.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content-Type must be one of: {ALLOWED_CONTENT_TYPES}",
        )

    variant = await service.get_variant_by_id_for_user(variant_id, current_user)
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    result = storage_service.generate_upload_url(
        entity_type="variants",
        entity_id=variant_id,
        content_type=request.content_type,
    )
    return UploadUrlResponse(**result)


@variants_router.post(
    "/{variant_id}/image/confirm",
    response_model=MessageResponse,
    summary="Confirm variant image upload",
    description="Confirms the image upload and associates it with the variant.",
    response_description="Image update confirmation",
    responses={
        400: {
            "description": "File not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "File not found. Make sure to upload first."}
                }
            },
        },
        404: {
            "description": "Variant not found",
            "model": ErrorResponse,
        },
    },
)
async def confirm_variant_image_upload(
    current_user: CurrentUser, variant_id: VariantId, request: ConfirmUploadRequest
):
    if not storage_service.file_exists(request.file_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found. Make sure to upload first.",
        )

    variant = await service.update_variant_image(
        variant_id, current_user, request.file_key
    )
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant not found",
        )

    return MessageResponse(message="Image updated successfully")


@variants_router.delete(
    "/{variant_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete variant image",
    description="Deletes the image associated with the variant.",
    response_description="Image deleted (no content)",
    responses={
        404: {
            "description": "Variant or image not found",
            "model": ErrorResponse,
        },
    },
)
async def delete_variant_image(current_user: CurrentUser, variant_id: VariantId):
    deleted = await service.delete_variant_image(variant_id, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variant or image not found",
        )


# ════════════════════════════════════════════════════════════
# OPTION GROUPS ROUTER (Independent operations)
# ════════════════════════════════════════════════════════════
option_groups_router = APIRouter(
    prefix="/option-groups",
    tags=["⚙️ Option Groups"],
    responses=COMMON_RESPONSES,
)


@option_groups_router.get(
    "/{group_id}",
    response_model=ProductOptionGroupResponse,
    summary="Get option group by ID",
    description="Gets an option group with all its options included.",
    response_description="Option group with its options",
    responses={
        404: {
            "description": "Option group not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {"example": {"detail": "Option group not found"}}
            },
        },
    },
)
async def get_option_group(current_user: CurrentUser, group_id: OptionGroupId):
    group = await service.get_option_group_by_id_for_user(group_id, current_user)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option group not found",
        )

    options = await service.get_options_by_group(group_id, current_user)
    return ProductOptionGroupResponse(
        id=cast(PydanticObjectId, group.id),
        name=group.name,
        options=[
            ProductOptionResponse(
                id=cast(PydanticObjectId, o.id),
                name=o.name,
                price=o.price,
                is_default=o.is_default,
                image=o.image,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in options
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@option_groups_router.patch(
    "/{group_id}",
    response_model=ProductOptionGroupResponse,
    summary="Update option group",
    description="""
Updates an option group's name.

**Example:**
```json
{"name": "Premium Extras"}
```
""",
    response_description="Updated group with its options",
    responses={
        404: {
            "description": "Option group not found",
            "model": ErrorResponse,
        },
    },
)
async def update_option_group(
    current_user: CurrentUser, group_id: OptionGroupId, data: ProductOptionGroupUpdate
):
    group = await service.update_option_group(group_id, current_user, data)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option group not found",
        )

    options = await service.get_options_by_group(group_id, current_user)
    return ProductOptionGroupResponse(
        id=cast(PydanticObjectId, group.id),
        name=group.name,
        options=[
            ProductOptionResponse(
                id=cast(PydanticObjectId, o.id),
                name=o.name,
                price=o.price,
                is_default=o.is_default,
                image=o.image,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in options
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@option_groups_router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete option group",
    description="""
Deletes an option group and **all** its options.

**⚠️ Includes:** Deletion of all options within the group and their images.
""",
    response_description="Group deleted (no content)",
    responses={
        404: {
            "description": "Option group not found",
            "model": ErrorResponse,
        },
    },
)
async def delete_option_group(current_user: CurrentUser, group_id: OptionGroupId):
    deleted = await service.delete_option_group(group_id, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option group not found",
        )


# ────────────────────────────────────────────────────────────
# Options within Group (Sub-resource)
# ────────────────────────────────────────────────────────────
@option_groups_router.get(
    "/{group_id}/options",
    response_model=list[ProductOptionResponse],
    summary="List group options",
    description="Gets all options from a specific group.",
    response_description="List of options",
    responses={
        404: {
            "description": "Option group not found",
            "model": ErrorResponse,
        },
    },
)
async def list_group_options(current_user: CurrentUser, group_id: OptionGroupId):
    group = await service.get_option_group_by_id_for_user(group_id, current_user)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option group not found",
        )

    options = await service.get_options_by_group(group_id, current_user)
    return [
        ProductOptionResponse(
            id=cast(PydanticObjectId, o.id),
            name=o.name,
            price=o.price,
            is_default=o.is_default,
            image=o.image,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in options
    ]


@option_groups_router.post(
    "/{group_id}/options",
    response_model=ProductOptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create option in group",
    description="""
Creates a new option within a group.

**Example:** Add "Extra Cheese" to the "Extra Toppings" group:
```json
{"name": "Extra Cheese", "price": 2.50}
```

Price can be 0 for options with no additional cost.
""",
    response_description="Option created successfully",
    responses={
        404: {
            "description": "Option group not found",
            "model": ErrorResponse,
        },
    },
)
async def create_group_option(
    current_user: CurrentUser, group_id: OptionGroupId, data: ProductOptionCreate
):
    option = await service.create_option(group_id, current_user, data)
    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option group not found",
        )
    return ProductOptionResponse(
        id=cast(PydanticObjectId, option.id),
        name=option.name,
        price=option.price,
        is_default=option.is_default,
        image=option.image,
        created_at=option.created_at,
        updated_at=option.updated_at,
    )


# ════════════════════════════════════════════════════════════
# OPTIONS ROUTER (Independent operations)
# ════════════════════════════════════════════════════════════
options_router = APIRouter(
    prefix="/options",
    tags=["🎯 Product Options"],
    responses=COMMON_RESPONSES,
)


@options_router.get(
    "/{option_id}",
    response_model=ProductOptionResponse,
    summary="Get option by ID",
    description="Gets the details of a specific option.",
    response_description="Option data",
    responses={
        404: {
            "description": "Option not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {"example": {"detail": "Option not found"}}
            },
        },
    },
)
async def get_option(current_user: CurrentUser, option_id: OptionId):
    option = await service.get_option_by_id_for_user(option_id, current_user)
    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option not found",
        )
    return ProductOptionResponse(
        id=cast(PydanticObjectId, option.id),
        name=option.name,
        price=option.price,
        is_default=option.is_default,
        image=option.image,
        created_at=option.created_at,
        updated_at=option.updated_at,
    )


@options_router.patch(
    "/{option_id}",
    response_model=ProductOptionResponse,
    summary="Update option",
    description="""
Updates an option's data.

**Partial update:** Only fields sent will be updated.

**Example:** Change price:
```json
{"price": 3.50}
```
""",
    response_description="Updated option",
    responses={
        404: {
            "description": "Option not found",
            "model": ErrorResponse,
        },
    },
)
async def update_option(
    current_user: CurrentUser, option_id: OptionId, data: ProductOptionUpdate
):
    option = await service.update_option(option_id, current_user, data)
    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option not found",
        )
    return ProductOptionResponse(
        id=cast(PydanticObjectId, option.id),
        name=option.name,
        price=option.price,
        is_default=option.is_default,
        image=option.image,
        created_at=option.created_at,
        updated_at=option.updated_at,
    )


@options_router.delete(
    "/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete option",
    description="Deletes an option and its associated image (if any).",
    response_description="Option deleted (no content)",
    responses={
        404: {
            "description": "Option not found",
            "model": ErrorResponse,
        },
    },
)
async def delete_option(current_user: CurrentUser, option_id: OptionId):
    deleted = await service.delete_option(option_id, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option not found",
        )


# ────────────────────────────────────────────────────────────
# Option Image (Presigned URLs)
# ────────────────────────────────────────────────────────────
@options_router.post(
    "/{option_id}/image/upload-url",
    response_model=UploadUrlResponse,
    summary="Get upload URL for option image",
    description=f"""
Generates a presigned URL to upload an option's image.

**Upload flow:**
1. Call this endpoint → get `upload_url` and `file_key`
2. PUT to `upload_url` with the image
3. Confirm with `POST /options/{{option_id}}/image/confirm`

**Allowed Content-Types:** {", ".join(f"`{ct}`" for ct in ALLOWED_CONTENT_TYPES)}
""",
    response_description="Presigned URL for upload",
    responses={
        400: {
            "description": "Content-Type not allowed",
            "model": ErrorResponse,
        },
        404: {
            "description": "Option not found",
            "model": ErrorResponse,
        },
    },
)
async def get_option_image_upload_url(
    current_user: CurrentUser, option_id: OptionId, request: UploadUrlRequest
):
    if request.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content-Type must be one of: {ALLOWED_CONTENT_TYPES}",
        )

    option = await service.get_option_by_id_for_user(option_id, current_user)
    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option not found",
        )

    result = storage_service.generate_upload_url(
        entity_type="options",
        entity_id=option_id,
        content_type=request.content_type,
    )
    return UploadUrlResponse(**result)


@options_router.post(
    "/{option_id}/image/confirm",
    response_model=MessageResponse,
    summary="Confirm option image upload",
    description="Confirms the image upload and associates it with the option.",
    response_description="Image update confirmation",
    responses={
        400: {
            "description": "File not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "File not found. Make sure to upload first."}
                }
            },
        },
        404: {
            "description": "Option not found",
            "model": ErrorResponse,
        },
    },
)
async def confirm_option_image_upload(
    current_user: CurrentUser, option_id: OptionId, request: ConfirmUploadRequest
):
    if not storage_service.file_exists(request.file_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found. Make sure to upload first.",
        )

    option = await service.update_option_image(
        option_id, current_user, request.file_key
    )
    if not option:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option not found",
        )

    return MessageResponse(message="Image updated successfully")


@options_router.delete(
    "/{option_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete option image",
    description="Deletes the image associated with the option.",
    response_description="Image deleted (no content)",
    responses={
        404: {
            "description": "Option or image not found",
            "model": ErrorResponse,
        },
    },
)
async def delete_option_image(current_user: CurrentUser, option_id: OptionId):
    deleted = await service.delete_option_image(option_id, current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Option or image not found",
        )
