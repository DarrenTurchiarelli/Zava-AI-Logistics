"""
Logging Configuration for Zava Logistics

Centralized logging setup with structured output for production environments.
Replaces scattered print() and debug_print() calls with proper logging.
"""

import logging
import os
import sys
from typing import Any, Dict, Optional


def setup_logging(app_name: str = "zava", log_level: Optional[str] = None) -> logging.Logger:
    """
    Configure application logging with console and optional file output
    
    Args:
        app_name: Name of the application/module
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Defaults to DEBUG if DEBUG_MODE=true, else INFO
    
    Returns:
        Configured logger instance
        
    Example:
        logger = setup_logging("zava.routes")
        logger.info("Route accessed", extra={"user": "admin", "path": "/parcels"})
    """
    # Determine log level from environment or parameter
    if log_level is None:
        debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        log_level = "DEBUG" if debug_mode else "INFO"
    
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Format: [2026-04-03 14:30:45] INFO - zava.routes - User login successful
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, context: Optional[Dict[str, Any]] = None):
    """
    Log message with structured context data
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        context: Dictionary of contextual data (user, tracking_number, etc.)
        
    Example:
        log_with_context(logger, "info", "Parcel registered", {
            "tracking_number": "DT123456",
            "user": "admin",
            "weight_kg": 1.5
        })
    """
    log_method = getattr(logger, level.lower())
    if context:
        log_method(message, extra=context)
    else:
        log_method(message)


# Global logger for application
app_logger = setup_logging("zava")
