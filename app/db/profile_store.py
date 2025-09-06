from __future__ import annotations
import sqlite3, json
from pathlib import Path
from typing import Any, Dict
from app.core.logger import logger

class ProfileStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
              user_id    TEXT NOT NULL,
              key        TEXT NOT NULL,
              value      TEXT,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (user_id, key)
            )
        """)
        self.conn.commit()

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        cur = self.conn.execute("SELECT key, value FROM user_profile WHERE user_id = ?", (user_id,))
        out: Dict[str, Any] = {}
        for k, v in cur.fetchall():
            try:
                out[k] = json.loads(v)
            except Exception:
                out[k] = v
        return out

    def upsert(self, user_id: str, updates: Dict[str, Any]) -> None:
        if not updates:
            return
        with self.conn:
            for k, v in updates.items():
                sv = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
                self.conn.execute(
                    """INSERT INTO user_profile(user_id, key, value)
                       VALUES(?, ?, ?)
                       ON CONFLICT(user_id, key) DO UPDATE SET
                         value = excluded.value,
                         updated_at = CURRENT_TIMESTAMP""",
                    (user_id, k, sv),
                )

    def close(self):
        try:
            self.conn.close()
        except Exception as e:
            logger.warning(f"profile store close error: {e}")
