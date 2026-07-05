"""
API client to interact with Groq or Grok LLM service.
Sends requests to OpenAI-compatible chat endpoints.
"""
from __future__ import annotations

import json
import requests
from src.config import settings
from src.logger import logger


class LLMClientError(RuntimeError):
    """Raised when the LLM API request fails."""


def generate_llm_response(prompt: str, system_message: str | None = None) -> str:
    """Sends a chat completion request to the configured LLM API (Groq/Grok)."""
    if not settings.llm_api_key:
        logger.warning("LLM_API_KEY is not configured. The AI assistant will run in mock mode.")
        return (
            "[MOCK INSIGHT] LLM API Key is missing. Here is a simulated response:\n"
            "Our overall revenue shows solid growth of +5.4% WoW, driven mainly by the FOODS category. "
            "Stores in California (CA) are the top performers, contributing 42% of total revenue. "
            "We recommend boosting inventory for high-velocity items in FOODS_1 in preparation for the upcoming holiday season."
        )

    # Clean endpoint URL
    base_url = settings.llm_api_url.rstrip("/")
    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.llm_model_name,
        "messages": messages,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }

    logger.info(f"Sending request to LLM API: {url} | Model: {settings.llm_model_name}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            logger.error(f"LLM API Error (HTTP {response.status_code}): {response.text}")
            raise LLMClientError(f"LLM API error (HTTP {response.status_code}): {response.text}")

        result_json = response.json()
        response_text = result_json["choices"][0]["message"]["content"]
        logger.info("LLM response successfully generated.")
        return response_text
    except Exception as e:
        logger.exception("Failed to connect or communicate with LLM API.")
        raise LLMClientError(f"LLM communications failure: {e}") from e
