from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.models.enums import Applicability, ExecutionStatus, RiskLevel, ScanOutcome


@dataclass
class CheckResult:
    checker_name: str
    stage: str
    success: bool
    latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    applicability: str = Applicability.APPLICABLE.value
    execution_status: str = ExecutionStatus.COMPLETED.value
    outcome: str = ScanOutcome.NORMAL.value
    skip_reason: str | None = None
    funnel_stage: int = 0
    scan_depth: str = "light"
    precondition_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityResult:
    checker_name: str
    success: bool
    risk_level: str = RiskLevel.UNKNOWN.value
    risk_tags: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    stage: str = "security"
    applicability: str = Applicability.APPLICABLE.value
    execution_status: str = ExecutionStatus.COMPLETED.value
    outcome: str = ScanOutcome.NORMAL.value
    skip_reason: str | None = None
    funnel_stage: int = 0
    scan_depth: str = "light"
    precondition_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoreResult:
    scorer_name: str
    score: int
    breakdown: dict[str, Any] = field(default_factory=dict)
