"""
Embedding service for semantic product search using LangChain.

Uses OpenAI embeddings by default. Add more providers as needed.
"""

import logging
from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from config import settings
from modules.products.models import (
    Product,
    ProductOption,
    ProductOptionGroup,
    ProductVariant,
)

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embeddings_model() -> Embeddings:
    """Get the OpenAI embeddings model (cached)."""
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
        api_key=settings.openai_api_key,  # ty:ignore[unknown-argument]
    )


async def generate_product_text(product: Product) -> str:
    """
    Generate enriched text representation of a product for embedding.

    Combines product name, description, price, variants, and options
    into a single searchable text.
    """
    parts = [f"Producto: {product.name}"]

    if product.description:
        parts.append(f"Descripción: {product.description}")

    parts.append(f"Precio: ${product.price:.2f}")

    # Get variants
    variants = await ProductVariant.find(
        ProductVariant.product.id == product.id  # type: ignore
    ).to_list()

    if variants:
        variant_texts = [f"{v.name} (${v.price:.2f})" for v in variants]
        parts.append(f"Variantes: {', '.join(variant_texts)}")

    # Get option groups and options
    option_groups = await ProductOptionGroup.find(
        ProductOptionGroup.product.id == product.id  # type: ignore
    ).to_list()

    if option_groups:
        parts.append("Opciones:")
        for group in option_groups:
            options = await ProductOption.find(
                ProductOption.option_group.id == group.id  # type: ignore
            ).to_list()

            if options:
                option_texts = []
                for opt in options:
                    if opt.is_default:
                        option_texts.append(f"{opt.name} (incluido)")
                    elif opt.price > 0:
                        option_texts.append(f"{opt.name} (+${opt.price:.2f})")
                    else:
                        option_texts.append(opt.name)

                parts.append(f"  - {group.name}: {', '.join(option_texts)}")

    return "\n".join(parts)


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding vector for text."""
    embeddings = get_embeddings_model()
    return await embeddings.aembed_query(text)


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single batch."""
    embeddings = get_embeddings_model()
    return await embeddings.aembed_documents(texts)


async def update_product_embedding(product: Product) -> Product:
    """Generate and update embedding for a product."""
    try:
        embedding_text = await generate_product_text(product)
        embedding = await generate_embedding(embedding_text)

        product.embedding = embedding
        product.embedding_text = embedding_text
        product.embedding_stale = False
        await product.save()

        logger.info(f"Updated embedding for product {product.id}: {product.name}")
        return product

    except Exception as e:
        logger.error(f"Failed to generate embedding for product {product.id}: {e}")
        raise


async def search_products_by_embedding(
    query: str,
    user_id: str,
    limit: int = 10,
) -> list[dict]:
    """
    Search products using semantic similarity.

    Requires MongoDB Atlas Vector Search index: 'product_embedding_index'
    """
    from beanie import PydanticObjectId

    query_embedding = await generate_embedding(query)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "product_embedding_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": limit * 10,
                "limit": limit,
                "filter": {"user.$id": PydanticObjectId(user_id)},
            }
        },
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "description": 1,
                "price": 1,
                "image": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    return await Product.aggregate(pipeline).to_list()


async def regenerate_all_embeddings(user_id: str) -> int:
    """Regenerate embeddings for all products of a user."""
    from beanie import PydanticObjectId

    products = await Product.find(
        Product.user.id == PydanticObjectId(user_id)  # type: ignore
    ).to_list()

    if not products:
        return 0

    # Generate texts
    texts = []
    for product in products:
        try:
            text = await generate_product_text(product)
            texts.append(text)
        except Exception as e:
            logger.error(f"Failed to generate text for product {product.id}: {e}")
            texts.append(f"Producto: {product.name}")

    # Batch embedding generation
    try:
        embeddings_list = await generate_embeddings_batch(texts)
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        embeddings_list = []
        for text in texts:
            try:
                emb = await generate_embedding(text)
                embeddings_list.append(emb)
            except Exception:
                embeddings_list.append([])

    # Update products
    count = 0
    for product, text, embedding in zip(products, texts, embeddings_list):
        if embedding:
            try:
                product.embedding = embedding
                product.embedding_text = text
                await product.save()
                count += 1
            except Exception as e:
                logger.error(f"Failed to save product {product.id}: {e}")

    logger.info(f"Regenerated embeddings for {count}/{len(products)} products")
    return count
