from __future__ import annotations

from dataclasses import dataclass, field

from core.models.enums import RiskLevel
from security.access.cert_probe import CertificateProbeResult


@dataclass
class CertificateDiff:
    direct_success: bool
    proxy_success: bool
    is_mismatch: bool = False
    risk_level: str = RiskLevel.UNKNOWN.value
    risk_tags: list[str] = field(default_factory=list)
    failure_type: str | None = None

    def to_dict(self) -> dict:
        return {
            "directSuccess": self.direct_success,
            "proxySuccess": self.proxy_success,
            "isMismatch": self.is_mismatch,
            "riskLevel": self.risk_level,
            "riskTags": self.risk_tags,
            "failureType": self.failure_type,
        }


def compare_certificate_results(direct: CertificateProbeResult, proxied: CertificateProbeResult) -> CertificateDiff:
    if not direct.success:
        return CertificateDiff(
            direct_success=False,
            proxy_success=proxied.success,
            failure_type=f"direct_{direct.error_type or 'error'}",
            risk_tags=["tls_baseline_failed"],
        )

    if not proxied.success:
        return CertificateDiff(
            direct_success=True,
            proxy_success=False,
            failure_type=f"proxy_{proxied.error_type or 'error'}",
            risk_tags=["tls_proxy_failed"],
        )

    tags: list[str] = []
    is_mismatch = direct.fingerprint_sha256 != proxied.fingerprint_sha256
    if is_mismatch:
        tags.extend(["cert_mismatch", "mitm_suspected"])
    if proxied.is_self_signed:
        tags.extend(["self_signed_cert", "mitm_suspected"])
    if proxied.issuer and "unknown" in proxied.issuer.lower():
        tags.extend(["unknown_issuer", "mitm_suspected"])

    tags = sorted(set(tags))
    risk_level = RiskLevel.HIGH.value if "mitm_suspected" in tags else RiskLevel.LOW.value
    return CertificateDiff(
        direct_success=True,
        proxy_success=True,
        is_mismatch=is_mismatch,
        risk_level=risk_level,
        risk_tags=tags,
    )
