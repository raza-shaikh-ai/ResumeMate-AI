import os
import json
import boto3
from typing import Optional

from graphs.config import (
    AWS_BEARER_TOKEN_BEDROCK,
    AWS_DEFAULT_REGION,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)


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


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    _validate_config()

    if AWS_BEARER_TOKEN_BEDROCK:
        os.environ["AWS_BEARER_TOKEN_BEDROCK"] = AWS_BEARER_TOKEN_BEDROCK

    try:
        client = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_DEFAULT_REGION,
        )
    except Exception as e:
        raise LLMClientError(f"Failed to initialize AWS Bedrock client: {e}") from e

    temp_val = temperature if temperature is not None else LLM_TEMPERATURE
    max_tokens_val = max_tokens if max_tokens is not None else LLM_MAX_TOKENS

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
    except Exception as e:
        raise LLMClientError(f"AWS Bedrock Converse API call failed: {e}") from e

    try:
        content = response["output"]["message"]["content"][0]["text"]
    except (KeyError, IndexError) as e:
        raise LLMClientError(
            f"Unexpected AWS Bedrock response structure: {json.dumps(response)}"
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

