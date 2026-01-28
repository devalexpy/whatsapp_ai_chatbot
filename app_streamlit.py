"""
Streamlit app para probar el grafo de LangGraph como un chat.

Ejecutar con:
    uv run streamlit run app_streamlit.py
"""

import asyncio
import uuid

import streamlit as st
from beanie import init_beanie
from pymongo import AsyncMongoClient

from bot.graph.builder import compiled_graph
from config import settings
from modules.products.models import (
    Product,
    ProductOption,
    ProductOptionGroup,
    ProductVariant,
)
from modules.users.models import User

# Rebuild Product model to resolve forward reference to User
Product.model_rebuild()

# MongoDB client and DB - created lazily in the same event loop
_mongo_client: AsyncMongoClient | None = None
_db_initialized = False


async def ensure_db_initialized():
    """Initialize MongoDB and Beanie in the current event loop."""
    global _mongo_client, _db_initialized
    if not _db_initialized:
        # Create client in the current event loop
        _mongo_client = AsyncMongoClient(settings.mongo_uri)
        db = _mongo_client.whatsapp_ai_chatbot

        await init_beanie(
            database=db,
            document_models=[
                User,
                Product,
                ProductVariant,
                ProductOptionGroup,
                ProductOption,
            ],
        )
        _db_initialized = True


# ════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="💬 WhatsApp Bot Chat",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom CSS
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    /* Header */
    .chat-header {
        background: linear-gradient(135deg, #00a884 0%, #008069 100%);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .header-avatar {
        font-size: 2rem;
    }
    
    .header-title {
        color: white;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0;
    }
    
    .header-status {
        color: rgba(255,255,255,0.8);
        font-size: 0.75rem;
        margin: 0;
    }
    
    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar */
    .sidebar-title {
        color: #00a884;
        font-weight: 600;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════
async def run_graph(user_message: str, thread_id: str, user_id: str) -> dict:
    """Run the graph with a user message using thread_id for state management."""
    # Ensure DB is initialized in the same event loop
    await ensure_db_initialized()

    result = await compiled_graph.ainvoke(
        {"user_message": user_message, "user_id": user_id},
        config={"configurable": {"thread_id": thread_id}},  # type: ignore[arg-type]
    )
    return result


# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Configuración")

    # User ID input
    user_id_input = st.text_input(
        "🏪 User ID (dueño de productos)",
        value=st.session_state.get("user_id", ""),
        placeholder="Ej: 507f1f77bcf86cd799439011",
        help="ID del usuario cuyos productos quieres consultar",
    )
    if user_id_input:
        st.session_state.user_id = user_id_input

    st.markdown("---")
    st.markdown("### 🧪 Panel de Pruebas")

    st.markdown(
        '<p class="sidebar-title">📝 Mensajes de ejemplo</p>', unsafe_allow_html=True
    )

    examples = {
        "🛒 Pedidos": [
            "Quiero ordenar una pizza",
            "Me das el menú?",
            "Cuánto cuesta la hamburguesa?",
        ],
        "ℹ️ Info": [
            "Cuál es el horario?",
            "Dónde están ubicados?",
            "Hacen envíos?",
        ],
        "👋 Saludos": [
            "Hola",
            "Buenos días",
            "Buenas tardes",
        ],
        "❓ Otros": [
            "askdjhaskjdh",
            "Cuéntame un chiste",
        ],
    }

    # Check if user_id is set for disabling buttons
    sidebar_has_user_id = bool(st.session_state.get("user_id", ""))

    for category, msgs in examples.items():
        with st.expander(category, expanded=False):
            for msg in msgs:
                if st.button(
                    msg,
                    key=f"ex_{msg}",
                    use_container_width=True,
                    disabled=not sidebar_has_user_id,
                ):
                    st.session_state.pending_message = msg

    st.markdown("---")

    # Clear chat button
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.last_state = {}
        st.rerun()

    # Show session info
    st.markdown("### 🔍 Sesión")
    st.caption(f"Thread: {st.session_state.get('thread_id', 'N/A')[:8]}...")

    # Show current state
    st.markdown("### 📊 Estado actual")
    if "last_state" in st.session_state and st.session_state.last_state:
        st.json(st.session_state.last_state)
    else:
        st.caption("Sin estado aún")


# ════════════════════════════════════════════════════════════
# MAIN CHAT INTERFACE
# ════════════════════════════════════════════════════════════

# Header
st.markdown(
    """
    <div class="chat-header">
        <span class="header-avatar">🤖</span>
        <div>
            <p class="header-title">Asistente de Pedidos</p>
            <p class="header-status">● En línea</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "pending_message" not in st.session_state:
    st.session_state.pending_message = ""
if "last_state" not in st.session_state:
    st.session_state.last_state = {}

# Check if user_id is configured
has_user_id = bool(st.session_state.user_id)

if not has_user_id:
    st.warning(
        "⚠️ Configura el **User ID** en el panel lateral para comenzar a chatear."
    )

# Display chat messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.write(msg["content"])

# Chat input (disabled if no user_id)
if prompt := st.chat_input(
    "Escribe un mensaje..." if has_user_id else "Configura el User ID primero",
    disabled=not has_user_id,
):
    st.session_state.pending_message = prompt

# Process pending message (from sidebar examples or chat input)
if st.session_state.pending_message and has_user_id:
    user_input = st.session_state.pending_message

    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display user message
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    # Run the graph and get response
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Pensando..."):
            result = asyncio.run(
                run_graph(
                    user_input,
                    st.session_state.thread_id,
                    st.session_state.user_id,
                )
            )

            # Save state for sidebar display
            st.session_state.last_state = dict(result)

            # Get bot response
            bot_response = result.get("response", "...")

            # Display response
            st.write(bot_response)

            # Add bot message to history
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": bot_response,
                }
            )

    # Clear pending message
    st.session_state.pending_message = ""
    st.rerun()

# Footer
st.markdown(
    """
    <div style="text-align: center; padding: 1rem; color: #8696a0; font-size: 0.75rem;">
        🔒 Los mensajes son de prueba • Powered by LangGraph
    </div>
    """,
    unsafe_allow_html=True,
)
