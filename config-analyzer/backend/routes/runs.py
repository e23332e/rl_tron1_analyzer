"""Routes: Run management, import, and CRUD."""

import os
import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify

from backend.config import DB_PATH, UPLOAD_DIR, SAMPLE_CONFIG_DIR
from backend.models.database import Database
from backend.parsers.env_parser import EnvConfigParser
from backend.parsers.agent_parser import AgentConfigParser
from backend.utils import (
    infer_robot_type,
    infer_task_variant,
    parse_evaluation_issues,
)

runs_bp = Blueprint("runs", __name__, url_prefix="/api/runs")


def get_db() -> Database:
    return Database(DB_PATH)


def _import_run(
    db: Database,
    env_path: str,
    agent_path: str,
    eval_path: str = None,
    run_name: str = None,
    experiment_name: str = None,
) -> int:
    """Import a single training run from YAML files."""
    # Parse env.yaml
    env = EnvConfigParser(env_path)
    env_data = env.extract_all()

    # Try to get experiment_name from agent.yaml if not provided
    if not experiment_name:
        try:
            agent = AgentConfigParser(agent_path)
            agent_data = agent.extract()
            exp_from_agent = agent_data.get("experiment_name")
            if exp_from_agent:
                experiment_name = exp_from_agent
        except Exception:
            pass

    if not experiment_name:
        # Fallback to parent directory name
        path = Path(env_path)
        parent = path.parent.parent  # go up from params/ to run_dir
        experiment_name = parent.name if parent.name != "params" else "Imported"

    # Determine timestamp from run_name or file path
    if not run_name:
        path = Path(env_path)
        parent = path.parent.parent  # run_dir containing params/
        run_name = parent.name
        if "_" not in run_name or len(run_name) < 19:
            run_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    timestamp = run_name[:19] if len(run_name) >= 19 else run_name
    robot_type = infer_robot_type(experiment_name)
    task_variant = infer_task_variant(experiment_name)

    # Create run entry
    run_id = db.create_run(
        run_name=run_name,
        experiment_name=experiment_name,
        timestamp=timestamp,
        robot_type=robot_type,
        task_variant=task_variant,
    )

    # Store reward terms
    rewards = env.extract_rewards()
    if rewards:
        db.insert_reward_terms(run_id, rewards)

    # Store events
    events = env.extract_events()
    if events:
        db.insert_events(run_id, events)

    # Store flattened config params
    env_params = env.flatten_to_params(run_id)
    if env_params:
        db.flush_config_params_section(run_id, env_params)

    # Parse and store agent config
    agent = AgentConfigParser(agent_path)
    agent_data = agent.extract()
    db.insert_agent_config(run_id, agent_data)

    agent_params = agent.flatten_to_params(run_id)
    if agent_params:
        db.flush_config_params_section(run_id, agent_params)

    # Store evaluation notes
    if eval_path and os.path.exists(eval_path):
        with open(eval_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read().strip()
        if content:
            issues = parse_evaluation_issues(content)
            db.insert_evaluation(run_id, content, issues)

    return run_id


@runs_bp.route("", methods=["GET"])
def list_runs():
    """List all runs with optional filtering."""
    db = get_db()
    robot_type = request.args.get("robot_type")
    experiment = request.args.get("experiment")
    runs = db.get_all_runs(robot_type=robot_type, experiment=experiment)
    for run in runs:
        if run.get("eval_issues"):
            try:
                run["eval_issues"] = json.loads(run["eval_issues"])
            except (json.JSONDecodeError, TypeError):
                pass
    return jsonify(runs)


@runs_bp.route("/<int:run_id>", methods=["GET"])
def get_run(run_id: int):
    """Get full detail for a single run."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    if run.get("eval_issues"):
        try:
            run["eval_issues"] = json.loads(run["eval_issues"])
        except (json.JSONDecodeError, TypeError):
            pass

    detail = {
        "run": run,
        "agent": db.get_agent_config(run_id),
        "rewards": db.get_reward_terms(run_id),
        "events": db.get_events(run_id),
        "evaluation": db.get_evaluation(run_id),
    }
    return jsonify(detail)


@runs_bp.route("/import", methods=["POST"])
def import_run():
    """Import YAML files via multipart form upload."""
    db = get_db()

    # Check required files
    if "env" not in request.files:
        return jsonify({"error": "env.yaml file is required"}), 400
    if "agent" not in request.files:
        return jsonify({"error": "agent.yaml file is required"}), 400

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Save uploaded files
    import uuid
    session_dir = UPLOAD_DIR / uuid.uuid4().hex
    session_dir.mkdir(parents=True, exist_ok=True)

    env_file = request.files["env"]
    agent_file = request.files["agent"]
    eval_file = request.files.get("eval")

    env_path = session_dir / "env.yaml"
    agent_path = session_dir / "agent.yaml"
    env_file.save(str(env_path))
    agent_file.save(str(agent_path))

    eval_path = None
    if eval_file and eval_file.filename:
        eval_path = session_dir / "eval.txt"
        eval_file.save(str(eval_path))

    run_name = request.form.get("run_name")
    experiment_name = request.form.get("experiment_name")

    try:
        run_id = _import_run(
            db, str(env_path), str(agent_path),
            str(eval_path) if eval_path else None,
            run_name, experiment_name)
        return jsonify({"success": True, "run_id": run_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _find_runs(root: Path) -> list[dict]:
    """Find all training runs under a root directory.

    Supports three structures:
    1. Direct: root/params/env.yaml (the root itself is a run dir)
    2. Flat: root/run_dir/params/env.yaml (each subdir is a run)
    3. Nested: root/experiment_dir/run_dir/params/env.yaml
    """
    runs = []

    # Check if root itself is a run directory
    root_params = root / "params"
    root_env = root_params / "env.yaml"
    root_agent = root_params / "agent.yaml"
    if root_env.exists() and root_agent.exists():
        root_eval = root / "exported" / "评价.txt"
        runs.append({
            "run_dir": root,
            "env_yaml": root_env,
            "agent_yaml": root_agent,
            "eval_file": root_eval if root_eval.exists() else None,
            "experiment_name": None,
        })

    # Try flat structure: each subdir is a run
    for item in root.iterdir():
        if not item.is_dir():
            continue
        params_dir = item / "params"
        env_yaml = params_dir / "env.yaml"
        agent_yaml = params_dir / "agent.yaml"
        if env_yaml.exists() and agent_yaml.exists():
            eval_file = item / "exported" / "评价.txt"
            runs.append({
                "run_dir": item,
                "env_yaml": env_yaml,
                "agent_yaml": agent_yaml,
                "eval_file": eval_file if eval_file.exists() else None,
                "experiment_name": None,
            })
            continue

        # Try nested structure
        for sub_item in item.iterdir():
            if not sub_item.is_dir():
                continue
            sub_params = sub_item / "params"
            sub_env = sub_params / "env.yaml"
            sub_agent = sub_params / "agent.yaml"
            if sub_env.exists() and sub_agent.exists():
                sub_eval = sub_item / "exported" / "评价.txt"
                runs.append({
                    "run_dir": sub_item,
                    "exp_dir": item,
                    "env_yaml": sub_env,
                    "agent_yaml": sub_agent,
                    "eval_file": sub_eval if sub_eval.exists() else None,
                })

    return runs


@runs_bp.route("/import-directory", methods=["POST"])
def import_directory():
    """Batch import from a directory path."""
    db = get_db()
    data = request.get_json() or {}
    dir_path = data.get("directory", str(SAMPLE_CONFIG_DIR))

    if not os.path.isdir(dir_path):
        return jsonify({"error": f"Directory not found: {dir_path}"}), 404

    imported = 0
    errors = []

    root = Path(dir_path)
    runs = _find_runs(root)

    for run_info in runs:
        try:
            exp_name = run_info.get("experiment_name")
            _import_run(
                db,
                str(run_info["env_yaml"]),
                str(run_info["agent_yaml"]),
                str(run_info["eval_file"]) if run_info["eval_file"] else None,
                run_name=run_info["run_dir"].name,
                experiment_name=exp_name)
            imported += 1
        except Exception as e:
            errors.append({"run": run_info["run_dir"].name, "error": str(e)})

    return jsonify({
        "success": True,
        "imported": imported,
        "errors": errors,
    })


@runs_bp.route("/<int:run_id>", methods=["DELETE"])
def delete_run(run_id: int):
    """Delete a run and all associated data."""
    db = get_db()
    if db.delete_run(run_id):
        return jsonify({"success": True})
    return jsonify({"error": "Run not found"}), 404


@runs_bp.route("/<int:run_id>", methods=["PUT"])
def update_run(run_id: int):
    """Update run notes or tags."""
    db = get_db()
    data = request.get_json() or {}
    if db.update_run(run_id, **data):
        return jsonify({"success": True})
    return jsonify({"error": "Run not found or no valid fields"}), 404


@runs_bp.route("/<int:run_id>/evaluation", methods=["PUT"])
def update_evaluation(run_id: int):
    """Update evaluation notes for a run."""
    db = get_db()
    run = db.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    data = request.get_json() or {}
    content = data.get("content", "")
    issues = parse_evaluation_issues(content)
    db.insert_evaluation(run_id, content, issues)
    return jsonify({"success": True, "parsed_issues": issues})
