"""Enterprise logging configuration."""
import logging
import sys
from pathlib import Path
from rich.logging import RichHandler
from config.settings import settings

def setup_logger(name: str = "marketing_agent") -> logging.Logger:
    """Configure structured logging with Rich."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Console handler with Rich
    console_handler = RichHandler(rich_tracebacks=True, markup=True)
    console_handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        "%(name)s | %(message)s",
        datefmt="[%X]"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for persistence
    log_dir = settings.OUTPUT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "agent.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logger()
