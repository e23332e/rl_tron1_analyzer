"""Flask application factory and entry point."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from backend.routes.runs import runs_bp
from backend.routes.config import config_bp
from backend.routes.compare import compare_bp
from backend.routes.search import search_bp, stats_bp
from backend.config import SECRET_KEY, UPLOAD_DIR


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=None,  # We'll handle static serving manually
    )
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    app.register_blueprint(runs_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(compare_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(stats_bp)

    # Create upload directory
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Serve frontend static files in production
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")

    @app.route("/")
    @app.route("/<path:path>")
    def serve_frontend(path="index.html"):
        # Don't intercept API routes
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        if os.path.exists(frontend_dist) and os.path.isfile(
            os.path.join(frontend_dist, path)
        ):
            return send_from_directory(frontend_dist, path)
        return send_from_directory(frontend_dist, "index.html")

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Not found"}), 404
        if os.path.exists(frontend_dist):
            return send_from_directory(frontend_dist, "index.html")
        return jsonify({"error": "Not found"}), 404

    return app


if __name__ == "__main__":
    app = create_app()
    print("=" * 60)
    print("RL Config Analysis Platform")
    print(f"Starting server on http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
