import os
from dotenv import load_dotenv
load_dotenv(override=True)

AWS_BEARER_TOKEN_BEDROCK: str = os.getenv("AWS_BEARER_TOKEN_BEDROCK", "")
AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "us.amazon.nova-pro-v1:0")

MAX_PAGE_RETRIES: int = 3
LLM_MAX_RETRIES: int = 3
LLM_TEMPERATURE: float = 0.3
LLM_MAX_TOKENS: int = 4096