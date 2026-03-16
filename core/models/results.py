from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    checker_name: str
    stage: str
    success: bool
    latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class SecurityResult:
    checker_name: str
    success: bool
    risk_level: str = "low"
    risk_tags: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ScoreResult:
    scorer_name: str
    score: int
    breakdown: dict[str, Any] = field(default_factory=dict)
