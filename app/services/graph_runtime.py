from __future__ import annotations
import contextvars
from pathlib import Path
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from app.core.config import settings
from app.core.logger import logger
from app.core.tracking import traceable

# current user context used by memory tools
current_user_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("current_user_id", default="default_user")

class GraphRuntime:
    """
    Holds the LangGraph checkpointer and lifecycle.
    We manually enter/exit the SqliteSaver context on app startup/shutdown.
    """
    def __init__(self, path: Path):
        self.path = path
        self._cm = None
        self.checkpointer: SqliteSaver | None = None

    def _ensure_file(self, p: Path):
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(p))
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        finally:
            conn.close()

    @traceable(name="graph_runtime_start")
    def start(self):
        self._ensure_file(self.path)
        self._cm = SqliteSaver.from_conn_string(self.path.as_posix())
        self.checkpointer = self._cm.__enter__()
        logger.info(f"SqliteSaver open at {self.path}")

    @traceable(name="graph_runtime_stop")
    def stop(self):
        if self._cm:
            self._cm.__exit__(None, None, None)
            logger.info("SqliteSaver closed")
            self._cm = None
            self.checkpointer = None

graph_runtime = GraphRuntime(settings.data_dir / "graph_state.sqlite3")
