import json
import requests
from typing import Optional

from graphs.config import (
    LLM_API_URL,
    LLM_MODEL_NAME,
    LLM_API_KEY,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)


class LLMClientError(Exception):
    pass


def _validate_config():
    missing = []
    if not LLM_API_URL:
        missing.append("LLM_API_URL")
    if not LLM_MODEL_NAME:
        missing.append("LLM_MODEL_NAME")
    if not LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if missing:
        raise LLMClientError(
            f"LLM config incomplete — set these in graphs/config.py: {', '.join(missing)}"
        )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    _validate_config()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }

    payload = {
        "model": LLM_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature if temperature is not None else LLM_TEMPERATURE,
        "max_tokens": max_tokens if max_tokens is not None else LLM_MAX_TOKENS,
    }

    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=120)
    except requests.exceptions.RequestException as e:
        raise LLMClientError(f"LLM API request failed: {e}") from e

    if response.status_code != 200:
        raise LLMClientError(
            f"LLM API returned HTTP {response.status_code}: {response.text[:500]}"
        )

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise LLMClientError(f"LLM API returned invalid JSON: {e}") from e

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise LLMClientError(
            f"Unexpected LLM response structure: {json.dumps(data)[:500]}"
        ) from e

    return content.strip()


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> dict:
    raw = call_llm(system_prompt, user_prompt, temperature, max_tokens)

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise LLMClientError(
            f"LLM response is not valid JSON.\nRaw:\n{raw[:1000]}\nError: {e}"
        ) from e
