"""Routes: Config section access (rewards, events, commands, etc.)."""

from flask import Blueprint, jsonify

from backend.config import DB_PATH
from backend.models.database import Database

config_bp = Blueprint("config", __name__, url_prefix="/api/runs/<int:run_id>/config")


def get_db() -> Database:
    return Database(DB_PATH)


@config_bp.route("/rewards", methods=["GET"])
def get_rewards(run_id: int):
    """Get reward terms for a specific run."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    terms = db.get_reward_terms(run_id)
    rewards = [t for t in terms if t["category"] == "reward"]
    penalties = [t for t in terms if t["category"] == "penalty"]
    return jsonify({
        "run_name": run["run_name"],
        "rewards": rewards,
        "penalties": penalties,
        "total_positive_weight": sum(t["weight"] for t in rewards),
        "total_negative_weight": sum(t["weight"] for t in penalties),
    })


@config_bp.route("/events", methods=["GET"])
def get_events(run_id: int):
    """Get domain randomization events for a specific run."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    events = db.get_events(run_id)
    startup = [e for e in events if e["mode"] == "startup"]
    reset = [e for e in events if e["mode"] == "reset"]
    interval = [e for e in events if e["mode"] == "interval"]
    return jsonify({
        "run_name": run["run_name"],
        "total": len(events),
        "startup": startup,
        "reset": reset,
        "interval": interval,
    })


@config_bp.route("/commands", methods=["GET"])
def get_commands(run_id: int):
    """Get command configuration (gait, velocity)."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    params = db.get_config_params(run_id, section="env.commands")
    # Group by command name
    commands = {}
    for p in params:
        path = p["param_path"]
        parts = path.split(".")
        if len(parts) >= 3:
            cmd_name = parts[1]
            key = parts[2]
            if cmd_name not in commands:
                commands[cmd_name] = {}
            commands[cmd_name][key] = p["value_text"]
    return jsonify({
        "run_name": run["run_name"],
        "commands": commands,
    })


@config_bp.route("/observations", methods=["GET"])
def get_observations(run_id: int):
    """Get observation space configuration."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    params = db.get_config_params(run_id, section="env.observations")
    obs_groups = {}
    for p in params:
        path = p["param_path"]
        parts = path.split(".")
        if len(parts) >= 2:
            group = parts[1] if parts[0] == "observations" else parts[0]
            if group not in obs_groups:
                obs_groups[group] = {}
            obs_groups[group][p["param_name"]] = p["value_text"]
    return jsonify({
        "run_name": run["run_name"],
        "observation_groups": obs_groups,
    })


@config_bp.route("/agent", methods=["GET"])
def get_agent(run_id: int):
    """Get agent/algorithm configuration."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    agent = db.get_agent_config(run_id)
    if not agent:
        return jsonify({"error": "Agent config not found"}), 404
    return jsonify({
        "run_name": run["run_name"],
        "agent": agent,
    })


@config_bp.route("/sim", methods=["GET"])
def get_sim(run_id: int):
    """Get simulation parameters."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    params = db.get_config_params(run_id, section="env.sim")
    sim = {}
    for p in params:
        sim[p["param_name"]] = p["value_text"]
    return jsonify({
        "run_name": run["run_name"],
        "sim_params": sim,
    })


@config_bp.route("/terminations", methods=["GET"])
def get_terminations(run_id: int):
    """Get termination conditions."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    params = db.get_config_params(run_id, section="env.terminations")
    terminations = {}
    for p in params:
        path = p["param_path"]
        parts = path.split(".")
        if len(parts) >= 2:
            name = parts[1]
            if name not in terminations:
                terminations[name] = {}
            terminations[name][p["param_name"]] = p["value_text"]
    return jsonify({
        "run_name": run["run_name"],
        "terminations": terminations,
    })
