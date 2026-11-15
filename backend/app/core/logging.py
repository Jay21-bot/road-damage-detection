"""
Logging Configuration Module
Provides uniform, formatted logging across API, video ingestion, and AI pipelines.
"""

import logging
import sys
from typing import Optional


def setup_logger(name: str = "road_ai", level: Optional[str] = None) -> logging.Logger:
    """Configures and returns a standardized logger."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
        logger.setLevel(log_level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logger()
