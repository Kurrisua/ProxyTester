from __future__ import annotations

from enum import Enum


class StableStrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Applicability(StableStrEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ExecutionStatus(StableStrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


class RiskLevel(StableStrEnum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BehaviorClass(StableStrEnum):
    NORMAL = "normal"
    CONTENT_TAMPERING = "content_tampering"
    AD_INJECTION = "ad_injection"
    SCRIPT_INJECTION = "script_injection"
    REDIRECT_MANIPULATION = "redirect_manipulation"
    RESOURCE_REPLACEMENT = "resource_replacement"
    MITM_SUSPECTED = "mitm_suspected"
    STEALTHY_MALICIOUS = "stealthy_malicious"
    UNSTABLE_BUT_NON_MALICIOUS = "unstable_but_non_malicious"


class ScanOutcome(StableStrEnum):
    NORMAL = "normal"
    ANOMALOUS = "anomalous"
    NOT_APPLICABLE = "not_applicable"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"
