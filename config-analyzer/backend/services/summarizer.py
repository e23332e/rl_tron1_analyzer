"""Statistics and summary computations."""

from backend.models.database import Database


def get_overview_stats(db: Database) -> dict:
    """Get aggregate statistics across all runs."""
    return db.get_overview_stats()


def get_reward_summary(db: Database, run_ids: list[int] = None) -> dict:
    """Get reward distribution summary across specified runs."""
    if run_ids is None:
        import sqlite3
        with db._get_conn() as conn:
            rows = conn.execute("SELECT id FROM runs").fetchall()
            run_ids = [row["id"] for row in rows]

    if not run_ids:
        return {"terms": {}, "stats": {}}

    terms_data = {}
    for rid in run_ids:
        terms = db.get_reward_terms(rid)
        for t in terms:
            name = t["term_name"]
            if name not in terms_data:
                terms_data[name] = {
                    "func": t["func"],
                    "category": t["category"],
                    "weights": [],
                    "run_count": 0,
                }
            terms_data[name]["weights"].append(t["weight"])
            terms_data[name]["run_count"] += 1

    for name, data in terms_data.items():
        weights = data["weights"]
        data["mean"] = sum(weights) / len(weights)
        data["min"] = min(weights)
        data["max"] = max(weights)
        if len(weights) > 1:
            mean = data["mean"]
            variance = sum((w - mean) ** 2 for w in weights) / len(weights)
            data["std"] = variance ** 0.5
        else:
            data["std"] = 0
        del data["weights"]

    return {
        "terms": dict(sorted(
            terms_data.items(),
            key=lambda x: abs(x[1]["mean"]),
            reverse=True,
        )),
        "total_runs": len(run_ids),
    }
