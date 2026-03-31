"""
Logging configuration for RAG application
"""

import logging
import logging.handlers
from pathlib import Path
from config.settings import get_settings

settings = get_settings()


def setup_logging():
    """Configure logging for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Define log format
    log_format = logging.Formatter(
        settings.LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # File handler (all logs)
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)
    
    # Console handler (warnings and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # Suppress verbose logs from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("faiss").setLevel(logging.WARNING)
    
    root_logger.info(f"Logging initialized - Level: {settings.LOG_LEVEL}")


def get_logger(name: str) -> logging.Logger:
    """Get logger by name (usually __name__)"""
    return logging.getLogger(name)
