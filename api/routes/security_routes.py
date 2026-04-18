from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.proxy_check_service import ProxyCheckService
from services.proxy_query_service import ProxyQueryService
from services.security_query_service import SecurityQueryService
from storage.mysql.proxy_repository import MySQLProxyRepository
from honeypot.manifest import list_targets

security_bp = Blueprint("security", __name__)


@security_bp.route("/api/security/overview", methods=["GET"])
def get_security_overview():
    service = SecurityQueryService()
    try:
        return jsonify(service.get_overview())
    finally:
        service.close()


@security_bp.route("/api/security/proxies", methods=["GET"])
def list_security_proxies():
    service = ProxyQueryService()
    try:
        filters = {
            "country": request.args.get("country"),
            "proxy_type": request.args.get("type"),
            "status": request.args.get("status"),
            "min_business_score": request.args.get("min_business_score", type=int),
            "security_risk": request.args.get("securityRisk") or request.args.get("riskLevel"),
            "behavior_class": request.args.get("behaviorClass"),
            "risk_tag": request.args.get("riskTag") or request.args.get("eventType"),
        }
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=20, type=int)
        sort = request.args.get("sort", default="last_check_time", type=str)
        data, total = service.list_proxies(filters=filters, page=page, limit=limit, sort=sort)
        return jsonify({"data": data, "total": total, "page": page, "limit": limit})
    finally:
        service.close()


@security_bp.route("/api/security/proxies/<ip>:<port>", methods=["GET"])
def get_security_proxy_detail(ip: str, port: str):
    service = SecurityQueryService()
    try:
        return jsonify(service.get_proxy_security_detail(ip, int(port)))
    finally:
        service.close()


@security_bp.route("/api/security/proxies/<ip>:<port>/history", methods=["GET"])
def get_security_proxy_history(ip: str, port: str):
    service = SecurityQueryService()
    try:
        limit = request.args.get("limit", default=80, type=int)
        return jsonify({"data": service.get_proxy_security_history(ip, int(port), limit=limit)})
    finally:
        service.close()


@security_bp.route("/api/security/proxies/<ip>:<port>/events", methods=["GET"])
def get_security_proxy_events(ip: str, port: str):
    service = SecurityQueryService()
    try:
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=20, type=int)
        data, total = service.get_proxy_security_events(ip, int(port), page=page, limit=limit)
        return jsonify({"data": data, "total": total, "page": page, "limit": limit})
    finally:
        service.close()


@security_bp.route("/api/security/scans", methods=["GET"])
@security_bp.route("/api/security/batches", methods=["GET"])
def list_security_scans():
    service = SecurityQueryService()
    try:
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=20, type=int)
        data, total = service.list_batches(page=page, limit=limit)
        return jsonify({"data": data, "total": total, "page": page, "limit": limit})
    finally:
        service.close()


@security_bp.route("/api/security/scans/<batch_id>", methods=["GET"])
@security_bp.route("/api/security/batches/<batch_id>", methods=["GET"])
def get_security_scan_detail(batch_id: str):
    service = SecurityQueryService()
    try:
        record_limit = request.args.get("recordLimit", default=100, type=int)
        detail = service.get_batch_detail(batch_id=batch_id, record_limit=record_limit)
        if detail is None:
            return jsonify({"error": "scan_batch_not_found", "batchId": batch_id}), 404
        return jsonify(detail)
    finally:
        service.close()


@security_bp.route("/api/security/events", methods=["GET"])
def list_security_events():
    service = SecurityQueryService()
    try:
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=20, type=int)
        filters = {
            "event_type": request.args.get("eventType"),
            "risk_level": request.args.get("riskLevel"),
            "country": request.args.get("country"),
        }
        data, total = service.list_events(page=page, limit=limit, filters=filters)
        return jsonify({"data": data, "total": total, "page": page, "limit": limit})
    finally:
        service.close()


