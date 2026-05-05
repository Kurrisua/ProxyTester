from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from core.context.check_context import CheckContext
from core.models.enums import Applicability, ExecutionStatus, ScanOutcome


SCAN_DEPTH_ORDER = {
    "light": 10,
    "standard": 20,
    "deep": 30,
    "multi_round": 40,
    "browser": 50,
}


@dataclass(frozen=True)
class ScanPolicy:
    name: str = "default"
    max_scan_depth: str = "standard"
    allowed_cost_levels: frozenset[str] = frozenset({"low", "medium"})
    enabled_checkers: frozenset[str] | None = None
    disabled_checkers: frozenset[str] = frozenset()
    config_aliases: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "HONEYPOT_BASE_URL": ("honeypot_url",),
            "MITM_TARGET_URL": ("mitm_target_url", "honeypot_https_url"),
            "HONEYPOT_HTTPS_URL": ("honeypot_https_url", "mitm_target_url"),
        }
    )

    @classmethod
    def from_runtime(cls, runtime: dict[str, Any] | None) -> "ScanPolicy":
        runtime = runtime or {}
        raw_policy = runtime.get("scan_policy")
        if isinstance(raw_policy, ScanPolicy):
            return raw_policy
        if isinstance(raw_policy, dict):
            return cls(
                name=str(raw_policy.get("name", raw_policy.get("scanPolicy", "runtime"))),
                max_scan_depth=str(raw_policy.get("max_scan_depth", raw_policy.get("maxScanDepth", runtime.get("max_scan_depth", "standard")))),
                allowed_cost_levels=frozenset(raw_policy.get("allowed_cost_levels", raw_policy.get("allowedCostLevels", ["low", "medium"]))),
                enabled_checkers=_optional_frozenset(raw_policy.get("enabled_checkers", raw_policy.get("enabledCheckers"))),
                disabled_checkers=frozenset(raw_policy.get("disabled_checkers", raw_policy.get("disabledCheckers", []))),
            )
        return cls(
            name=str(runtime.get("scan_policy_name", "default")),
            max_scan_depth=str(runtime.get("max_scan_depth", runtime.get("maxScanDepth", "standard"))),
            allowed_cost_levels=frozenset(runtime.get("allowed_cost_levels", runtime.get("allowedCostLevels", ["low", "medium"]))),
            enabled_checkers=_optional_frozenset(runtime.get("enabled_checkers", runtime.get("enabledCheckers"))),
            disabled_checkers=frozenset(runtime.get("disabled_checkers", runtime.get("disabledCheckers", []))),
        )

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "maxScanDepth": self.max_scan_depth,
            "allowedCostLevels": sorted(self.allowed_cost_levels),
            "enabledCheckers": sorted(self.enabled_checkers) if self.enabled_checkers is not None else None,
            "disabledCheckers": sorted(self.disabled_checkers),
        }


@dataclass(frozen=True)
class PolicyDecision:
    should_run: bool
    applicability: str = Applicability.APPLICABLE.value
    execution_status: str = ExecutionStatus.COMPLETED.value
    outcome: str = ScanOutcome.NORMAL.value
    reason: str | None = None
    precondition_summary: dict[str, Any] = field(default_factory=dict)


class CapabilityRouter:
    def decide(self, checker, context: CheckContext, policy: ScanPolicy | None = None) -> PolicyDecision:
        policy = policy or ScanPolicy.from_runtime(context.runtime)
        metadata = checker_metadata(checker)
        summary = {
            "policy": policy.describe(),
            "checker": metadata,
        }

        if not metadata["enabled"]:
            return _skip("checker_disabled", summary)
        if checker.name in policy.disabled_checkers:
            return _skip("disabled_by_scan_policy", summary)
        if policy.enabled_checkers is not None and checker.name not in policy.enabled_checkers:
            return _skip("not_selected_by_scan_policy", summary)
        if _depth_value(metadata["scanDepth"]) > _depth_value(policy.max_scan_depth):
            return _skip("scan_depth_limited_by_policy", summary)
        if metadata["costLevel"] not in policy.allowed_cost_levels:
            return _skip("cost_level_limited_by_policy", summary)

        missing_capability = _missing_capability(metadata["requiredCapabilities"], context)
        if missing_capability:
            return PolicyDecision(
                should_run=False,
                applicability=Applicability.NOT_APPLICABLE.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.NOT_APPLICABLE.value,
                reason=f"missing_capability:{missing_capability}",
                precondition_summary=summary,
            )

        missing_config = _missing_config(metadata["requiredConfig"], context, policy)
        if missing_config:
            return _skip(f"missing_config:{missing_config}", summary)

        missing_result = _missing_result(metadata["requiredResults"], context)
        if missing_result:
            return _skip(f"missing_required_result:{missing_result}", summary)

        if not checker.supports(context):
            return PolicyDecision(
                should_run=False,
                applicability=Applicability.NOT_APPLICABLE.value,
                execution_status=ExecutionStatus.SKIPPED.value,
                outcome=ScanOutcome.NOT_APPLICABLE.value,
                reason="checker_not_supported_for_proxy",
                precondition_summary=summary,
            )

        return PolicyDecision(should_run=True, precondition_summary=summary)


def checker_metadata(checker) -> dict[str, Any]:
    return {
        "name": getattr(checker, "name", checker.__class__.__name__),
        "stage": getattr(checker, "stage", "security"),
        "order": getattr(checker, "order", 100),
        "enabled": bool(getattr(checker, "enabled", True)),
        "funnelStage": getattr(checker, "funnel_stage", 0),
        "scanDepth": getattr(checker, "scan_depth", "light"),
        "costLevel": getattr(checker, "cost_level", "low"),
        "requiredCapabilities": list(getattr(checker, "required_capabilities", ()) or ()),
        "requiredConfig": list(getattr(checker, "required_config", ()) or ()),
        "requiredResults": list(getattr(checker, "required_results", ()) or ()),
        "producesEvents": list(getattr(checker, "produces_events", ()) or ()),
        "description": getattr(checker, "description", ""),
    }


def validate_security_checker(checker) -> list[str]:
    errors: list[str] = []
    metadata = checker_metadata(checker)
    required_text_fields = ("name", "stage", "scanDepth", "costLevel")
    for field_name in required_text_fields:
        if not metadata.get(field_name):
            errors.append(f"{checker.__class__.__name__}.{field_name} is required")
    if metadata["scanDepth"] not in SCAN_DEPTH_ORDER:
        errors.append(f"{checker.name}.scan_depth must be one of {sorted(SCAN_DEPTH_ORDER)}")
    if metadata["costLevel"] not in {"low", "medium", "high"}:
        errors.append(f"{checker.name}.cost_level must be low, medium, or high")
    if not isinstance(getattr(checker, "required_capabilities", ()), tuple):
        errors.append(f"{checker.name}.required_capabilities must be a tuple")
    if not isinstance(getattr(checker, "required_config", ()), tuple):
        errors.append(f"{checker.name}.required_config must be a tuple")
    return errors


def _optional_frozenset(value) -> frozenset[str] | None:
    if value is None:
        return None
    return frozenset(value)


def _skip(reason: str, summary: dict[str, Any]) -> PolicyDecision:
    return PolicyDecision(
        should_run=False,
        execution_status=ExecutionStatus.SKIPPED.value,
        outcome=ScanOutcome.SKIPPED.value,
        reason=reason,
        precondition_summary=summary,
    )


def _depth_value(depth: str) -> int:
    return SCAN_DEPTH_ORDER.get(depth, SCAN_DEPTH_ORDER["browser"] + 1)


def _missing_capability(required: list[str], context: CheckContext) -> str | None:
    for capability in required:
        if capability == "usable" and not context.proxy.is_usable:
            return capability
        if capability == "http" and not context.proxy.http:
            return capability
        if capability == "https" and not context.proxy.https:
            return capability
        if capability == "web" and not (context.proxy.http or context.proxy.https):
            return capability
        if capability == "socks5" and not context.proxy.socks5:
            return capability
        if capability == "tls_proxy" and not (context.proxy.https or context.proxy.socks5):
            return capability
    return None


def _missing_config(required: list[str], context: CheckContext, policy: ScanPolicy) -> str | None:
    for config_name in required:
        runtime_keys = policy.config_aliases.get(config_name, ())
        has_runtime_value = any(context.runtime.get(key) for key in runtime_keys)
        if not has_runtime_value and not os.getenv(config_name):
            return config_name
    return None


def _missing_result(required: list[str], context: CheckContext) -> str | None:
    completed = {
        result.checker_name
        for result in context.security_results
        if result.execution_status == ExecutionStatus.COMPLETED.value
    }
    for checker_name in required:
        if checker_name not in completed:
            return checker_name
    return None
