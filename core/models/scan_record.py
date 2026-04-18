from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SecurityScanBatch:
    batch_id: str
    status: str = "running"
    scan_mode: str = "base_pipeline"
    scan_policy: str = "phase0_recording"
    max_scan_depth: str = "light"
    target_proxy_count: int = 0
    checked_proxy_count: int = 0
    skipped_proxy_count: int = 0
    error_proxy_count: int = 0
    parameters: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    error_message: str | None = None


@dataclass
class SecurityScanRecord:
    batch_id: str
    proxy_ip: str
    proxy_port: int
    stage: str
    checker_name: str
    proxy_id: int | None = None
    round_index: int = 1
    funnel_stage: int = 0
    scan_depth: str = "light"
    applicability: str = "applicable"
    execution_status: str = "completed"
    outcome: str = "normal"
    skip_reason: str | None = None
    precondition_summary: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float | None = None
    is_anomalous: bool = False
    risk_level: str = "unknown"
    risk_tags: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