@security_bp.route("/api/security/events/<int:event_id>", methods=["GET"])
def get_security_event_detail(event_id: int):
    service = SecurityQueryService()
    try:
        detail = service.get_event_detail(event_id)
        if detail is None:
            return jsonify({"error": "security_event_not_found", "eventId": event_id}), 404
        return jsonify(detail)
    finally:
        service.close()


@security_bp.route("/api/security/geo", methods=["GET"])
def get_security_geo_summary():
    service = SecurityQueryService()
    try:
        return jsonify({"data": service.get_geo_summary()})
    finally:
        service.close()


@security_bp.route("/api/security/geo/<country>", methods=["GET"])
def get_security_geo_region_detail(country: str):
    service = SecurityQueryService()
    try:
        return jsonify(service.get_geo_region_detail(country))
    finally:
        service.close()


@security_bp.route("/api/security/stats/behavior", methods=["GET"])
def get_security_behavior_stats():
    service = SecurityQueryService()
    try:
        return jsonify({"data": service.get_behavior_stats()})
    finally:
        service.close()


@security_bp.route("/api/security/stats/risk-trend", methods=["GET"])
@security_bp.route("/api/security/analytics/trend", methods=["GET"])
def get_security_risk_trend():
    service = SecurityQueryService()
    try:
        days = request.args.get("days", default=14, type=int)
        return jsonify({"data": service.get_risk_trend(days=days)})
    finally:
        service.close()


@security_bp.route("/api/security/analytics/event-types", methods=["GET"])
def get_security_event_type_distribution():
    service = SecurityQueryService()
    try:
        return jsonify({"data": service.get_event_type_distribution()})
    finally:
        service.close()


@security_bp.route("/api/security/analytics/risk-distribution", methods=["GET"])
def get_security_risk_distribution():
    service = SecurityQueryService()
    try:
        return jsonify(service.get_risk_distribution())
    finally:
        service.close()


@security_bp.route("/api/security/honeypot/manifest", methods=["GET"])
def get_security_honeypot_manifest():
    return jsonify({"data": list_targets()})


@security_bp.route("/api/security/proxies/<ip>:<port>/scan", methods=["POST"])
def scan_security_proxy(ip: str, port: str):
    return _run_security_scan([f"{ip}:{port}"])


@security_bp.route("/api/security/batches", methods=["POST"])
@security_bp.route("/api/security/scans", methods=["POST"])
def create_security_batch():
    payload = request.get_json(silent=True) if request.is_json else {}
    payload = payload if isinstance(payload, dict) else {}
    return _run_security_scan(payload.get("proxies") or payload.get("targets") or [])


def _run_security_scan(addresses) -> tuple:
    payload = request.get_json(silent=True) if request.is_json else {}
    payload = payload if isinstance(payload, dict) else {}
    max_workers = int(payload.get("maxWorkers", 20))
    if isinstance(addresses, str):
        addresses = [addresses]

    repository = MySQLProxyRepository()
    proxies = []
    try:
        for address in addresses:
            ip, port = _parse_address(str(address))
            proxy = repository.get_proxy_by_address(ip, port)
            if proxy is not None:
                proxies.append(proxy)
    except ValueError as exc:
        return jsonify({"error": "invalid_proxy_address", "message": str(exc)}), 400
    finally:
        repository.__exit__(None, None, None)

    if not proxies:
        return jsonify({"error": "no_matching_proxies", "requested": addresses}), 404

    checker = ProxyCheckService()
    alive = checker.run_full_check(proxies, max_workers=max_workers, save_to_db=True)
    return jsonify(
        {
            "success": True,
            "message": "security_scan_completed",
            "batchId": checker.last_batch_id,
            "targetProxyCount": len(proxies),
            "aliveCount": len(alive),
        }
    )


def _parse_address(address: str) -> tuple[str, int]:
    if ":" not in address:
        raise ValueError(f"Invalid proxy address: {address}")
    ip, port = address.rsplit(":", 1)
    return ip, int(port)
