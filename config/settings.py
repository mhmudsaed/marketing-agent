"""Enterprise configuration management."""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Centralized application settings."""
    
    # LLM (OpenAI-compatible: OpenRouter, llama.cpp server, vLLM, etc.)
    LLM_BASE_URL: str = os.getenv(
        "LLM_BASE_URL",
        os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
    LLM_MODEL: str = os.getenv(
        "LLM_MODEL",
        os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    )
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", os.getenv("OPENROUTER_TIMEOUT", "120")))
    LLM_DISABLE_THINKING: bool = os.getenv("LLM_DISABLE_THINKING", "true").lower() == "true"
    LLM_EXTRA_BODY: dict = json.loads(os.getenv("LLM_EXTRA_BODY", "{}") or "{}")

    # Backwards-compatible names used by the existing code and docs.
    OPENROUTER_API_KEY: str = LLM_API_KEY
    OPENROUTER_BASE_URL: str = LLM_BASE_URL
    OPENROUTER_MODEL: str = LLM_MODEL
    OPENROUTER_TIMEOUT: int = LLM_TIMEOUT
    
    # Tavily
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    TAVILY_MAX_RESULTS: int = int(os.getenv("TAVILY_MAX_RESULTS", "10"))
    TAVILY_SEARCH_DEPTH: str = os.getenv("TAVILY_SEARCH_DEPTH", "advanced")
    
    # SerpApi
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    SERPAPI_MAX_RESULTS: int = int(os.getenv("SERPAPI_MAX_RESULTS", "10"))
    SERPAPI_LOCATION: str = os.getenv("SERPAPI_LOCATION", "")
    SERPAPI_GL: str = os.getenv("SERPAPI_GL", "us")
    SERPAPI_HL: str = os.getenv("SERPAPI_HL", "en")
    
    # Firecrawl
    FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")
    
    # Pipeline
    MAX_RESEARCH_DEPTH: int = int(os.getenv("MAX_RESEARCH_DEPTH", "3"))
    MAX_OSINT_PAGES: int = int(os.getenv("MAX_OSINT_PAGES", "8"))
    MAX_CONTENT_VARIANTS: int = int(os.getenv("MAX_CONTENT_VARIANTS", "3"))
    MAX_VERIFICATION_RETRIES: int = int(os.getenv("MAX_VERIFICATION_RETRIES", "3"))
    ENABLE_AUTO_PUBLISH: bool = os.getenv("ENABLE_AUTO_PUBLISH", "false").lower() == "true"
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Content
    DEFAULT_CALENDAR_DAYS: int = int(os.getenv("DEFAULT_CALENDAR_DAYS", "14"))
    DEFAULT_POSTS_PER_WEEK: int = int(os.getenv("DEFAULT_POSTS_PER_WEEK", "5"))
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate that required settings are configured."""
        errors = []
        is_local_llm = any(host in cls.LLM_BASE_URL for host in ("localhost", "127.0.0.1", "0.0.0.0"))
        if not cls.LLM_API_KEY and not is_local_llm:
            errors.append("LLM_API_KEY or OPENROUTER_API_KEY is required for non-local LLM backends")
        if not cls.TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY is required")
        if not cls.SERPAPI_KEY:
            errors.append("SERPAPI_KEY is required")
        return errors

settings = Settings()
