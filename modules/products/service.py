"""Product service with business logic."""

from datetime import datetime, timezone

from beanie import PydanticObjectId

from modules.products.models import (
    Product,
    ProductOption,
    ProductOptionGroup,
    ProductVariant,
)
from modules.products.schemas import (
    ProductCreate,
    ProductDetailResponse,
    ProductOptionCreate,
    ProductOptionGroupCreate,
    ProductOptionGroupResponse,
    ProductOptionGroupUpdate,
    ProductOptionResponse,
    ProductOptionUpdate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
)
from modules.products.storage import storage_service
from modules.products.tasks import (
    mark_product_embedding_stale,
    schedule_embedding_update,
)
from modules.users.models import User


def utc_now() -> datetime:
    """Return the current datetime in UTC."""
    return datetime.now(timezone.utc)


# ────────────────────────────────────────────────────────────
# Product Service
# ────────────────────────────────────────────────────────────
async def get_products(
    user: User, skip: int = 0, limit: int = 20
) -> tuple[list[Product], int]:
    """Get paginated list of products for a user."""
    query = Product.find(Product.user.id == user.id)  # type: ignore[attr-defined]
    total = await query.count()
    products = await query.skip(skip).limit(limit).to_list()
    return products, total


async def get_product_by_id(product_id: str) -> Product | None:
    """Get a product by ID."""
    return await Product.get(PydanticObjectId(product_id))


async def get_product_by_id_for_user(product_id: str, user: User) -> Product | None:
    """Get a product by ID only if it belongs to the user."""
    product = await get_product_by_id(product_id)
    if not product:
        return None
    # Check ownership
    await product.fetch_link(Product.user)  # type: ignore[attr-defined]
    if product.user.id != user.id:  # type: ignore[attr-defined]
        return None
    return product


async def get_product_detail(
    product_id: str, user: User
) -> ProductDetailResponse | None:
    """Get a product with its variants and option groups."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product:
        return None

    # Get variants
    variants = await ProductVariant.find(
        ProductVariant.product.id == product.id  # type: ignore
    ).to_list()

    # Get option groups
    option_groups = await ProductOptionGroup.find(
        ProductOptionGroup.product.id == product.id  # type: ignore
    ).to_list()

    # Get options for each group
    option_groups_response = []
    for group in option_groups:
        options = await ProductOption.find(
            ProductOption.option_group.id == group.id  # type: ignore
        ).to_list()
        option_groups_response.append(
            ProductOptionGroupResponse(
                id=group.id,
                name=group.name,
                options=[
                    ProductOptionResponse(
                        id=opt.id,
                        name=opt.name,
                        price=opt.price,
                        is_default=opt.is_default,
                        image=opt.image,
                        created_at=opt.created_at,
                        updated_at=opt.updated_at,
                    )
                    for opt in options
                ],
                created_at=group.created_at,
                updated_at=group.updated_at,
            )
        )

    await product.fetch_link(Product.user)  # type: ignore[attr-defined]
    user_id = product.user.id  # type: ignore[attr-defined]
    assert user_id is not None
    assert product.id is not None

    return ProductDetailResponse(
        id=product.id,
        user_id=user_id,
        name=product.name,
        description=product.description,
        price=product.price,
        image=product.image,
        variants=[
            ProductVariantResponse(
                id=v.id,
                name=v.name,
                price=v.price,
                image=v.image,
                created_at=v.created_at,
                updated_at=v.updated_at,
            )
            for v in variants
        ],
        option_groups=option_groups_response,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


async def create_product(user: User, data: ProductCreate) -> Product:
    """Create a new product for a user."""
    product = Product(user=user, embedding_stale=True, **data.model_dump())
    await product.insert()
    await product.fetch_link(Product.user)

    # Schedule embedding generation in background (debounced)
    schedule_embedding_update(str(product.id))

    return product


async def update_product(
    product_id: str, user: User, data: ProductUpdate
) -> Product | None:
    """Update an existing product if it belongs to the user."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = utc_now()
        await product.update({"$set": update_data})
        await product.sync()

        # Schedule embedding update in background (debounced)
        await mark_product_embedding_stale(product)

    return product


async def delete_product(product_id: str, user: User) -> bool:
    """Delete a product and all its related resources if it belongs to the user."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product:
        return False

    # Delete product image if exists
    if product.image:
        storage_service.delete_file(product.image)

    # Delete variants and their images
    variants = await ProductVariant.find(
        ProductVariant.product.id == product.id  # type: ignore
    ).to_list()
    for variant in variants:
        if variant.image:
            storage_service.delete_file(variant.image)
        await variant.delete()

    # Delete option groups and options
    option_groups = await ProductOptionGroup.find(
        ProductOptionGroup.product.id == product.id  # type: ignore
    ).to_list()

    for group in option_groups:
        options = await ProductOption.find(
            ProductOption.option_group.id == group.id  # type: ignore
        ).to_list()
        for option in options:
            if option.image:
                storage_service.delete_file(option.image)
            await option.delete()
        await group.delete()

    await product.delete()
    return True


async def update_product_image(
    product_id: str, user: User, file_key: str
) -> Product | None:
    """Update product image if it belongs to the user."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product:
        return None

    # Delete previous image if exists
    if product.image:
        storage_service.delete_file(product.image)

    product.image = file_key
    product.updated_at = utc_now()
    await product.save()
    return product


