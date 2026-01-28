from bot.graph.state import ChatState


def initial_message(state: ChatState) -> dict:
    """Initial message node."""
    return {
        "current_step": "INITIAL_MESSAGE",
        "response": (
            "¡Hola! 👋 Bienvenido, soy tu asistente virtual. 🤖\n\n"
            "Estoy aquí para ayudarte con:\n"
            "🛒 Realizar pedidos\n"
            "📋 Ver nuestro menú\n"
            "ℹ️ Información sobre horarios, ubicación y más\n\n"
            "¿En qué puedo ayudarte hoy? 😊"
        ),
    }
