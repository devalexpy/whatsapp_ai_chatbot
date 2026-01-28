from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from bot.graph.nodes.asking_for_variant import asking_for_variant
from bot.graph.nodes.confirm_product import confirm_product
from bot.graph.nodes.fallback import fallback
from bot.graph.nodes.initial_message import initial_message
from bot.graph.nodes.intent import detect_intent
from bot.graph.nodes.select_product import select_product
from bot.graph.nodes.select_variant import select_variant
from bot.graph.nodes.semantic_search_products import semantic_search_products
from bot.graph.routing import intent_router
from bot.graph.state import ChatState

# ════════════════════════════════════════════════════════════
# GRAPH DEFINITION
# ════════════════════════════════════════════════════════════
bot_graph = StateGraph(ChatState)  # type: ignore

# ════════════════════════════════════════════════════════════
# NODES
# ════════════════════════════════════════════════════════════
bot_graph.add_node("intent", detect_intent)
bot_graph.add_node("initial_message", initial_message)
bot_graph.add_node("fallback", fallback)
bot_graph.add_node("semantic_search_products", semantic_search_products)
bot_graph.add_node("select_product", select_product)
bot_graph.add_node("asking_for_variant", asking_for_variant)
bot_graph.add_node("confirm_product", confirm_product)
bot_graph.add_node("select_variant", select_variant)

# ════════════════════════════════════════════════════════════
# EDGES
# ════════════════════════════════════════════════════════════
bot_graph.add_edge(START, "intent")
bot_graph.add_conditional_edges(
    "intent",
    intent_router,
    {
        "initial_message": "initial_message",
        "fallback": "fallback",
        "semantic_search_products": "semantic_search_products",
        "select_product": "select_product",
        "asking_for_variant": "asking_for_variant",
        "confirm_product": "confirm_product",
        "select_variant": "select_variant",
    },
)

bot_graph.add_edge("initial_message", END)
bot_graph.add_edge("fallback", END)
bot_graph.add_edge("semantic_search_products", END)
# select_product uses Command for routing (no edge needed)
# confirm_product uses Command for routing (no edge needed)
# select_variant uses Command for routing (no edge needed)
bot_graph.add_edge("asking_for_variant", END)

# ════════════════════════════════════════════════════════════
# COMPILED GRAPH WITH MEMORY
# ════════════════════════════════════════════════════════════
memory = MemorySaver()
compiled_graph = bot_graph.compile(checkpointer=memory)
