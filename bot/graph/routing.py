"""Routing functions for the bot graph."""

from bot.graph.state import ChatState

INTENT_ROUTE_MAP = {
    "INITIAL": {
        "IDLE": "initial_message",
        "SELECTING_PRODUCT": "select_product",
        "CONFIRMING_PRODUCT": "confirm_product",
        "ASKING_FOR_VARIANT": "asking_for_variant",
        "SELECTING_VARIANT": "select_variant",
    },
    "OTHER": {
        "IDLE": "initial_message",
        "SELECTING_PRODUCT": "select_product",
        "CONFIRMING_PRODUCT": "confirm_product",
        "ASKING_FOR_VARIANT": "asking_for_variant",
        "SELECTING_VARIANT": "select_variant",
    },
    "ORDER": {
        "IDLE": "semantic_search_products",
        "INITIAL_MESSAGE": "semantic_search_products",
        "SELECTING_PRODUCT": "select_product",
        "CONFIRMING_PRODUCT": "confirm_product",
        "ASKING_FOR_VARIANT": "asking_for_variant",
        "SELECTING_VARIANT": "select_variant",
    },
}


def intent_router(state: ChatState) -> str:
    """Route function for conditional edges based on intent and step."""
    intent = state.get("intent", "")
    current_step = state.get("current_step", "IDLE")  # Default to IDLE

    return INTENT_ROUTE_MAP.get(intent, {}).get(current_step, "fallback")
