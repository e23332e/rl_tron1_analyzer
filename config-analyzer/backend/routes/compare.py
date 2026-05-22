"""Routes: Comparison endpoints."""

from flask import Blueprint, request, jsonify

from backend.config import DB_PATH
from backend.models.database import Database
from backend.services.comparison import (
    compare_rewards,
    compare_events,
    compare_agent,
    compute_delta,
)

compare_bp = Blueprint("compare", __name__, url_prefix="/api/compare")


def get_db() -> Database:
    return Database(DB_PATH)


@compare_bp.route("/rewards", methods=["GET"])
def cmp_rewards():
    """Compare reward terms across runs. Query: ?ids=1,2,3"""
    db = get_db()
    ids_str = request.args.get("ids", "")
    if not ids_str:
        return jsonify({"error": "ids parameter required"}), 400
    try:
        run_ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
    except ValueError:
        return jsonify({"error": "Invalid ids format"}), 400
    if len(run_ids) < 2:
        return jsonify({"error": "Need at least 2 run ids"}), 400
    result = compare_rewards(db, run_ids)
    return jsonify(result)


@compare_bp.route("/events", methods=["GET"])
def cmp_events():
    """Compare events across runs. Query: ?ids=1,2,3"""
    db = get_db()
    ids_str = request.args.get("ids", "")
    if not ids_str:
        return jsonify({"error": "ids parameter required"}), 400
    try:
        run_ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
    except ValueError:
        return jsonify({"error": "Invalid ids format"}), 400
    if len(run_ids) < 2:
        return jsonify({"error": "Need at least 2 run ids"}), 400
    result = compare_events(db, run_ids)
    return jsonify(result)


@compare_bp.route("/agent", methods=["GET"])
def cmp_agent():
    """Compare agent configs across runs. Query: ?ids=1,2,3"""
    db = get_db()
    ids_str = request.args.get("ids", "")
    if not ids_str:
        return jsonify({"error": "ids parameter required"}), 400
    try:
        run_ids = [int(x.strip()) for x in ids_str.split(",") if x.strip()]
    except ValueError:
        return jsonify({"error": "Invalid ids format"}), 400
    if len(run_ids) < 2:
        return jsonify({"error": "Need at least 2 run ids"}), 400
    result = compare_agent(db, run_ids)
    return jsonify(result)


@compare_bp.route("/delta/<int:run_a>/<int:run_b>", methods=["GET"])
def cmp_delta(run_a: int, run_b: int):
    """Full delta analysis between two runs."""
    db = get_db()
    result = compute_delta(db, run_a, run_b)
    return jsonify(result)
