from pathlib import Path

PROMPTS_PATH = Path(__file__).parent.parent / "prompts"

SEMANTIC_SEARCH_PRODUCTS_PROMPT = PROMPTS_PATH / "semantic_search_products_prompt.txt"

INTENT_PROMPT = PROMPTS_PATH / "intent_prompt.txt"

QUERY_FORMAT_PROMPT = PROMPTS_PATH / "query_format_prompt.txt"

RERANK_PROMPT = PROMPTS_PATH / "rerank_prompt.txt"
