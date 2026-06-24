import os
import json
import time
import logging
import boto3
from typing import Optional

from graphs.config import (
    AWS_BEARER_TOKEN_BEDROCK,
    AWS_DEFAULT_REGION,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_MAX_RETRIES,
)

logger = logging.getLogger(__name__)


class LLMClientError(Exception):
    pass


def _validate_config():
    missing = []
    if not AWS_BEARER_TOKEN_BEDROCK:
        missing.append("AWS_BEARER_TOKEN_BEDROCK")
    if not AWS_DEFAULT_REGION:
        missing.append("AWS_DEFAULT_REGION")
    if not LLM_MODEL_NAME:
        missing.append("LLM_MODEL_NAME")
    if missing:
        raise LLMClientError(
            f"AWS/Bedrock config incomplete — set these in your .env: {', '.join(missing)}"
        )


_bedrock_client = None


def _get_client():
    global _bedrock_client
    if _bedrock_client is None:
        try:
            _bedrock_client = boto3.client(
                service_name="bedrock-runtime",
                region_name=AWS_DEFAULT_REGION,
            )
        except Exception as e:
            raise LLMClientError(f"Failed to initialize AWS Bedrock client: {e}") from e
    return _bedrock_client


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    _validate_config()

    client = _get_client()
    temp_val = temperature if temperature is not None else LLM_TEMPERATURE
    max_tokens_val = max_tokens if max_tokens is not None else LLM_MAX_TOKENS

    last_error = None
    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            response = client.converse(
                modelId=LLM_MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": user_prompt}]
                    }
                ],
                system=[
                    {
                        "text": system_prompt
                    }
                ],
                inferenceConfig={
                    "temperature": temp_val,
                    "maxTokens": max_tokens_val
                }
            )
            content = response["output"]["message"]["content"][0]["text"]
            return content.strip()

        except (KeyError, IndexError) as e:
            raise LLMClientError(
                f"Unexpected AWS Bedrock response structure: {json.dumps(response)}"
            ) from e
        except Exception as e:
            last_error = e
            if attempt < LLM_MAX_RETRIES:
                wait = 2 ** attempt
                logger.warning(
                    f"Bedrock call failed (attempt {attempt}/{LLM_MAX_RETRIES}): {e}. "
                    f"Retrying in {wait}s..."
                )
                print(f"LLM call failed (attempt {attempt}/{LLM_MAX_RETRIES}): {e}. Retrying in {wait}s...")
                time.sleep(wait)

    raise LLMClientError(
        f"AWS Bedrock Converse API call failed after {LLM_MAX_RETRIES} attempts "
        f"(model: {LLM_MODEL_NAME}): {last_error}"
    ) from last_error


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
