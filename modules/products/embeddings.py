"""
Embedding service for semantic product search.

Uses centralized LLM configuration from bot.llm module.
"""

import logging

from bot.llm import generate_embedding, generate_embeddings_batch
from modules.products.models import Product

logger = logging.getLogger(__name__)


async def generate_product_text(product: Product) -> str:
    """
    Generate simple text representation of a product for embedding.

    Uses only name and description for cleaner semantic matching.
    Variants and options are handled separately after initial search.
    """
    parts = [product.name]

    if product.description:
        # Truncate description to first 200 chars for cleaner embedding
        desc = (
            product.description[:200]
            if len(product.description) > 200
            else product.description
        )
        parts.append(desc)

    return " - ".join(parts)


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
