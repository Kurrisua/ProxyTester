from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.security_query_service import SecurityQueryService

security_bp = Blueprint("security", __name__)


@security_bp.route("/api/security/overview", methods=["GET"])
def get_security_overview():
    service = SecurityQueryService()
    try:
        return jsonify(service.get_overview())
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


@security_bp.route("/api/security/geo", methods=["GET"])
def get_security_geo_summary():
    service = SecurityQueryService()
    try:
        return jsonify({"data": service.get_geo_summary()})
    finally:
        service.close()
