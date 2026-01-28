from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

from bot.graph.constans import RERANK_PROMPT
from bot.graph.state import ChatState, Product
from bot.llm import get_fast_model, get_vector_store

# LLM for re-ranking
llm = get_fast_model()
vector_store = get_vector_store()

RERANK_PROMPT_TEMPLATE = PromptTemplate.from_template(RERANK_PROMPT.read_text())


def parse_search_results(documents: list[Document]) -> list[Product]:
    """Parse LangChain Documents into Product dicts for state."""
    products: list[Product] = []

    for doc in documents:
        metadata = doc.metadata
        product: Product = {
            "id": str(metadata.get("_id", "")),
            "name": metadata.get("name", "Producto"),
            "description": metadata.get("description"),
            "price": float(metadata.get("price", 0)),
        }
        products.append(product)

    return products


async def rerank_products(user_message: str, products: list[Product]) -> list[Product]:
    """Use LLM to filter and keep only relevant products."""
    if not products:
        return []

    # Format products list for the prompt
    products_list = "\n".join(
        f"{i + 1}. {p['name']} - {p.get('description', '')[:100]}"
        for i, p in enumerate(products)
    )

    try:
        prompt = RERANK_PROMPT_TEMPLATE.format(
            user_request=user_message,
            products_list=products_list,
        )
        response = await llm.ainvoke(prompt)
        result = str(response.content).strip().lower()

        if result == "none":
            return []

        # Parse the numbers from response (e.g., "1, 3" -> [1, 3])
        relevant_indices = []
        for part in result.replace(",", " ").split():
            try:
                idx = int(part.strip()) - 1  # Convert to 0-based index
                if 0 <= idx < len(products):
                    relevant_indices.append(idx)
            except ValueError:
                continue

        # Return only the relevant products
        return [products[i] for i in relevant_indices]

    except Exception:
        # Fallback: return first product if any
        return products[:1] if products else []


def format_single_product(product: Product) -> str:
    """Format a single product with full details."""
    name = product.get("name", "Producto")
    price = product.get("price", 0)
    description = product.get("description", "")

    parts = [
        f"🎯 *{name}*\n",
        f"💰 Precio: ${price:.2f}",
    ]

    if description:
        parts.append(f"\n📝 {description}")

    parts.append("\n\n¿Te gustaría ordenar este producto? 😊")

    return "\n".join(parts)


def format_products_response(products: list[Product]) -> str:
    """Format products list into a friendly response message."""
    # Single product: show full details
    if len(products) == 1:
        return format_single_product(products[0])

    # Multiple products: show list
    response_parts = ["🛒 ¡Encontré estos productos para ti!\n"]

    for i, product in enumerate(products, 1):
        name = product.get("name", "Producto")
        price = product.get("price", 0)
        description = product.get("description", "")

        product_line = f"{i}. *{name}* - ${price:.2f}"
        if description:
            # Truncate long descriptions
            short_desc = (
                description[:80] + "..." if len(description) > 80 else description
            )
            product_line += f"\n   _{short_desc}_"

        response_parts.append(product_line)

    response_parts.append("\n¿Cuál te gustaría ordenar? Dime el número o el nombre 😊")

    return "\n".join(response_parts)


async def semantic_search_products(state: ChatState) -> dict:
    """Semantic search products node with LLM re-ranking."""
    user_id = state.get("user_id", "")
    user_message = state.get("user_message") or ""

    try:
        # Use pre_filter for MongoDB Atlas Vector Search
        pre_filter = {"user_id": {"$eq": user_id}} if user_id else None

        # Get more candidates for re-ranking (k=10)
        results_with_scores = await vector_store.asimilarity_search_with_score(
            user_message,
            k=10,
            pre_filter=pre_filter,
        )

        documents = [doc for doc, _ in results_with_scores]

    except Exception:
        documents = []

    # Parse results into products
    candidates = parse_search_results(documents)

    # Re-rank with LLM to filter relevant products
    products = await rerank_products(user_message, candidates)

    if not products:
        return {
            "search_results": [],
            "response": "🔍 No encontré productos que coincidan con tu búsqueda.\n\n"
            "¿Podrías ser más específico o preguntarme por otra cosa? 😊",
        }

    # Format friendly response
    response = format_products_response(products)

    result = {
        "search_results": products,
        "response": response,
    }

    if len(products) == 1:
        result["current_step"] = "ASKING_FOR_VARIANT"
        result["current_product"] = products[0]
    else:
        result["current_step"] = "SELECTING_PRODUCT"

    return result