async def delete_product_image(product_id: str, user: User) -> bool:
    """Delete product image if it belongs to the user."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product or not product.image:
        return False

    storage_service.delete_file(product.image)
    product.image = None
    product.updated_at = utc_now()
    await product.save()
    return True


# ────────────────────────────────────────────────────────────
# Product Variant Service
# ────────────────────────────────────────────────────────────
async def get_variants_by_product(product_id: str, user: User) -> list[ProductVariant]:
    """Get variants for a product if it belongs to the user."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product:
        return []
    return await ProductVariant.find(
        ProductVariant.product.id == product.id  # type: ignore
    ).to_list()


async def get_variant_by_id(variant_id: str) -> ProductVariant | None:
    """Get a variant by ID."""
    return await ProductVariant.get(PydanticObjectId(variant_id))


async def get_variant_by_id_for_user(
    variant_id: str, user: User
) -> ProductVariant | None:
    """Get a variant by ID only if its product belongs to the user."""
    variant = await get_variant_by_id(variant_id)
    if not variant:
        return None
    # Fetch the product to check ownership
    await variant.fetch_link(ProductVariant.product)
    product = variant.product  # type: ignore
    await product.fetch_link(Product.user)  # type: ignore[attr-defined]
    if product.user.id != user.id:  # type: ignore[attr-defined]
        return None
    return variant


async def create_variant(
    product_id: str, user: User, data: ProductVariantCreate
) -> ProductVariant | None:
    """Create a new variant for a product if it belongs to the user."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product:
        return None

    variant = ProductVariant(product=product, **data.model_dump())
    await variant.insert()
    await variant.fetch_link(ProductVariant.product)

    # Update product embedding (includes variant info)
    await mark_product_embedding_stale(product)

    return variant


async def update_variant(
    variant_id: str, user: User, data: ProductVariantUpdate
) -> ProductVariant | None:
    """Update an existing variant if its product belongs to the user."""
    variant = await get_variant_by_id_for_user(variant_id, user)
    if not variant:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = utc_now()
        await variant.update({"$set": update_data})
        await variant.sync()

        # Update product embedding
        await variant.fetch_link(ProductVariant.product)
        await mark_product_embedding_stale(variant.product)  # type: ignore

    return variant


async def delete_variant(variant_id: str, user: User) -> bool:
    """Delete a variant if its product belongs to the user."""
    variant = await get_variant_by_id_for_user(variant_id, user)
    if not variant:
        return False

    # Get product before deleting variant
    await variant.fetch_link(ProductVariant.product)
    product: Product = variant.product  # type: ignore[assignment]

    if variant.image:
        storage_service.delete_file(variant.image)

    await variant.delete()

    # Update product embedding
    await mark_product_embedding_stale(product)

    return True


async def update_variant_image(
    variant_id: str, user: User, file_key: str
) -> ProductVariant | None:
    """Update variant image if its product belongs to the user."""
    variant = await get_variant_by_id_for_user(variant_id, user)
    if not variant:
        return None

    if variant.image:
        storage_service.delete_file(variant.image)

    variant.image = file_key
    variant.updated_at = utc_now()
    await variant.save()
    return variant


async def delete_variant_image(variant_id: str, user: User) -> bool:
    """Delete variant image if its product belongs to the user."""
    variant = await get_variant_by_id_for_user(variant_id, user)
    if not variant or not variant.image:
        return False

    storage_service.delete_file(variant.image)
    variant.image = None
    variant.updated_at = utc_now()
    await variant.save()
    return True


# ────────────────────────────────────────────────────────────
# Product Option Group Service
# ────────────────────────────────────────────────────────────
async def get_option_groups_by_product(
    product_id: str, user: User
) -> list[ProductOptionGroup]:
    """Get option groups for a product if it belongs to the user."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product:
        return []
    return await ProductOptionGroup.find(
        ProductOptionGroup.product.id == product.id  # type: ignore
    ).to_list()


async def get_option_group_by_id(group_id: str) -> ProductOptionGroup | None:
    """Get an option group by ID."""
    return await ProductOptionGroup.get(PydanticObjectId(group_id))


async def get_option_group_by_id_for_user(
    group_id: str, user: User
) -> ProductOptionGroup | None:
    """Get an option group by ID only if its product belongs to the user."""
    group = await get_option_group_by_id(group_id)
    if not group:
        return None
    # Fetch the product to check ownership
    await group.fetch_link(ProductOptionGroup.product)
    product = group.product  # type: ignore
    await product.fetch_link(Product.user)  # type: ignore[attr-defined]
    if product.user.id != user.id:  # type: ignore[attr-defined]
        return None
    return group


