from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from honeypot.manifest import TARGETS, list_targets

honeypot_bp = Blueprint("honeypot", __name__)


@honeypot_bp.route("/honeypot/manifest", methods=["GET"])
def get_honeypot_manifest():
    base_url = request.host_url.rstrip("/")
    return jsonify({"targets": list_targets(base_url)})


@honeypot_bp.route("/honeypot/static/basic", methods=["GET"])
@honeypot_bp.route("/honeypot/static/complex", methods=["GET"])
@honeypot_bp.route("/honeypot/assets/site.css", methods=["GET"])
@honeypot_bp.route("/honeypot/assets/site.js", methods=["GET"])
@honeypot_bp.route("/honeypot/assets/pixel.txt", methods=["GET"])
@honeypot_bp.route("/honeypot/assets/marker.svg", methods=["GET"])
@honeypot_bp.route("/honeypot/download/sample.txt", methods=["GET"])
@honeypot_bp.route("/honeypot/download/sample.zip", methods=["GET"])
def get_honeypot_asset():
    target = TARGETS[request.path]
    _log_honeypot_request(target.body, target.expected_status_code)
    return Response(target.body, status=target.expected_status_code, content_type=target.content_type)


@honeypot_bp.route("/honeypot/submit", methods=["POST"])
def submit_honeypot_form():
    body = '{"status":"received"}'
    _log_honeypot_request(body, 200)
    return jsonify({"status": "received"})


def _log_honeypot_request(response_body, response_status_code: int) -> None:
    try:
        from storage.mysql.honeypot_repository import MySQLHoneypotRepository

        repository = MySQLHoneypotRepository()
        try:
            repository.log_request(
                method=request.method,
                path=request.path,
                source_ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                user_agent=request.headers.get("User-Agent"),
                request_headers=dict(request.headers),
                response_status_code=response_status_code,
                response_body=response_body,
            )
        finally:
            repository.close()
    except Exception:
        # Honeypot serving must remain deterministic even when optional logging is unavailable.
        return
