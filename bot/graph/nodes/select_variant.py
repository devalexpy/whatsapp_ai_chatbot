from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from bot.graph.state import ChatState


def select_variant(state: ChatState) -> Command[Literal[END]]:  # ty:ignore[invalid-type-form]
    """Select a variant for the current product."""
    user_message = state.get("user_message", "")
    variants_results = state.get("variants_results")
    assert variants_results is not None
    if user_message.strip().isdigit():
        try:
            index = int(user_message) - 1
            selected_variant = variants_results[index]
        except (IndexError, ValueError):
            pass
    elif user_message.strip().lower() == "no":
        return Command(
            update={
                "current_step": "ASKING_FOR_OPTIONS",
            },
            goto=END,
        )
    else:
        selected_variant = next(
            (v for v in variants_results if v["name"].lower() == user_message.lower()),  # type: ignore
            None,
        )

    if selected_variant:
        return Command(
            update={
                "current_variant": selected_variant,
            },
            goto=END,
        )
    else:
        return Command(
            update={
                "response": "No encontré esa variante. ¿Te gustaría elegir alguna otra variante?",
            },
            goto=END,
        )
