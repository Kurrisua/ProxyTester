from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SecurityResourceObservation:
    resource_url: str
    resource_type: str | None = None
    record_id: int | None = None
    proxy_id: int | None = None
    direct_status_code: int | None = None
    proxy_status_code: int | None = None
    direct_sha256: str | None = None
    proxy_sha256: str | None = None
    direct_size: int | None = None
    proxy_size: int | None = None
    direct_mime_type: str | None = None
    proxy_mime_type: str | None = None
    is_modified: bool = False
    failure_type: str | None = None
    risk_level: str = "unknown"
    summary: dict[str, Any] = field(default_factory=dict)
    observed_at: datetime = field(default_factory=datetime.now)
