from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from bot.graph.state import ChatState


def select_product(state: ChatState) -> Command[Literal["asking_for_variant", END]]:  # ty:ignore[invalid-type-form]
    """Select a product from the search results.

    Uses Command to combine state updates and routing:
    - If product selected → go to asking_for_variant
    - If error → go to END (stay in current step)
    """
    user_message = state.get("user_message", "")
    search_results = state.get("search_results", [])

    selected_product = None

    if user_message.strip().isdigit():
        try:
            index = int(user_message) - 1
            selected_product = search_results[index]
        except (IndexError, ValueError):
            pass
    else:
        # Try to match by name
        selected_product = next(
            (
                p
                for p in search_results
                if p.get("name", "").lower() == user_message.lower()
            ),
            None,
        )

    if selected_product:
        # Product found → continue to asking_for_variant
        return Command(
            update={
                "current_step": "ASKING_FOR_VARIANT",
                "current_product": selected_product,
            },
            goto="asking_for_variant",
        )
    else:
        # Product not found → stay and ask again
        return Command(
            update={
                "response": "No encontré ese producto. ¿Cuál te gustaría ordenar? "
                "Dime el número o el nombre 😊",
            },
            goto=END,
        )
