from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from bot.graph.state import ChatState


def confirm_product(state: ChatState) -> Command[Literal["asking_for_variant", END]]:  # ty:ignore[invalid-type-form]
    """Confirm the product selection."""
    user_message = state.get("user_message", "")

    if user_message.lower() == "si" or user_message.lower() == "sí":
        return Command(
            update={
                "current_step": "ASKING_FOR_VARIANT",
            },
            goto="asking_for_variant",
        )
    elif user_message.lower() == "no":
        return Command(
            update={
                "current_step": "IDLE",
                "response": "¡Entiendo! Si no encontraste el producto que buscabas o prefieres no ordenar en este momento, está bien 😊.\n"
                "Si deseas buscar otro producto o tienes alguna otra consulta, ¡aquí estoy para ayudarte! "
                "¿Te gustaría intentar con otro producto o preguntar algo más?",
            },
            goto=END,
        )
    else:
        return Command(
            update={
                "response": "Esa no es una opción válida. ¿Te gustaría ordenar otro producto? 😊 Dime si o no.",
            },
            goto=END,
        )
