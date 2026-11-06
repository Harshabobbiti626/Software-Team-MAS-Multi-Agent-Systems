"""
Durable Event-Sourced Mission Persistence & Resumability Engine for MAS.
Stores mission sessions, real-time stage transitions, token metrics, pod statuses,
and strategic gates in a durable SQLite WAL-journaled database.
Enables instant hydration across server restarts and in-flight mission resumption.
"""

import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MissionStore:
    """
    Thread-safe durable SQLite store for MAS missions.
    """

    def __init__(self, db_path: str = ".mas_missions.db"):
        self.db_path = Path(db_path).resolve()
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    target_dir TEXT,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    stage_index INTEGER NOT NULL DEFAULT 1,
                    interactive INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    completed_at REAL,
                    tokens_used_json TEXT NOT NULL,
                    pods_json TEXT NOT NULL,
                    pending_gate_json TEXT,
                    error TEXT
                );

                CREATE TABLE IF NOT EXISTS mission_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_mission_events_id ON mission_events(mission_id);
            """)
            conn.commit()

    def save_mission(
        self,
        mission_id: str,
        title: str,
        description: str,
        target_dir: Optional[str] = None,
        status: str = "RUNNING",
        stage: str = "CONTRACTS",
        stage_index: int = 1,
        interactive: bool = False,
        created_at: Optional[float] = None,
        tokens_used: Optional[Dict[str, Any]] = None,
        pods: Optional[Dict[str, Any]] = None,
        pending_gate: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        c_time = created_at or time.time()
        tok_str = json.dumps(
            tokens_used or {"prompt": 0, "candidate": 0, "thinking": 0, "total": 0}
        )
        pods_str = json.dumps(pods or {})
        gate_str = json.dumps(pending_gate) if pending_gate else None

        with self._lock, self._connection() as conn:
            conn.execute(
                """
                INSERT INTO missions (
                    mission_id, title, description, target_dir, status, stage, stage_index,
                    interactive, created_at, tokens_used_json, pods_json, pending_gate_json, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    target_dir=excluded.target_dir,
                    status=excluded.status,
                    stage=excluded.stage,
                    stage_index=excluded.stage_index,
                    tokens_used_json=excluded.tokens_used_json,
                    pods_json=excluded.pods_json,
                    pending_gate_json=excluded.pending_gate_json,
                    error=excluded.error
                """,
                (
                    mission_id,
                    title,
                    description,
                    target_dir,
                    status,
                    stage,
                    stage_index,
                    1 if interactive else 0,
                    c_time,
                    tok_str,
                    pods_str,
                    gate_str,
                    error,
                ),
            )
            conn.commit()

    def update_mission_state(
        self,
        mission_id: str,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        stage_index: Optional[int] = None,
        tokens_used: Optional[Dict[str, Any]] = None,
        pods: Optional[Dict[str, Any]] = None,
        pending_gate: Optional[Any] = None,
        error: Optional[str] = None,
        completed_at: Optional[float] = None,
    ) -> None:
        updates = []
        params = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if stage is not None:
            updates.append("stage = ?")
            params.append(stage)
        if stage_index is not None:
            updates.append("stage_index = ?")
            params.append(stage_index)
        if tokens_used is not None:
            updates.append("tokens_used_json = ?")
            params.append(json.dumps(tokens_used))
        if pods is not None:
            updates.append("pods_json = ?")
            params.append(json.dumps(pods))
        if pending_gate is not None:
            updates.append("pending_gate_json = ?")
            params.append(json.dumps(pending_gate) if pending_gate else None)
        elif pending_gate is False:
            updates.append("pending_gate_json = NULL")
        if error is not None:
            updates.append("error = ?")
            params.append(error)
        if completed_at is not None:
            updates.append("completed_at = ?")
            params.append(completed_at)

        if not updates:
            return

        params.append(mission_id)
        sql = f"UPDATE missions SET {', '.join(updates)} WHERE mission_id = ?"

        with self._lock, self._connection() as conn:
            conn.execute(sql, tuple(params))
            conn.commit()

    def record_event(self, mission_id: str, event_type: str, data: Dict[str, Any]) -> None:
        payload_str = json.dumps(data, default=str)
        now = time.time()
        with self._lock, self._connection() as conn:
            conn.execute(
                "INSERT INTO mission_events (mission_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (mission_id, event_type, payload_str, now),
            )
            conn.commit()

    def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._connection() as conn:
            cursor = conn.execute("SELECT * FROM missions WHERE mission_id = ?", (mission_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def list_missions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "mission_id": row["mission_id"],
            "title": row["title"],
            "description": row["description"],
            "target_dir": row["target_dir"],
            "status": row["status"],
            "stage": row["stage"],
            "stage_index": row["stage_index"],
            "interactive": bool(row["interactive"]),
            "created_at": row["created_at"],
            "completed_at": row["completed_at"],
            "tokens_used": json.loads(row["tokens_used_json"]) if row["tokens_used_json"] else {},
            "pods": json.loads(row["pods_json"]) if row["pods_json"] else {},
            "pending_gate": json.loads(row["pending_gate_json"])
            if row["pending_gate_json"]
            else None,
            "error": row["error"],
        }


_global_mission_store: Optional[MissionStore] = None


def get_mission_store(db_path: str = ".mas_missions.db") -> MissionStore:
    global _global_mission_store
    if _global_mission_store is None:
        _global_mission_store = MissionStore(db_path=db_path)
    return _global_mission_store
