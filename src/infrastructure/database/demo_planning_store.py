"""Separate durable demo decisions; never dispatches or changes operational data."""

import json
import sqlite3
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class DemoDecisionConflict(ValueError):
    pass


class DemoPlanningStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS demo_plans "
                "(id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL, "
                "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _read(row) -> dict:
        return {**json.loads(row["payload"]), "id": row["id"], "status": row["status"],
                "created_at": row["created_at"], "updated_at": row["updated_at"]}

    def save(self, plan: dict, option_id: str, actor: str, note: str) -> dict:
        option = next((item for item in plan["options"] if item["id"] == option_id), None)
        if option is None:
            raise ValueError("Choose a response from the displayed plan.")
        now = datetime.now(UTC).isoformat()
        payload = {
            "day": plan["day"], "facility_code": plan["facility_code"], "inputs": plan["inputs"],
            "option": option, "provenance": plan["provenance"],
            "events": [{"action": "proposed", "actor": actor, "at": now, "note": note}],
            "execution": [],
        }
        identifier = str(uuid.uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO demo_plans VALUES (?, ?, ?, ?, ?)",
                       (identifier, "proposed", json.dumps(payload), now, now))
        return self.get(identifier)

    def get(self, identifier: str) -> dict:
        with self._connect() as db:
            row = db.execute("SELECT * FROM demo_plans WHERE id = ?", (identifier,)).fetchone()
        if row is None:
            raise KeyError("Demo plan not found.")
        return self._read(row)

    def recent(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM demo_plans ORDER BY created_at DESC LIMIT 20").fetchall()
        return [self._read(row) for row in rows]

    def transition(self, identifier: str, action: str, actor: str, note: str) -> dict:
        if action not in {"approve", "reject", "simulate"}:
            raise ValueError("Choose approve, reject or simulate.")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM demo_plans WHERE id = ?", (identifier,)).fetchone()
            if row is None:
                raise KeyError("Demo plan not found.")
            plan = self._read(row)
            status = plan["status"]
            if action == "approve":
                if status != "proposed" or not plan["option"]["viable"]:
                    raise DemoDecisionConflict("Only a viable proposed plan can be approved.")
                next_status = "approved"
            elif action == "reject":
                if status not in {"proposed", "approved"}:
                    raise DemoDecisionConflict("This plan can no longer be rejected.")
                next_status = "rejected"
            else:
                if status == "simulated":
                    return plan
                if status != "approved":
                    raise DemoDecisionConflict("Approve the plan before simulating execution.")
                next_status = "simulated"
                plan["execution"] = [
                    {"system": item.get("system", "demo planning"), "action": item,
                     "status": "simulated only", "operational_write": False}
                    for item in plan["option"]["actions"]
                ]
            now = datetime.now(UTC).isoformat()
            plan["events"].append({"action": next_status, "actor": actor, "at": now, "note": note})
            payload = {key: value for key, value in plan.items()
                       if key not in {"id", "status", "created_at", "updated_at"}}
            db.execute("UPDATE demo_plans SET status = ?, payload = ?, updated_at = ? WHERE id = ?",
                       (next_status, json.dumps(payload), now, identifier))
        return self.get(identifier)
