"""Shared logging helpers for AlertZarr services."""

from __future__ import annotations

import logging
from pythonjsonlogger import jsonlogger


def configure_logging(level: int = logging.INFO) -> None:
    """Configure JSON logging for CLI utilities."""
    formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[handler], force=True)

```