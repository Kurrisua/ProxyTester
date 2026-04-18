from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AccessResult:
    success: bool
    mode: str
    target_url: str
    final_url: str | None = None
    status_code: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    body_text: str | None = None
    body_bytes_sha256: str | None = None
    body_size: int | None = None
    mime_type: str | None = None
    elapsed_ms: float | None = None
    redirect_chain: list[dict] = field(default_factory=list)
    certificate_summary: dict | None = None
    error_type: str | None = None
    error_message: str | None = None
