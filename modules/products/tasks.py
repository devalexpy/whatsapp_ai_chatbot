"""
Background tasks for product operations using Upstash QStash SDK.

QStash is a serverless message queue that:
- Persists messages (survives server restarts)
- Handles retries automatically
- Calls your endpoint via HTTP when ready

Flow:
1. User updates product → mark as stale + send to QStash with delay
2. QStash waits for delay (debouncing)
3. QStash calls POST /internal/embeddings/process/{product_id}
4. Your endpoint generates the embedding
"""

import logging
from urllib.parse import urljoin

from qstash import AsyncQStash

from config import settings
from modules.products.models import Product

logger = logging.getLogger(__name__)


def get_qstash_client() -> AsyncQStash | None:
    """Get QStash async client for publishing messages."""
    if not settings.qstash_token:
        logger.warning("QStash token not configured")
        return None
    return AsyncQStash(
        token=settings.qstash_token, base_url=settings.qstash_url or None
    )


async def _publish_to_qstash(
    destination_url: str,
    body: dict,
    delay_seconds: int | None = None,
    deduplication_id: str | None = None,
) -> bool:
    """
    Publish a message to QStash using the official SDK.

    Args:
        destination_url: Full URL that QStash will call
        body: JSON body to send
        delay_seconds: Delay before delivery (for debouncing)
        deduplication_id: If provided, prevents duplicate messages within 10 min

    Returns:
        True if published successfully
    """
    client = get_qstash_client()
    if not client:
        logger.warning("QStash not configured, skipping background task")
        return False

    try:
        # Build publish options
        await client.message.publish_json(
            url=destination_url,
            body=body,
            delay=f"{delay_seconds}s" if delay_seconds else None,
            deduplication_id=deduplication_id,
        )
        logger.info(f"QStash: Published to {destination_url}")
        return True
    except Exception as e:
        logger.error(f"QStash: Failed to publish - {e}")
        return False


async def schedule_embedding_update(product_id: str) -> None:
    """
    Schedule an embedding update via QStash with deduplication.

    Multiple calls within 10 minutes for the same product will be deduplicated,
    ensuring only one embedding generation happens.

    Args:
        product_id: Product ID to update
    """
    # Build the callback URL
    callback_url = urljoin(
        settings.app_base_url,
        f"/internal/embeddings/process/{product_id}",
    )

    logger.info(f"QStash: Publishing to {callback_url}")

    await _publish_to_qstash(
        destination_url=callback_url,
        body={"product_id": product_id},
        delay_seconds=settings.qstash_delay_seconds,
        # Deduplication: same product within 10 min = only one call
        deduplication_id=f"embedding-{product_id}",
    )


async def mark_product_embedding_stale(product: Product) -> None:
    """
    Mark a product's embedding as stale and schedule background update.

    Call this whenever the product or its related data changes.
    """
    if product.id:
        product.embedding_stale = True
        await product.save()
        await schedule_embedding_update(str(product.id))


async def mark_product_stale_by_id(product_id: str) -> None:
    """
    Mark a product's embedding as stale by ID and schedule update.

    Useful when you have the ID but not the full product object.
    """
    from beanie import PydanticObjectId

    product = await Product.get(PydanticObjectId(product_id))
    if product:
        await mark_product_embedding_stale(product)
