"""
Tier 2: Episodic Memory (Event Sourcing & SQLite Audit Log).
Provides an immutable ledger of every agent action, state transition, and tool execution.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


class EpisodicMemory:
    def __init__(self, db_path: str = ".mas_episodic.db"):
        self.db_path = Path(db_path).resolve()
        self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    agent_role TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            conn.commit()

    def record_event(
        self,
        session_id: str,
        task_id: str,
        agent_role: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, default=str)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO episodic_events (session_id, task_id, agent_role, event_type, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (session_id, task_id, agent_role, event_type, payload_str, now),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def get_events_for_task(self, task_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, session_id, task_id, agent_role, event_type, payload_json, created_at
                FROM episodic_events
                WHERE task_id = ?
                ORDER BY id ASC
            """,
                (task_id,),
            )
            rows = cursor.fetchall()

        events = []
        for r in rows:
            events.append(
                {
                    "id": r["id"],
                    "session_id": r["session_id"],
                    "task_id": r["task_id"],
                    "agent_role": r["agent_role"],
                    "event_type": r["event_type"],
                    "payload": json.loads(r["payload_json"]),
                    "created_at": r["created_at"],
                }
            )
        return events

    def get_all_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, session_id, task_id, agent_role, event_type, payload_json, created_at
                FROM episodic_events
                ORDER BY id DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = cursor.fetchall()

        events = []
        for r in rows:
            events.append(
                {
                    "id": r["id"],
                    "session_id": r["session_id"],
                    "task_id": r["task_id"],
                    "agent_role": r["agent_role"],
                    "event_type": r["event_type"],
                    "payload": json.loads(r["payload_json"]),
                    "created_at": r["created_at"],
                }
            )
        return events
