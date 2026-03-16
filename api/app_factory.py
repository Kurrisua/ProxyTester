from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from api.routes.proxy_routes import proxy_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(proxy_bp)
    return app
