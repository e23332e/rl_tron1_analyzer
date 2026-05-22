"""SQLite database schema and CRUD operations."""

import sqlite3
import json
import time
from pathlib import Path
from typing import Optional

from backend.config import DB_PATH


class Database:
    """SQLite database manager for config analysis platform."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self._init_schema()

    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self):
        """Create tables if they don't exist."""
        with self._get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_name TEXT NOT NULL,
                experiment_name TEXT,
                timestamp TEXT,
                robot_type TEXT,
                task_variant TEXT,
                notes TEXT,
                tags TEXT,
                checkpoint_count INTEGER DEFAULT 0,
                imported_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS config_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                section TEXT NOT NULL,
                param_path TEXT NOT NULL,
                param_name TEXT NOT NULL,
                value_text TEXT,
                value_type TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_cp_run ON config_params(run_id);
            CREATE INDEX IF NOT EXISTS idx_cp_path ON config_params(param_path);
            CREATE INDEX IF NOT EXISTS idx_cp_section ON config_params(section);

            CREATE TABLE IF NOT EXISTS reward_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                term_name TEXT NOT NULL,
                func TEXT NOT NULL,
                weight REAL NOT NULL,
                category TEXT,
                params_summary TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_rt_run ON reward_terms(run_id);

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                func TEXT NOT NULL,
                mode TEXT NOT NULL,
                params_summary TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS agent_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL UNIQUE,
                algorithm TEXT,
                learning_rate REAL,
                gamma REAL,
                lam REAL,
                entropy_coef REAL,
                desired_kl REAL,
                max_grad_norm REAL,
                value_loss_coef REAL,
                clip_param REAL,
                num_learning_epochs INTEGER,
                num_mini_batches INTEGER,
                schedule TEXT,
                max_iterations INTEGER,
                num_steps INTEGER,
                actor_dims TEXT,
                critic_dims TEXT,
                activation TEXT,
                init_noise_std REAL,
                obs_history_len INTEGER,
                encoder_dims TEXT,
                encoder_output_dim INTEGER,
                seed INTEGER,
                experiment_name TEXT,
                resume INTEGER,
                load_run TEXT,
                save_interval INTEGER,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL UNIQUE,
                content TEXT,
                parsed_issues TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            );
            """)

    # ---- Runs ----

    def create_run(
        self,
        run_name: str,
        experiment_name: str = None,
        timestamp: str = None,
        robot_type: str = None,
        task_variant: str = None,
        notes: str = None,
        tags: list = None,
    ) -> int:
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO runs (run_name, experiment_name, timestamp,
                   robot_type, task_variant, notes, tags, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_name, experiment_name, timestamp,
                    robot_type, task_variant, notes,
                    json.dumps(tags) if tags else None,
                    time.time(),
                ),
            )
            return cur.lastrowid

    def get_all_runs(self, robot_type: str = None, experiment: str = None) -> list[dict]:
        with self._get_conn() as conn:
            query = """
            SELECT r.*,
                   (SELECT COUNT(*) FROM reward_terms WHERE run_id = r.id) AS reward_count,
                   (SELECT COUNT(*) FROM events WHERE run_id = r.id) AS event_count,
                   e.content AS eval_content,
                   e.parsed_issues AS eval_issues
            FROM runs r
            LEFT JOIN evaluations e ON e.run_id = r.id
            WHERE 1=1
            """
            params = []
            if robot_type:
                query += " AND r.robot_type = ?"
                params.append(robot_type)
            if experiment:
                query += " AND r.experiment_name = ?"
                params.append(experiment)
            query += " ORDER BY r.imported_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_run(self, run_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT r.*,
                   e.content AS eval_content,
                   e.parsed_issues AS eval_issues
                   FROM runs r
                   LEFT JOIN evaluations e ON e.run_id = r.id
                   WHERE r.id = ?""",
                (run_id,),
            ).fetchone()
            return dict(row) if row else None

    def delete_run(self, run_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
            return cur.rowcount > 0

    def update_run(self, run_id: int, **kwargs) -> bool:
        allowed = {"notes", "tags", "run_name", "experiment_name"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        if "tags" in updates and isinstance(updates["tags"], list):
            updates["tags"] = json.dumps(updates["tags"])
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [run_id]
        with self._get_conn() as conn:
            cur = conn.execute(
                f"UPDATE runs SET {set_clause} WHERE id = ?", params
            )
            return cur.rowcount > 0

    # ---- Config Params ----

    def insert_config_param(
        self, run_id: int, section: str, param_path: str,
        param_name: str, value_text: str, value_type: str,
    ):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO config_params
                   (run_id, section, param_path, param_name, value_text, value_type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (run_id, section, param_path, param_name, value_text, value_type),
            )

    def flush_config_params_section(self, run_id: int, params: list[dict]):
        """Batch insert config params."""
        with self._get_conn() as conn:
            conn.executemany(
                """INSERT INTO config_params
                   (run_id, section, param_path, param_name, value_text, value_type)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (run_id, p["section"], p["param_path"], p["param_name"],
                     p["value_text"], p["value_type"])
                    for p in params
                ],
            )

    def get_config_params(
        self, run_id: int, section: str = None
    ) -> list[dict]:
        with self._get_conn() as conn:
            if section:
                rows = conn.execute(
                    "SELECT * FROM config_params WHERE run_id = ? AND section = ?",
                    (run_id, section),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM config_params WHERE run_id = ?", (run_id,)
                ).fetchall()
            return [dict(row) for row in rows]

    # ---- Reward Terms ----

    def insert_reward_terms(self, run_id: int, terms: list[dict]):
        with self._get_conn() as conn:
            conn.executemany(
                """INSERT INTO reward_terms (run_id, term_name, func, weight, category, params_summary)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [
                    (run_id, t["term_name"], t["func"], t["weight"],
                     t["category"], json.dumps(t.get("params_summary", {}), ensure_ascii=False))
                    for t in terms
                ],
            )

    def get_reward_terms(self, run_id: int) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM reward_terms WHERE run_id = ? ORDER BY weight DESC",
                (run_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    # ---- Events ----

    def insert_events(self, run_id: int, events: list[dict]):
        with self._get_conn() as conn:
            conn.executemany(
                """INSERT INTO events (run_id, event_name, func, mode, params_summary)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (run_id, e["event_name"], e["func"], e["mode"],
                     json.dumps(e.get("params_summary", {}), ensure_ascii=False))
                    for e in events
                ],
            )

    def get_events(self, run_id: int) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY mode, event_name",
                (run_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    # ---- Agent Config ----

    def insert_agent_config(self, run_id: int, config: dict):
        defaults = {
            "algorithm": None, "learning_rate": None, "gamma": None,
            "lam": None, "entropy_coef": None, "desired_kl": None,
            "max_grad_norm": None, "value_loss_coef": None, "clip_param": None,
            "num_learning_epochs": None, "num_mini_batches": None,
            "schedule": None, "max_iterations": None, "num_steps": None,
            "actor_dims": None, "critic_dims": None, "activation": None,
            "init_noise_std": None, "obs_history_len": None,
            "encoder_dims": None, "encoder_output_dim": None,
            "seed": None, "experiment_name": None, "resume": 0,
            "load_run": None, "save_interval": None,
        }
        data = {**defaults, **config}
        # Convert lists to JSON strings
        for key in ("actor_dims", "critic_dims", "encoder_dims"):
            if isinstance(data[key], list):
                data[key] = json.dumps(data[key])
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO agent_config
                   (run_id, algorithm, learning_rate, gamma, lam, entropy_coef,
                    desired_kl, max_grad_norm, value_loss_coef, clip_param,
                    num_learning_epochs, num_mini_batches, schedule,
                    max_iterations, num_steps, actor_dims, critic_dims,
                    activation, init_noise_std, obs_history_len,
                    encoder_dims, encoder_output_dim, seed, experiment_name,
                    resume, load_run, save_interval)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, data["algorithm"], data["learning_rate"], data["gamma"],
                 data["lam"], data["entropy_coef"], data["desired_kl"],
                 data["max_grad_norm"], data["value_loss_coef"], data["clip_param"],
                 data["num_learning_epochs"], data["num_mini_batches"],
                 data["schedule"], data["max_iterations"], data["num_steps"],
                 data["actor_dims"], data["critic_dims"],
                 data["activation"], data["init_noise_std"],
                 data["obs_history_len"], data["encoder_dims"],
                 data["encoder_output_dim"], data["seed"],
                 data["experiment_name"], data["resume"], data["load_run"],
                 data["save_interval"]),
            )

    def get_agent_config(self, run_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent_config WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            for key in ("actor_dims", "critic_dims", "encoder_dims"):
                if result.get(key):
                    try:
                        result[key] = json.loads(result[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            return result

    # ---- Evaluations ----

    def insert_evaluation(self, run_id: int, content: str, parsed_issues: list):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO evaluations (run_id, content, parsed_issues)
                   VALUES (?, ?, ?)""",
                (run_id, content, json.dumps(parsed_issues, ensure_ascii=False)),
            )

    def get_evaluation(self, run_id: int) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM evaluations WHERE run_id = ?", (run_id,)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            if result.get("parsed_issues"):
                try:
                    result["parsed_issues"] = json.loads(result["parsed_issues"])
                except (json.JSONDecodeError, TypeError):
                    pass
            return result

    # ---- Comparison helpers ----

    def get_reward_terms_for_runs(self, run_ids: list[int]) -> dict[int, list[dict]]:
        if not run_ids:
            return {}
        with self._get_conn() as conn:
            placeholders = ",".join("?" * len(run_ids))
            rows = conn.execute(
                f"""SELECT rt.* FROM reward_terms rt
                    WHERE rt.run_id IN ({placeholders})
                    ORDER BY rt.run_id, rt.weight DESC""",
                run_ids,
            ).fetchall()
        result = {rid: [] for rid in run_ids}
        for row in rows:
            d = dict(row)
            result[d["run_id"]].append(d)
        return result

    def get_events_for_runs(self, run_ids: list[int]) -> dict[int, list[dict]]:
        if not run_ids:
            return {}
        with self._get_conn() as conn:
            placeholders = ",".join("?" * len(run_ids))
            rows = conn.execute(
                f"""SELECT * FROM events
                    WHERE run_id IN ({placeholders})
                    ORDER BY run_id, mode, event_name""",
                run_ids,
            ).fetchall()
        result = {rid: [] for rid in run_ids}
        for row in rows:
            d = dict(row)
            result[d["run_id"]].append(d)
        return result

    def get_agent_configs_for_runs(self, run_ids: list[int]) -> dict[int, dict]:
        if not run_ids:
            return {}
        result = {}
        for rid in run_ids:
            cfg = self.get_agent_config(rid)
            if cfg:
                result[rid] = cfg
        return result

    # ---- Search ----

    def search_params(self, query: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT cp.*, r.run_name, r.experiment_name
                   FROM config_params cp
                   JOIN runs r ON r.id = cp.run_id
                   WHERE cp.param_path LIKE ? OR cp.value_text LIKE ?
                   ORDER BY r.imported_at DESC""",
                (f"%{query}%", f"%{query}%"),
            ).fetchall()
            return [dict(row) for row in rows]

    def search_evaluations(self, query: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT e.*, r.run_name, r.experiment_name
                   FROM evaluations e
                   JOIN runs r ON r.id = e.run_id
                   WHERE e.content LIKE ?
                   ORDER BY r.imported_at DESC""",
                (f"%{query}%",),
            ).fetchall()
            return [dict(row) for row in rows]

    # ---- Statistics ----

    def get_experiments(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                """SELECT experiment_name, robot_type,
                   COUNT(*) AS run_count,
                   MAX(timestamp) AS latest_timestamp
                   FROM runs
                   GROUP BY experiment_name, robot_type
                   ORDER BY latest_timestamp DESC"""
            ).fetchall()
            return [dict(row) for row in rows]

    def get_overview_stats(self) -> dict:
        with self._get_conn() as conn:
            run_count = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            exp_count = conn.execute(
                "SELECT COUNT(DISTINCT experiment_name) FROM runs"
            ).fetchone()[0]
            param_count = conn.execute(
                "SELECT COUNT(DISTINCT param_path) FROM config_params"
            ).fetchone()[0]
            return {
                "total_runs": run_count,
                "total_experiments": exp_count,
                "unique_params": param_count,
            }
