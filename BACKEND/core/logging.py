"""
core/logging.py — LawAgent AI Standart Loglama
==============================================
"""

import logging
import sys

def setup_logger(name: str = "LawAgent", level: int = logging.INFO) -> logging.Logger:
    """Tüm modüllerde tutarlı formatlanmış logger sağlar."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger

log = setup_logger("LawAgent")
