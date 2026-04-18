from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from honeypot.manifest import TARGETS, list_targets

honeypot_bp = Blueprint("honeypot", __name__)


@honeypot_bp.route("/honeypot/manifest", methods=["GET"])
def get_honeypot_manifest():
    base_url = request.host_url.rstrip("/")
    return jsonify({"targets": list_targets(base_url)})


@honeypot_bp.route("/honeypot/static/basic", methods=["GET"])
@honeypot_bp.route("/honeypot/assets/site.css", methods=["GET"])
@honeypot_bp.route("/honeypot/assets/site.js", methods=["GET"])
@honeypot_bp.route("/honeypot/assets/pixel.txt", methods=["GET"])
def get_honeypot_asset():
    target = TARGETS[request.path]
    return Response(target.body, status=target.expected_status_code, content_type=target.content_type)


@honeypot_bp.route("/honeypot/submit", methods=["POST"])
def submit_honeypot_form():
    return jsonify({"status": "received"})
