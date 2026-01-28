from typing import TypedDict

from langchain_core.prompts import PromptTemplate

from bot.graph.constans import INTENT_PROMPT
from bot.graph.state import ChatState, Intent
from bot.llm import get_fast_model

INTENT_PROMPT_TEMPLATE = PromptTemplate.from_template(INTENT_PROMPT.read_text())

llm = get_fast_model()


class IntentOutput(TypedDict):
    """Intent output."""

    intent: Intent


async def detect_intent(state: ChatState) -> dict:
    """Detect user intent from the conversation state."""
    user_message = state.get("user_message", "")

    structured_llm = llm.with_structured_output(IntentOutput)
    prompt = INTENT_PROMPT_TEMPLATE.format(user_message=user_message)
    intent_output = await structured_llm.ainvoke(prompt)
    intent = intent_output["intent"]

    return {"intent": intent}
