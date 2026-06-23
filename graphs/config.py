import os

LLM_API_URL: str = os.getenv("LLM_API_URL", "")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "")
LLM_API_KEY: str = os.getenv("AGENT_ROUTER_TOKEN") or os.getenv("LLM_API_KEY") or ""

MAX_PAGE_RETRIES: int = 3
LLM_TEMPERATURE: float = 0.3
LLM_MAX_TOKENS: int = 4096
