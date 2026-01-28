"""
Centralized LLM management for the chatbot.

All LLM instances (chat models, embeddings) are created and cached here.
This allows easy switching between providers and consistent configuration.
"""

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.vectorstores import VectorStore
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from config import settings


# ════════════════════════════════════════════════════════════
# CHAT MODELS
# ════════════════════════════════════════════════════════════
@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """
    Get the main chat model for conversations (cached).

    Uses OpenAI by default. To add more providers:
    1. Add config in settings (e.g., anthropic_api_key)
    2. Add conditional logic here
    """
    return ChatOpenAI(
        model=settings.openai_chat_model,  # type: ignore
        temperature=settings.openai_chat_temperature,
        api_key=settings.openai_api_key,  # type: ignore
    )


@lru_cache(maxsize=1)
def get_fast_model() -> BaseChatModel:
    """
    Get a fast/cheap model for simple tasks (intent detection, etc.).

    Uses gpt-4o-mini for speed and cost efficiency.
    """
    return ChatOpenAI(
        model="gpt-4o-mini",  # type: ignore
        temperature=0,
        api_key=settings.openai_api_key,  # type: ignore
    )


# ════════════════════════════════════════════════════════════
# EMBEDDING MODELS
# ════════════════════════════════════════════════════════════
@lru_cache(maxsize=1)
def get_embeddings_model() -> Embeddings:
    """
    Get the embeddings model for semantic search (cached).

    Uses OpenAI text-embedding-3-small by default.
    """
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,  # type: ignore
        dimensions=settings.openai_embedding_dimensions,
        api_key=settings.openai_api_key,  # type: ignore
    )


# ════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════
async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for a single text."""
    embeddings = get_embeddings_model()
    return await embeddings.aembed_query(text)


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single batch."""
    embeddings = get_embeddings_model()
    return await embeddings.aembed_documents(texts)


# ════════════════════════════════════════════════════════════
# VECTOR STORE
# ════════════════════════════════════════════════════════════
@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    """Get the vector store for semantic search (cached)."""
    return MongoDBAtlasVectorSearch.from_connection_string(
        connection_string=settings.mongo_uri,
        namespace="whatsapp_ai_chatbot.products",
        embedding=get_embeddings_model(),
        index_name="products_embedding",
        text_key="embedding_text",  # Campo donde guardamos el texto del embedding
    )
