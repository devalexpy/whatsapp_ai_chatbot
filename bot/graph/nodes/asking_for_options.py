from bot.graph.state import ChatState
from modules.products import service as products_service


async def asking_for_options(state: ChatState) -> dict:
    """Ask user for options."""
    current_product = state.get("current_product")
    assert current_product is not None

    user_id = state.get("user_id", "")
    product_id = current_product.get("id", "")

    option_groups = await products_service.get_option_groups_by_product(
        product_id, user_id
    )
    if option_groups:
        formated_option_groups_names = ", ".join([og.name for og in option_groups])
        return {
            "current_step": "SELECTING_OPTION",
            "response": f"¿Te gustaría agregar algun extra? algo como {formated_option_groups_names} 😊\n"
            "Si no deseas agregar ningun extra, dime *no*",
        }
    else:
        return {
            "current_step": "IDLE",
            "response": "No hay extras disponibles para este producto. ¿Te gustaría ordenar otro producto?",
        }
