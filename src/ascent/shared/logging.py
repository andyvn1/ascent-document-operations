"""Structured logging setup.

Configures the standard library's logging module once, at startup, so
every module can just call logging.getLogger(__name__) and get
consistent, structured output — no per-module logging configuration.
"""

import logging
import sys

from ascent.shared.config import Settings


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )