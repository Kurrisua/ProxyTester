from __future__ import annotations

from dataclasses import dataclass, field
from time import sleep
from typing import Any
from uuid import uuid4

from core.models.scan_record import SecurityScanBatch


@dataclass
class DynamicObservationStep:
    round_index: int
    target_url: str
    user_agent: str | None = None
    wait_seconds: float = 0
    runtime: dict[str, Any] = field(default_factory=dict)

    def to_runtime(self) -> dict[str, Any]:
        return {
            **self.runtime,
            "round_index": self.round_index,
            "honeypot_url": self.target_url,
            "observation_target_url": self.target_url,
            "user_agent": self.user_agent,
            "observation_step": self.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "roundIndex": self.round_index,
            "targetUrl": self.target_url,
            "userAgent": self.user_agent,
            "waitSeconds": self.wait_seconds,
            "runtime": self.runtime,
        }


@dataclass
class DynamicObservationPlan:
    steps: list[DynamicObservationStep]
    scan_policy: str = "dynamic_observation"
    max_scan_depth: str = "multi_round"
    sample_reason: str = "manual_or_suspicious_proxy"
    parameters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_targets(
        cls,
        targets: list[str],
        *,
        user_agents: list[str] | None = None,
        wait_seconds: float = 0,
        parameters: dict[str, Any] | None = None,
    ) -> "DynamicObservationPlan":
        user_agents = user_agents or [None]
        steps: list[DynamicObservationStep] = []
        round_index = 1
        for target in targets:
            for user_agent in user_agents:
                steps.append(DynamicObservationStep(round_index, target, user_agent=user_agent, wait_seconds=wait_seconds))
                round_index += 1
        return cls(steps=steps, parameters=parameters or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanPolicy": self.scan_policy,
            "maxScanDepth": self.max_scan_depth,
            "sampleReason": self.sample_reason,
            "roundCount": len(self.steps),
            "steps": [step.to_dict() for step in self.steps],
            "parameters": self.parameters,
        }


class DynamicObservationRunner:
    """Runs a bounded, synchronous multi-round observation using the existing pipeline."""

    def __init__(self, pipeline, scan_repository=None) -> None:
        self.pipeline = pipeline
        self.scan_repository = scan_repository or getattr(pipeline, "scan_repository", None)

    def run_for_proxy(self, proxy, plan: DynamicObservationPlan) -> list:
        batch_id = str(uuid4())
        if self.scan_repository:
            self.scan_repository.create_batch(
                SecurityScanBatch(
                    batch_id=batch_id,
                    scan_mode="dynamic_observation",
                    scan_policy=plan.scan_policy,
                    max_scan_depth=plan.max_scan_depth,
                    target_proxy_count=1,
                    parameters=plan.to_dict(),
                )
            )

        contexts = []
        try:
            for step in plan.steps:
                if step.wait_seconds > 0:
                    sleep(step.wait_seconds)
                contexts.append(self.pipeline.run_for_proxy(proxy, batch_id=batch_id, runtime=step.to_runtime()))
        except Exception as exc:
            if self.scan_repository:
                self.scan_repository.finish_batch(batch_id, "error", str(exc))
            raise

        if self.scan_repository:
            self.scan_repository.finish_batch(batch_id, "completed")
        return contexts
