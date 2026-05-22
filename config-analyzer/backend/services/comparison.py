"""Cross-run comparison and delta analysis."""

from backend.models.database import Database


def compare_rewards(db: Database, run_ids: list[int]) -> dict:
    """Compare reward terms across multiple runs."""
    run_data = db.get_reward_terms_for_runs(run_ids)
    runs_info = {}
    for rid in run_ids:
        run = db.get_run(rid)
        if run:
            runs_info[rid] = {"run_name": run["run_name"], "experiment": run["experiment_name"]}

    # Collect all unique term names across runs
    all_terms = set()
    for terms in run_data.values():
        for t in terms:
            all_terms.add(t["term_name"])

    # Build comparison table
    comparison = []
    for term_name in sorted(all_terms):
        row = {"term_name": term_name, "values": {}}
        for rid in run_ids:
            term_data = next(
                (t for t in run_data.get(rid, []) if t["term_name"] == term_name),
                None,
            )
            if term_data:
                row["values"][rid] = {
                    "weight": term_data["weight"],
                    "func": term_data["func"],
                    "category": term_data["category"],
                }
            else:
                row["values"][rid] = None

        # Determine if values are identical
        weights = set()
        for v in row["values"].values():
            if v:
                weights.add(v["weight"])
        row["identical"] = len(weights) <= 1
        comparison.append(row)

    return {
        "runs": [{"id": rid, **runs_info[rid]} for rid in run_ids],
        "terms": comparison,
    }


def compare_events(db: Database, run_ids: list[int]) -> dict:
    """Compare events across multiple runs."""
    run_data = db.get_events_for_runs(run_ids)
    runs_info = {}
    for rid in run_ids:
        run = db.get_run(rid)
        if run:
            runs_info[rid] = {"run_name": run["run_name"], "experiment": run["experiment_name"]}

    all_event_names = set()
    for events in run_data.values():
        for e in events:
            all_event_names.add(e["event_name"])

    comparison = []
    for event_name in sorted(all_event_names):
        row = {"event_name": event_name, "values": {}}
        for rid in run_ids:
            event_data = next(
                (e for e in run_data.get(rid, []) if e["event_name"] == event_name),
                None,
            )
            if event_data:
                row["values"][rid] = {
                    "func": event_data["func"],
                    "mode": event_data["mode"],
                }
            else:
                row["values"][rid] = None

        modes = set()
        for v in row["values"].values():
            if v:
                modes.add(v["mode"])
        row["identical"] = len(modes) <= 1
        comparison.append(row)

    return {
        "runs": [{"id": rid, **runs_info[rid]} for rid in run_ids],
        "events": comparison,
    }


def compare_agent(db: Database, run_ids: list[int]) -> dict:
    """Compare agent configurations across multiple runs."""
    configs = db.get_agent_configs_for_runs(run_ids)
    runs_info = {}
    for rid in run_ids:
        run = db.get_run(rid)
        if run:
            runs_info[rid] = {"run_name": run["run_name"], "experiment": run["experiment_name"]}

    compare_fields = [
        "learning_rate", "gamma", "lam", "entropy_coef",
        "max_iterations", "num_steps", "activation", "algorithm",
        "actor_dims", "critic_dims", "encoder_dims", "encoder_output_dim",
        "seed",
    ]

    comparison = []
    for field in compare_fields:
        row = {"field": field, "values": {}}
        for rid in run_ids:
            cfg = configs.get(rid, {})
            row["values"][rid] = cfg.get(field)
        # Check equality
        vals = set(str(v) for v in row["values"].values())
        row["identical"] = len(vals) <= 1
        comparison.append(row)

    return {
        "runs": [{"id": rid, **runs_info[rid]} for rid in run_ids],
        "params": comparison,
    }


def compute_delta(db: Database, run_id_a: int, run_id_b: int) -> dict:
    """Full delta analysis between two runs."""
    run_a = db.get_run(run_id_a)
    run_b = db.get_run(run_id_b)
    if not run_a or not run_b:
        return {"error": "One or both runs not found"}

    reward_a = {t["term_name"]: t for t in db.get_reward_terms(run_id_a)}
    reward_b = {t["term_name"]: t for t in db.get_reward_terms(run_id_b)}

    all_terms = set(list(reward_a.keys()) + list(reward_b.keys()))
    reward_changes = {"modified": [], "added": [], "removed": []}
    for term in sorted(all_terms):
        if term in reward_a and term in reward_b:
            if reward_a[term]["weight"] != reward_b[term]["weight"]:
                reward_changes["modified"].append({
                    "term": term,
                    "from": reward_a[term]["weight"],
                    "to": reward_b[term]["weight"],
                })
        elif term in reward_a:
            reward_changes["removed"].append(term)
        else:
            reward_changes["added"].append(term)

    event_a = {e["event_name"]: e for e in db.get_events(run_id_a)}
    event_b = {e["event_name"]: e for e in db.get_events(run_id_b)}
    all_events = set(list(event_a.keys()) + list(event_b.keys()))
    event_changes = {"modified": [], "added": [], "removed": []}
    for evt in sorted(all_events):
        if evt in event_a and evt in event_b:
            if event_a[evt]["mode"] != event_b[evt]["mode"]:
                event_changes["modified"].append({
                    "event": evt,
                    "from": event_a[evt]["mode"],
                    "to": event_b[evt]["mode"],
                })
        elif evt in event_a:
            event_changes["removed"].append(evt)
        else:
            event_changes["added"].append(evt)

    agent_a = db.get_agent_config(run_id_a) or {}
    agent_b = db.get_agent_config(run_id_b) or {}
    compare_fields = [
        "learning_rate", "gamma", "entropy_coef", "max_iterations",
        "num_steps", "activation", "actor_dims", "critic_dims",
    ]
    agent_changes = {}
    for field in compare_fields:
        va = agent_a.get(field)
        vb = agent_b.get(field)
        if str(va) != str(vb):
            agent_changes[field] = {"from": va, "to": vb}

    return {
        "run_a": {"id": run_id_a, "run_name": run_a["run_name"]},
        "run_b": {"id": run_id_b, "run_name": run_b["run_name"]},
        "reward_changes": reward_changes,
        "event_changes": event_changes,
        "agent_changes": agent_changes,
    }