async def create_option_group(
    product_id: str, user: User, data: ProductOptionGroupCreate
) -> ProductOptionGroup | None:
    """Create a new option group if the product belongs to the user."""
    product = await get_product_by_id_for_user(product_id, user)
    if not product:
        return None

    group = ProductOptionGroup(product=product, **data.model_dump())
    await group.insert()
    await group.fetch_link(ProductOptionGroup.product)

    # Update product embedding
    await mark_product_embedding_stale(product)

    return group


async def update_option_group(
    group_id: str, user: User, data: ProductOptionGroupUpdate
) -> ProductOptionGroup | None:
    """Update an option group if its product belongs to the user."""
    group = await get_option_group_by_id_for_user(group_id, user)
    if not group:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = utc_now()
        await group.update({"$set": update_data})
        await group.sync()

        # Update product embedding
        await group.fetch_link(ProductOptionGroup.product)
        await mark_product_embedding_stale(group.product)  # type: ignore

    return group


async def delete_option_group(group_id: str, user: User) -> bool:
    """Delete an option group and all its options if its product belongs to the user."""
    group = await get_option_group_by_id_for_user(group_id, user)
    if not group:
        return False

    # Get product before deleting
    await group.fetch_link(ProductOptionGroup.product)
    product: Product = group.product  # type: ignore[assignment]

    # Delete group options
    options = await ProductOption.find(
        ProductOption.option_group.id == group.id  # type: ignore
    ).to_list()

    for option in options:
        if option.image:
            storage_service.delete_file(option.image)
        await option.delete()

    await group.delete()

    # Update product embedding
    await mark_product_embedding_stale(product)

    return True


# ────────────────────────────────────────────────────────────
# Product Option Service
# ────────────────────────────────────────────────────────────
async def get_options_by_group(group_id: str, user: User) -> list[ProductOption]:
    """Get options for a group if its product belongs to the user."""
    group = await get_option_group_by_id_for_user(group_id, user)
    if not group:
        return []
    return await ProductOption.find(
        ProductOption.option_group.id == group.id  # type: ignore
    ).to_list()


async def get_option_by_id(option_id: str) -> ProductOption | None:
    """Get an option by ID."""
    return await ProductOption.get(PydanticObjectId(option_id))


async def get_option_by_id_for_user(option_id: str, user: User) -> ProductOption | None:
    """Get an option by ID only if its product belongs to the user."""
    option = await get_option_by_id(option_id)
    if not option:
        return None
    # Fetch the group and product to check ownership
    await option.fetch_link(ProductOption.option_group)
    group: ProductOptionGroup = option.option_group  # type: ignore
    await group.fetch_link(ProductOptionGroup.product)
    product: Product = group.product  # type: ignore
    await product.fetch_link(Product.user)  # type: ignore[attr-defined]
    if product.user.id != user.id:  # type: ignore[attr-defined]
        return None
    return option


async def create_option(
    group_id: str, user: User, data: ProductOptionCreate
) -> ProductOption | None:
    """Create a new option in a group if its product belongs to the user."""
    group = await get_option_group_by_id_for_user(group_id, user)
    if not group:
        return None

    option = ProductOption(option_group=group, **data.model_dump())
    await option.insert()
    await option.fetch_link(ProductOption.option_group)

    # Update product embedding
    await group.fetch_link(ProductOptionGroup.product)
    await mark_product_embedding_stale(group.product)  # type: ignore

    return option


async def update_option(
    option_id: str, user: User, data: ProductOptionUpdate
) -> ProductOption | None:
    """Update an option if its product belongs to the user."""
    option = await get_option_by_id_for_user(option_id, user)
    if not option:
        return None

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = utc_now()
        await option.update({"$set": update_data})
        await option.sync()

        # Update product embedding
        await option.fetch_link(ProductOption.option_group)
        group: ProductOptionGroup = option.option_group  # type: ignore
        await group.fetch_link(ProductOptionGroup.product)
        await mark_product_embedding_stale(group.product)  # type: ignore

    return option


async def delete_option(option_id: str, user: User) -> bool:
    """Delete an option if its product belongs to the user."""
    option = await get_option_by_id_for_user(option_id, user)
    if not option:
        return False

    # Get product before deleting
    await option.fetch_link(ProductOption.option_group)
    group: ProductOptionGroup = option.option_group  # type: ignore
    await group.fetch_link(ProductOptionGroup.product)
    product: Product = group.product  # type: ignore

    if option.image:
        storage_service.delete_file(option.image)

    await option.delete()

    # Update product embedding
    await mark_product_embedding_stale(product)

    return True


async def update_option_image(
    option_id: str, user: User, file_key: str
) -> ProductOption | None:
    """Update option image if its product belongs to the user."""
    option = await get_option_by_id_for_user(option_id, user)
    if not option:
        return None

    if option.image:
        storage_service.delete_file(option.image)

    option.image = file_key
    option.updated_at = utc_now()
    await option.save()
    return option


async def delete_option_image(option_id: str, user: User) -> bool:
    """Delete option image if its product belongs to the user."""
    option = await get_option_by_id_for_user(option_id, user)
    if not option or not option.image:
        return False

    storage_service.delete_file(option.image)
    option.image = None
    option.updated_at = utc_now()
    await option.save()
    return True
