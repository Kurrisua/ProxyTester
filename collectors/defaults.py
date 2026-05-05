from __future__ import annotations

from pathlib import Path


COLLECTORS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = COLLECTORS_DIR.parent
DATA_DIR = COLLECTORS_DIR / "data"
DEFAULT_LAST_DATA_PATH = DATA_DIR / "lastData.txt"
DEFAULT_LAST_DATA_JSON_PATH = DATA_DIR / "lastData.json"
THIRD_PARTY_DIR = PROJECT_ROOT / "third_party"
DEADPOOL_DIR = THIRD_PARTY_DIR / "Deadpool-proxypool1.5" / "Deadpool-proxypool1.5"
DEADPOOL_FIR_PATH = DEADPOOL_DIR / "fir.py"
DEADPOOL_LAST_DATA_PATH = DEADPOOL_DIR / "lastData.txt"
DEADPOOL_HTTP_PATH = DEADPOOL_DIR / "http.txt"
DEADPOOL_GIT_PATH = DEADPOOL_DIR / "git.txt"
