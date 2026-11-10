"""
AI categorization module using an OpenAI-compatible /chat/completions endpoint.

Why temperature=0?
Temperature controls randomness. For classification tasks like categorization,
we want deterministic, consistent, and predictable outputs, not creativity.

Why fallback to Category.OTHER?
External API calls can fail (network timeouts, rate limits, provider outages, or
invalid keys). Resilient software must degrade gracefully—an expense tracker should
never fail to record an expense just because the categorization AI is unavailable.
"""

import logging
import os
import re
from typing import Optional
from dotenv import load_dotenv
import httpx

from app.models import Category

# Load environment variables from .env if present
load_dotenv()

logger = logging.getLogger("expense_tracker.llm")


def get_llm_config() -> tuple[Optional[str], str, str]:
    """Retrieve LLM settings from environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    return api_key, base_url, model


def parse_category(raw_output: str) -> Optional[Category]:
    """
    Leniently parse LLM response into a valid Category enum member.
    Strips whitespace and punctuation, handles case-insensitivity,
    and checks if an allowed category name is present.
    """
    if not raw_output:
        return None

    # Clean punctuation and whitespace: e.g. " Food. " -> "food"
    cleaned = raw_output.strip().strip("'\"`.").lower()

    # 1. Exact match against lowercase enum value or enum name
    for cat in Category:
        if cleaned == cat.value.lower() or cleaned == cat.name.lower():
            return cat

    # 2. Match individual words in the response
    words = re.findall(r"\b[A-Za-z]+\b", raw_output)
    for word in words:
        for cat in Category:
            if word.lower() == cat.value.lower():
                return cat

    return None


def categorize(description: str) -> Category:
    """
    Categorize an expense description using an OpenAI-compatible LLM.

    Resilience rules:
    - If API key is missing or blank: logs warning, returns Category.OTHER.
    - If network error, timeout, or HTTP error occurs: logs warning, returns Category.OTHER.
    - If output does not match any valid category: logs warning, returns Category.OTHER.
    - Never raises an unhandled exception to prevent disrupting expense creation.
    """
    api_key, base_url, model = get_llm_config()

    # Check for missing or placeholder API key
    if not api_key or api_key.strip() == "" or api_key == "your_api_key_here":
        logger.warning("LLM_API_KEY not set or placeholder; defaulting to Category.OTHER")
        return Category.OTHER

    categories_list = ", ".join([c.value for c in Category])
    endpoint = f"{base_url}/chat/completions"

    system_prompt = (
        f"You are an expense categorization assistant. "
        f"The allowed categories are: {categories_list}. "
        f"Reply with exactly one category name, nothing else."
    )
    user_prompt = f"Expense description: {description}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 10,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        # Use synchronous httpx Client with 10-second timeout
        with httpx.Client(timeout=10.0) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed_cat = parse_category(raw_text)

            if parsed_cat:
                return parsed_cat
            else:
                logger.warning(
                    "LLM returned an unrecognized category '%s'; defaulting to Category.OTHER",
                    raw_text,
                )
                return Category.OTHER

    except httpx.TimeoutException as exc:
        logger.warning("LLM request timed out after 10s: %s; defaulting to Category.OTHER", exc)
        return Category.OTHER
    except httpx.HTTPStatusError as exc:
        logger.warning("LLM API returned HTTP status error %s; defaulting to Category.OTHER", exc.response.status_code)
        return Category.OTHER
    except httpx.RequestError as exc:
        logger.warning("LLM request network error: %s; defaulting to Category.OTHER", exc)
        return Category.OTHER
    except Exception as exc:
        logger.warning("Unexpected error during LLM categorization: %s; defaulting to Category.OTHER", exc)
        return Category.OTHER

