"""Structured logging configuration using structlog."""

import sys
from typing import Any, Dict
import structlog
from structlog.stdlib import LoggerFactory
from structlog.typing import Processor

# Remove immediate settings import
_configured = False


def configure_logging():
    """Configure structured logging for the application."""
    global _configured
    if _configured:
        return
        
    try:
        # Import settings only when needed
        from ..config import settings
        log_format = settings.log_format
    except:
        # Fallback if settings unavailable
        log_format = "console"
    
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add JSON formatter for production
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    try:
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=LoggerFactory(),
            context_class=dict,
            cache_logger_on_first_use=True,
        )
        _configured = True
    except Exception as e:
        # Fallback to basic logging if structlog fails
        import logging
        logging.basicConfig(level=logging.INFO)
        _configured = True


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    if not _configured:
        configure_logging()
    
    try:
        return structlog.get_logger(name)
    except:
        # Fallback to standard logger if structlog fails
        import logging
        return logging.getLogger(name)

# DO NOT configure on import - wait for first use 