"""
Utility functions for Lamy bot.
Includes logging setup and other helper functions.
"""

import logging
import colorlog
from datetime import datetime
import os
from pathlib import Path


def setup_logging(log_level: str = "INFO") -> None:
    """
    Set up colored logging for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Set up colored console handler
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
    )
    
    # Set up file handler
    file_handler = logging.FileHandler(
        log_dir / f"lamy_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set specific loggers
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at {log_level} level")


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.
    
    Returns:
        True if all required variables are set, False otherwise
    """
    required_vars = [
        "DISCORD_TOKEN",
        "OPENAI_API_KEY",
        "DEVELOPER_ID",
        "CREATOR_NAME",
        "PINECONE_API_KEY",
        "PINECONE_INDEX_NAME"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
            
    if missing_vars:
        logger = logging.getLogger(__name__)
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
        
    return True


def format_timestamp(timestamp: datetime) -> str:
    """
    Format a timestamp for display.
    
    Args:
        timestamp: The datetime to format
        
    Returns:
        Formatted timestamp string
    """
    return timestamp.strftime("%Y년 %m월 %d일 %H시 %M분")


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text to a maximum length with ellipsis.
    
    Args:
        text: The text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def clean_content(content: str) -> str:
    """
    Clean message content by removing excess whitespace and formatting.
    
    Args:
        content: The content to clean
        
    Returns:
        Cleaned content
    """
    # Remove multiple spaces
    content = ' '.join(content.split())
    
    # Remove leading/trailing whitespace
    content = content.strip()
    
    return content


def get_data_path(filename: str) -> Path:
    """
    Get the full path for a data file.
    
    Args:
        filename: The filename
        
    Returns:
        Full path to the file in the data directory
    """
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    return data_dir / filename 