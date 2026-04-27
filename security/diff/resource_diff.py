from __future__ import annotations

from dataclasses import asdict, dataclass

from core.models.enums import RiskLevel
from security.access.models import AccessResult


@dataclass
class ResourceDiff:
    resource_url: str
    resource_type: str
    direct_status_code: int | None
    proxy_status_code: int | None
    direct_sha256: str | None
    proxy_sha256: str | None
    direct_size: int | None
    proxy_size: int | None
    direct_mime_type: str | None
    proxy_mime_type: str | None
    is_modified: bool
    failure_type: str | None
    risk_level: str
    risk_tags: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def compare_resource_results(resource_type: str, direct: AccessResult, proxied: AccessResult) -> ResourceDiff:
    failure_type = None
    risk_tags: list[str] = []

    if not direct.success:
        failure_type = f"direct_{direct.error_type or 'fetch_failed'}"
        return _diff(resource_type, direct, proxied, False, failure_type, RiskLevel.UNKNOWN.value, ["resource_baseline_failed"])

    if not proxied.success:
        failure_type = f"proxy_{proxied.error_type or 'fetch_failed'}"
        return _diff(resource_type, direct, proxied, False, failure_type, RiskLevel.UNKNOWN.value, ["resource_fetch_failed"])

    if direct.status_code != proxied.status_code:
        failure_type = "status_code_changed"
        risk_tags.append("resource_status_changed")

    mime_changed = _normalize_mime(direct.mime_type) != _normalize_mime(proxied.mime_type)
    hash_changed = direct.body_bytes_sha256 != proxied.body_bytes_sha256
    size_changed = direct.body_size != proxied.body_size

    if mime_changed:
        risk_tags.append("mime_type_mismatch")
    if hash_changed:
        risk_tags.append(_resource_replacement_tag(resource_type))
    elif size_changed:
        risk_tags.append("resource_size_changed")

    is_modified = bool(risk_tags and not failure_type) or bool(hash_changed or mime_changed)
    risk_level = _risk_level(resource_type, hash_changed, mime_changed, failure_type)
    return _diff(resource_type, direct, proxied, is_modified, failure_type, risk_level, risk_tags)


def _diff(
    resource_type: str,
    direct: AccessResult,
    proxied: AccessResult,
    is_modified: bool,
    failure_type: str | None,
    risk_level: str,
    risk_tags: list[str],
) -> ResourceDiff:
    return ResourceDiff(
        resource_url=direct.target_url,
        resource_type=resource_type,
        direct_status_code=direct.status_code,
        proxy_status_code=proxied.status_code,
        direct_sha256=direct.body_bytes_sha256,
        proxy_sha256=proxied.body_bytes_sha256,
        direct_size=direct.body_size,
        proxy_size=proxied.body_size,
        direct_mime_type=direct.mime_type,
        proxy_mime_type=proxied.mime_type,
        is_modified=is_modified,
        failure_type=failure_type,
        risk_level=risk_level,
        risk_tags=risk_tags,
    )


def _normalize_mime(value: str | None) -> str | None:
    if value is None:
        return None
    return value.split(";", 1)[0].strip().lower()


def _resource_replacement_tag(resource_type: str) -> str:
    if resource_type == "javascript":
        return "script_modified"
    if resource_type == "css":
        return "css_modified"
    if resource_type in {"image", "text"}:
        return "file_replaced"
    return "resource_replacement"


def _risk_level(resource_type: str, hash_changed: bool, mime_changed: bool, failure_type: str | None) -> str:
    if failure_type:
        return RiskLevel.UNKNOWN.value
    if hash_changed and resource_type == "javascript":
        return RiskLevel.HIGH.value
    if hash_changed:
        return RiskLevel.MEDIUM.value
    if mime_changed:
        return RiskLevel.MEDIUM.value
    return RiskLevel.LOW.value
