"""
Internal endpoints for background processing.

These endpoints are called by QStash and should NOT be exposed publicly.
Secured with signature verification using Upstash SDK.
"""

import logging

from fastapi import APIRouter, Header, HTTPException, Request, status
from qstash import Receiver

from config import settings
from modules.products.embeddings import update_product_embedding
from modules.products.models import Product

logger = logging.getLogger(__name__)

internal_router = APIRouter(
    prefix="/internal/embeddings",
    tags=["🔒 Internal"],
    include_in_schema=False,  # Hide from OpenAPI docs
)


def get_qstash_receiver() -> Receiver | None:
    """Get QStash receiver for signature verification."""
    if not settings.qstash_current_signing_key:
        return None
    return Receiver(
        current_signing_key=settings.qstash_current_signing_key,
        next_signing_key=settings.qstash_next_signing_key
        or settings.qstash_current_signing_key,
    )


@internal_router.post("/process/{product_id}")
async def process_embedding(
    product_id: str,
    request: Request,
    upstash_signature: str | None = Header(default=None, alias="Upstash-Signature"),
):
    """
    Process embedding for a product.

    Called by QStash after the delay period.
    """
    # Verify the request came from QStash using official SDK
    receiver = get_qstash_receiver()
    if receiver and upstash_signature:
        body = await request.body()
        body_str = body.decode("utf-8") if body else ""
        url = str(request.url)

        try:
            receiver.verify(
                body=body_str,
                signature=upstash_signature,
                url=url,
            )
        except Exception as e:
            logger.warning(f"Invalid QStash signature for product {product_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

    # Get product
    from beanie import PydanticObjectId

    product = await Product.get(PydanticObjectId(product_id))

    if not product:
        logger.warning(f"Product {product_id} not found for embedding update")
        # Return 200 to prevent QStash retries for deleted products
        return {"status": "skipped", "reason": "product_not_found"}

    if not product.embedding_stale:
        logger.info(f"Product {product_id} embedding already up to date")
        return {"status": "skipped", "reason": "already_updated"}

    try:
        await update_product_embedding(product)
        logger.info(f"Successfully updated embedding for product {product_id}")
        return {"status": "success", "product_id": product_id}

    except Exception as e:
        logger.error(f"Failed to update embedding for product {product_id}: {e}")
        # Return 500 to trigger QStash retry
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
