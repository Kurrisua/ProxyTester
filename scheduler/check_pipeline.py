from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from uuid import uuid4

from core.context.check_context import CheckContext
from core.models.enums import Applicability, ExecutionStatus, RiskLevel, ScanOutcome
from core.models.results import CheckResult, SecurityResult
from core.models.scan_record import SecurityScanBatch, SecurityScanRecord


class CheckPipeline:
    def __init__(self, checkers, security_checkers, scorers, repository=None, scan_repository=None, max_workers: int = 100):
        self.checkers = sorted(checkers, key=lambda item: item.order)
        self.security_checkers = sorted(security_checkers, key=lambda item: item.order)
        self.scorers = scorers
        self.repository = repository
        self.scan_repository = scan_repository
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        self.last_batch_id: str | None = None

    def run_for_proxy(self, proxy, batch_id: str | None = None, runtime: dict | None = None):
        context = CheckContext(proxy=proxy)
        if batch_id:
            context.runtime["batch_id"] = batch_id
        if runtime:
            context.runtime.update(runtime)

        blocked = False
        for checker in self.checkers:
            if not checker.enabled:
                self._record_check_result(context, self._build_skipped_check_result(checker, "checker_disabled"))
                continue
            if blocked:
                self._record_check_result(context, self._build_skipped_check_result(checker, "previous_blocking_checker_failed"))
                continue
            if not checker.supports(context):
                self._record_check_result(context, self._build_not_applicable_check_result(checker))
                continue

            started_at = perf_counter()
            try:
                result = checker.check(context)
                result.latency_ms = result.latency_ms if result.latency_ms is not None else round((perf_counter() - started_at) * 1000, 2)
                self._normalize_result(result)
            except TimeoutError as exc:
                result = self._build_error_check_result(checker, exc, ExecutionStatus.TIMEOUT.value, ScanOutcome.TIMEOUT.value)
            except Exception as exc:
                result = self._build_error_check_result(checker, exc, ExecutionStatus.ERROR.value, ScanOutcome.ERROR.value)

            context.add_check_result(result)
            self._apply_check_result(context, result)
            self._persist_scan_record(context, result)
            if checker.blocking and not result.success:
                blocked = True

        if context.proxy.is_usable:
            for checker in self.security_checkers:
                if not checker.enabled:
                    self._record_security_result(context, self._build_skipped_security_result(checker, "checker_disabled"))
                    continue
                if not checker.supports(context):
                    self._record_security_result(context, self._build_not_applicable_security_result(checker))
                    continue
                try:
                    result = checker.check(context)
                    self._normalize_result(result)
                except TimeoutError as exc:
                    result = self._build_error_security_result(checker, exc, ExecutionStatus.TIMEOUT.value, ScanOutcome.TIMEOUT.value)
                except Exception as exc:
                    result = self._build_error_security_result(checker, exc, ExecutionStatus.ERROR.value, ScanOutcome.ERROR.value)
                self._record_security_result(context, result)
        else:
            for checker in self.security_checkers:
                self._record_security_result(context, self._build_skipped_security_result(checker, "proxy_not_usable"))

        for scorer in self.scorers:
            scorer.score(context)

        return context

    def run_batch(self, proxies):
        contexts = []
        total = len(proxies)
        batch_id = str(uuid4())
        self.last_batch_id = batch_id
        if self.scan_repository:
            self.scan_repository.create_batch(SecurityScanBatch(batch_id=batch_id, target_proxy_count=total))

        started_at = perf_counter()
        self.logger.info("Starting check batch for %s proxies with max_workers=%s", total, self.max_workers)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {executor.submit(self.run_for_proxy, proxy, batch_id): proxy for proxy in proxies}
            for index, future in enumerate(as_completed(future_map), start=1):
                proxy = future_map[future]
                try:
                    contexts.append(future.result())
                except Exception:
                    self.logger.exception("Proxy check failed for %s:%s", proxy.ip, proxy.port)
                    continue
                if index == total or index % 50 == 0:
                    self.logger.info("Completed proxy checks: %s/%s", index, total)

        if self.repository:
            self._persist_contexts(contexts)

        alive_count = sum(1 for context in contexts if context.proxy.is_alive)
        self.logger.info(
            "Finished check batch in %.2fs (contexts=%s alive=%s)",
            perf_counter() - started_at,
            len(contexts),
            alive_count,
        )
        if self.scan_repository:
            self.scan_repository.finish_batch(batch_id, "completed")
        return contexts

    def _persist_contexts(self, contexts) -> None:
        alive_contexts = [context for context in contexts if context.proxy.is_alive]
        self.logger.info("Persisting %s alive proxies to the repository serially", len(alive_contexts))
        for index, context in enumerate(alive_contexts, start=1):
            try:
                self.repository.save_proxy(context.proxy)
            except Exception:
                self.logger.exception("Failed to save proxy %s:%s", context.proxy.ip, context.proxy.port)
            if index == len(alive_contexts) or index % 50 == 0:
                self.logger.info("Persisted proxies: %s/%s", index, len(alive_contexts))

    def _record_check_result(self, context: CheckContext, result: CheckResult) -> None:
        context.add_check_result(result)
        self._persist_scan_record(context, result)

    def _record_security_result(self, context: CheckContext, result: SecurityResult) -> None:
        context.add_security_result(result)
        self._persist_scan_record(context, result)

    def _persist_scan_record(self, context: CheckContext, result) -> None:
        if not self.scan_repository:
            return
        outcome = getattr(result, "outcome", ScanOutcome.NORMAL.value)
        record = SecurityScanRecord(
            batch_id=context.runtime.get("batch_id", "ad-hoc"),
            proxy_ip=context.proxy.ip,
            proxy_port=context.proxy.port,
            stage=getattr(result, "stage", "security"),
            checker_name=result.checker_name,
            funnel_stage=getattr(result, "funnel_stage", 0),
            round_index=int(context.runtime.get("round_index", 1)),
            scan_depth=getattr(result, "scan_depth", "light"),
            applicability=getattr(result, "applicability", Applicability.APPLICABLE.value),
            execution_status=getattr(result, "execution_status", ExecutionStatus.COMPLETED.value),
            outcome=outcome,
            skip_reason=getattr(result, "skip_reason", None),
            precondition_summary=self._precondition_summary(context, result),
            elapsed_ms=getattr(result, "latency_ms", None),
            is_anomalous=outcome == ScanOutcome.ANOMALOUS.value,
            risk_level=getattr(result, "risk_level", RiskLevel.UNKNOWN.value),
            risk_tags=getattr(result, "risk_tags", []),
            evidence=getattr(result, "evidence", {}),
            error_message=getattr(result, "error", None),
        )
        record_id = self.scan_repository.save_scan_record(record)
        self._persist_child_security_artifacts(record_id, record, result)

    def _persist_child_security_artifacts(self, record_id: int | None, record: SecurityScanRecord, result) -> None:
        evidence = getattr(result, "evidence", {}) or {}
        if not isinstance(evidence, dict):
            return

        if self._should_index_evidence(result) and hasattr(self.scan_repository, "save_evidence_file"):
            self.scan_repository.save_evidence_file(
                {
                    "record_id": record_id,
                    "proxy_id": record.proxy_id,
                    "evidence_type": "inline_summary",
                    "storage_path": f"inline://security_scan_records/{record_id}/evidence" if record_id else "inline://security_scan_records/ad-hoc/evidence",
                    "summary": self._evidence_summary(record, result),
                }
            )

        for observation in evidence.get("resourceObservations", []) or []:
            if hasattr(self.scan_repository, "save_resource_observation"):
                payload = dict(observation)
                payload.setdefault("record_id", record_id)
                payload.setdefault("proxy_id", record.proxy_id)
                self.scan_repository.save_resource_observation(payload)

        for observation in evidence.get("certificateObservations", []) or []:
            if hasattr(self.scan_repository, "save_certificate_observation"):
                payload = dict(observation)
                payload.setdefault("record_id", record_id)
                payload.setdefault("proxy_id", record.proxy_id)
                self.scan_repository.save_certificate_observation(payload)

        for event in evidence.get("behaviorEvents", []) or []:
            if hasattr(self.scan_repository, "save_behavior_event"):
                payload = dict(event)
                payload.setdefault("record_id", record_id)
                payload.setdefault("batch_id", record.batch_id)
                payload.setdefault("proxy_id", record.proxy_id)
                self.scan_repository.save_behavior_event(payload)

    @staticmethod
    def _should_index_evidence(result) -> bool:
        evidence = getattr(result, "evidence", None)
        return bool(evidence) and getattr(result, "outcome", None) == ScanOutcome.ANOMALOUS.value

    @staticmethod
    def _evidence_summary(record: SecurityScanRecord, result) -> str:
        tags = ", ".join(getattr(result, "risk_tags", []) or [])
        return f"{record.checker_name} outcome={record.outcome} risk={record.risk_level} tags={tags}".strip()

    @staticmethod
    def _precondition_summary(context: CheckContext, result) -> dict:
        summary = dict(getattr(result, "precondition_summary", {}) or {})
        if "round_index" in context.runtime:
            summary.setdefault("roundIndex", context.runtime["round_index"])
        if "observation_target_url" in context.runtime:
            summary.setdefault("targetUrl", context.runtime["observation_target_url"])
        if context.runtime.get("user_agent"):
            summary.setdefault("userAgent", context.runtime["user_agent"])
        if "observation_step" in context.runtime:
            summary.setdefault("observationStep", context.runtime["observation_step"])
        return summary

    @staticmethod
    def _normalize_result(result) -> None:
        if getattr(result, "execution_status", None) != ExecutionStatus.COMPLETED.value:
            return
        if getattr(result, "error", None):
            result.execution_status = ExecutionStatus.ERROR.value
            result.outcome = ScanOutcome.ERROR.value
        elif getattr(result, "success", False):
            result.outcome = getattr(result, "outcome", ScanOutcome.NORMAL.value) or ScanOutcome.NORMAL.value
        else:
            result.outcome = getattr(result, "outcome", ScanOutcome.ERROR.value) or ScanOutcome.ERROR.value

    @staticmethod
    def _build_not_applicable_check_result(checker) -> CheckResult:
        return CheckResult(
            checker_name=checker.name,
            stage=checker.stage,
            success=False,
            applicability=Applicability.NOT_APPLICABLE.value,
            execution_status=ExecutionStatus.SKIPPED.value,
            outcome=ScanOutcome.NOT_APPLICABLE.value,
            skip_reason="checker_not_supported_for_proxy",
        )

    @staticmethod
    def _build_skipped_check_result(checker, reason: str) -> CheckResult:
        return CheckResult(
            checker_name=checker.name,
            stage=checker.stage,
            success=False,
            execution_status=ExecutionStatus.SKIPPED.value,
            outcome=ScanOutcome.SKIPPED.value,
            skip_reason=reason,
        )

    @staticmethod
    def _build_error_check_result(checker, exc: Exception, status: str, outcome: str) -> CheckResult:
        return CheckResult(
            checker_name=checker.name,
            stage=checker.stage,
            success=False,
            execution_status=status,
            outcome=outcome,
            error=str(exc),
        )

    @staticmethod
    def _build_not_applicable_security_result(checker) -> SecurityResult:
        return SecurityResult(
            checker_name=checker.name,
            success=False,
            stage=getattr(checker, "stage", "security"),
            applicability=Applicability.NOT_APPLICABLE.value,
            execution_status=ExecutionStatus.SKIPPED.value,
            outcome=ScanOutcome.NOT_APPLICABLE.value,
            skip_reason="checker_not_supported_for_proxy",
            funnel_stage=getattr(checker, "funnel_stage", 0),
            scan_depth=getattr(checker, "scan_depth", "light"),
        )

    @staticmethod
    def _build_skipped_security_result(checker, reason: str) -> SecurityResult:
        return SecurityResult(
            checker_name=checker.name,
            success=False,
            stage=getattr(checker, "stage", "security"),
            execution_status=ExecutionStatus.SKIPPED.value,
            outcome=ScanOutcome.SKIPPED.value,
            skip_reason=reason,
            funnel_stage=getattr(checker, "funnel_stage", 0),
            scan_depth=getattr(checker, "scan_depth", "light"),
        )

    @staticmethod
    def _build_error_security_result(checker, exc: Exception, status: str, outcome: str) -> SecurityResult:
        return SecurityResult(
            checker_name=checker.name,
            success=False,
            stage=getattr(checker, "stage", "security"),
            execution_status=status,
            outcome=outcome,
            error=str(exc),
            funnel_stage=getattr(checker, "funnel_stage", 0),
            scan_depth=getattr(checker, "scan_depth", "light"),
        )

    def _apply_check_result(self, context: CheckContext, result) -> None:
        proxy = context.proxy
        if result.checker_name == "tcp_checker":
            if result.success:
                proxy.is_alive = True
            else:
                proxy.record_fail()
                proxy.is_alive = False
            proxy.update_check_time()
            return

        if result.checker_name == "socks5_checker":
            proxy.socks5 = bool(result.metadata.get("socks5"))
        elif result.checker_name == "https_checker":
            proxy.https = bool(result.metadata.get("https"))
        elif result.checker_name == "http_checker":
            proxy.http = bool(result.metadata.get("http"))
            proxy.response_time = result.latency_ms or proxy.response_time
        elif result.checker_name == "protocol_aggregator":
            proxy.http = bool(result.metadata.get("http"))
            proxy.https = bool(result.metadata.get("https"))
            proxy.socks5 = bool(result.metadata.get("socks5"))
            proxy.update_proxy_type()
            if proxy.proxy_type:
                proxy.record_success()
            else:
                proxy.is_alive = False
                proxy.record_fail()
        elif result.checker_name == "anonymity_checker" and result.success:
            proxy.anonymity = result.metadata.get("anonymity")
            proxy.response_time = result.latency_ms or proxy.response_time
        elif result.checker_name in {"exit_geo_checker", "ip_geo_fallback_checker"} and result.success:
            proxy.geo_source = result.metadata.get("geo_source")
            proxy.exit_ip = result.metadata.get("exit_ip", proxy.exit_ip)
            proxy.country = result.metadata.get("country")
            proxy.city = result.metadata.get("city")
            proxy.isp = result.metadata.get("isp")
        elif result.checker_name == "business_availability_checker":
            proxy.business_score = int(result.metadata.get("business_score", 0))
