"""Logging configuration using Loguru with module-specific filtering."""

import logging
import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """Configure Loguru with module-specific log levels.

    This allows you to set a global log level (e.g., WARNING) while
    enabling DEBUG logging for specific modules like evidence_seeker.
    """
    # Remove default handler
    logger.remove()

    # Get module-specific log levels
    module_levels = settings.get_module_log_levels()
    global_level = settings.log_level.upper()

    # Configure standard Python logging (for libraries like SQLAlchemy)
    # Set root logger to WARNING to suppress noisy libraries
    logging.basicConfig(level=logging.WARNING)

    # Suppress specific noisy loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("passlib").setLevel(logging.ERROR)

    # If user specifically wants DEBUG for certain modules, enable them
    for module_prefix, level in module_levels.items():
        if module_prefix.startswith("sqlalchemy"):
            logging.getLogger(module_prefix).setLevel(getattr(logging, level))

    # Add custom filter function
    def log_filter(record: dict) -> bool:
        """Filter logs based on module-specific or global log level.

        Args:
            record: Loguru log record containing module name and level

        Returns:
            True if the log should be emitted, False otherwise
        """
        module_name = record["name"]
        log_level = record["level"].name

        # Check if there's a specific level for this module or its parent
        for module_prefix, required_level in module_levels.items():
            if module_name.startswith(module_prefix):
                # This module has a specific log level
                return _should_log(log_level, required_level)

        # Fall back to global level
        return _should_log(log_level, global_level)

    # Add handler with our custom filter
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="TRACE",  # Let all messages through, filter handles actual level
        filter=log_filter,
        colorize=True,
    )

    # Intercept standard library logging and redirect to loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Set up interception for standard library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Log the configuration for debugging
    logger.info(f"Logging configured: global_level={global_level}")
    if module_levels:
        logger.info(f"Module-specific levels: {module_levels}")


def _should_log(log_level: str, required_level: str) -> bool:
    """Check if a log should be emitted based on its level.

    Args:
        log_level: The level of the log message (e.g., "DEBUG", "INFO")
        required_level: The minimum required level (e.g., "WARNING")

    Returns:
        True if log_level >= required_level in severity
    """
    level_hierarchy = {
        "TRACE": 0,
        "DEBUG": 1,
        "INFO": 2,
        "SUCCESS": 2,
        "WARNING": 3,
        "ERROR": 4,
        "CRITICAL": 5,
    }

    return level_hierarchy.get(log_level, 0) >= level_hierarchy.get(required_level, 0)
