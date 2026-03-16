from __future__ import annotations

from pathlib import Path


COLLECTORS_DIR = Path(__file__).resolve().parent
DATA_DIR = COLLECTORS_DIR / "data"
DEFAULT_LAST_DATA_PATH = DATA_DIR / "lastData.txt"
DEFAULT_LAST_DATA_JSON_PATH = DATA_DIR / "lastData.json"
