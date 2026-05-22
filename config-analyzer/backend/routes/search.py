"""Routes: Search across configs."""

from flask import Blueprint, request, jsonify

from backend.config import DB_PATH
from backend.models.database import Database
from backend.services.summarizer import get_overview_stats, get_reward_summary

search_bp = Blueprint("search", __name__, url_prefix="/api/search")
stats_bp = Blueprint("stats", __name__, url_prefix="/api/stats")


def get_db() -> Database:
    return Database(DB_PATH)


@search_bp.route("", methods=["GET"])
def search_all():
    """Search param paths/values and evaluation notes."""
    db = get_db()
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    param_results = db.search_params(query)
    eval_results = db.search_evaluations(query)

    # Group param results by param_path
    grouped_params = {}
    for r in param_results:
        key = f"{r['param_path']}={r['value_text']}"
        if key not in grouped_params:
            grouped_params[key] = {
                "param_path": r["param_path"],
                "param_name": r["param_name"],
                "value_text": r["value_text"],
                "section": r["section"],
                "runs": [],
            }
        grouped_params[key]["runs"].append({
            "run_id": r["run_id"],
            "run_name": r["run_name"],
            "experiment": r["experiment_name"],
        })

    return jsonify({
        "query": query,
        "param_results": list(grouped_params.values()),
        "eval_results": [dict(r) for r in eval_results],
        "total_param_matches": len(param_results),
        "total_eval_matches": len(eval_results),
    })


@search_bp.route("/eval", methods=["GET"])
def search_eval():
    """Search evaluation notes specifically."""
    db = get_db()
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    results = db.search_evaluations(query)
    return jsonify({
        "query": query,
        "results": [dict(r) for r in results],
        "total": len(results),
    })


@stats_bp.route("/overview", methods=["GET"])
def overview():
    """Get aggregate overview statistics."""
    db = get_db()
    stats = get_overview_stats(db)
    experiments = db.get_experiments()
    return jsonify({
        **stats,
        "experiments": experiments,
    })


@stats_bp.route("/reward-distribution", methods=["GET"])
def reward_distribution():
    """Get reward weight distribution across all runs."""
    db = get_db()
    runs = db.get_all_runs()
    run_ids = [r["id"] for r in runs]
    summary = get_reward_summary(db, run_ids)
    return jsonify(summary)
