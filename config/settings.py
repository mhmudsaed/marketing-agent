"""Enterprise configuration management."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Centralized application settings."""
    
    # OpenRouter
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    OPENROUTER_TIMEOUT: int = 120
    
    # Tavily
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    TAVILY_MAX_RESULTS: int = int(os.getenv("TAVILY_MAX_RESULTS", "10"))
    
    # Firecrawl
    FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")
    
    # Pipeline
    MAX_RESEARCH_DEPTH: int = int(os.getenv("MAX_RESEARCH_DEPTH", "3"))
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
        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY is required")
        if not cls.TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY is required")
        return errors

settings = Settings()
