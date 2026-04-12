from __future__ import annotations

import logging
import os
from pathlib import Path


def configure_logging(log_level: str | None = None) -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    resolved_level = (log_level or os.getenv("PROXYTESTER_LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, resolved_level, logging.INFO)

    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "proxytester.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.setLevel(level)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
