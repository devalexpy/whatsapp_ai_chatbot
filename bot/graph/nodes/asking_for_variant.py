"""Node to ask user for product variant selection."""

from typing import TYPE_CHECKING

from bot.graph.state import ChatState
from bot.graph.state import ProductVariant as ProductVariantState
from modules.products import service as products_service

if TYPE_CHECKING:
    from modules.products.models import ProductVariant


def parse_variant_results(
    variants: list["ProductVariant"],
) -> list[ProductVariantState]:
    """Convert ProductVariant models to serializable dicts for state."""
    return [
        ProductVariantState(id=str(v.id), name=v.name, price=v.price) for v in variants
    ]


async def asking_for_variant(
    state: ChatState,
) -> dict:  # ty:ignore[invalid-type-form]
    """Ask user to select a variant for the current product."""
    current_product = state.get("current_product")
    assert current_product is not None

    user_id = state.get("user_id", "")
    product_id = current_product.get("id", "")
    product_name = current_product.get("name", "Producto")

    variants = await products_service.get_variants_by_product(product_id, user_id)

    if variants:
        variants_data = parse_variant_results(variants)
        variant_list = "\n".join(
            f"  {i}. {v['name']} - ${v['price']:.2f}"
            for i, v in enumerate(variants_data, 1)
        )
        return {
            "current_step": "SELECTING_VARIANT",
            "variants_results": variants_data,
            "response": (
                f"✅ *{product_name}* seleccionado.\n\n"
                f"📋 Variantes disponibles:\n{variant_list}\n\n"
                "¿Te gustaría elegir una variante? Dime el número o nombre 😊\n"
                "Si no deseas elegir variante, dime *no*"
            ),
        }

    return {
        "current_step": "ASKING_FOR_OPTIONS",
    }
