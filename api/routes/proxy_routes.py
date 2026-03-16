from __future__ import annotations

from flask import Blueprint, jsonify, request

from collectors import DEFAULT_LAST_DATA_PATH
from services.proxy_check_service import ProxyCheckService
from services.proxy_query_service import ProxyQueryService

proxy_bp = Blueprint("proxy", __name__)


@proxy_bp.route("/api/proxies", methods=["GET"])
def get_proxies():
    service = ProxyQueryService()
    try:
        filters = {
            "country": request.args.get("country"),
            "proxy_type": request.args.get("type"),
            "status": request.args.get("status"),
            "min_business_score": request.args.get("min_business_score", type=int),
        }
        page = request.args.get("page", default=1, type=int)
        limit = request.args.get("limit", default=10, type=int)
        sort = request.args.get("sort", default="response_time", type=str)
        data, total = service.list_proxies(filters=filters, page=page, limit=limit, sort=sort)
        return jsonify({"data": data, "total": total, "page": page, "limit": limit})
    finally:
        service.close()


@proxy_bp.route("/api/filters", methods=["GET"])
def get_filters():
    service = ProxyQueryService()
    try:
        return jsonify(service.get_filters())
    finally:
        service.close()


@proxy_bp.route("/api/stats", methods=["GET"])
def get_stats():
    service = ProxyQueryService()
    try:
        return jsonify(service.get_stats())
    finally:
        service.close()


@proxy_bp.route("/api/proxies/high-quality", methods=["GET"])
def get_high_quality_proxies():
    service = ProxyQueryService()
    try:
        min_score = request.args.get("min_score", default=2, type=int)
        limit = request.args.get("limit", default=10, type=int)
        data = service.get_high_quality_proxies(min_score=min_score, limit=limit)
        return jsonify({"data": data, "total": len(data), "minScore": min_score})
    finally:
        service.close()


@proxy_bp.route("/api/proxies/<ip>:<port>", methods=["DELETE"])
def delete_proxy(ip: str, port: str):
    service = ProxyQueryService()
    try:
        service.delete_proxy(ip, int(port))
        return jsonify({"success": True})
    finally:
        service.close()


@proxy_bp.route("/api/refresh", methods=["POST"])
def refresh_proxies():
    default_path = str(DEFAULT_LAST_DATA_PATH)
    payload = request.get_json(silent=True) if request.is_json else {}
    file_path = payload.get("filePath", default_path) if isinstance(payload, dict) else default_path
    check_service = ProxyCheckService()
    proxies = check_service.load_from_file(file_path)
    alive = check_service.run_full_check(proxies, save_to_db=True)
    return jsonify({"success": True, "message": "刷新任务完成", "aliveCount": len(alive)})
