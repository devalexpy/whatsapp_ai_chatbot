from bot.graph.state import ChatState


def fallback(state: ChatState) -> dict:
    """Fallback node."""
    return {
        "response": (
            "🤔 Hmm, no estoy seguro de cómo ayudarte con eso.\n\n"
            "Pero puedo asistirte con:\n"
            "🛒 *Hacer un pedido* - Dime qué te gustaría ordenar\n"
            "❓ *Información* - Pregunta por horarios, ubicación o métodos de pago\n\n"
            "¿Qué te gustaría hacer? 😊"
        )
    }
