# app/main.py (only the relevant parts shown)
from fastapi import FastAPI
from app.core.config import settings
from app.core.logger import logger
from app.db.profile_store import ProfileStore
from app.tools.memory_tools import set_profile_store
from app.services.graph_runtime import graph_runtime
from app.agents.unified_graph import build_graph
from app.api.routes import health, chat, memory
from pathlib import Path

app = FastAPI(title="Unified Agents API", version="0.1.0")

@app.on_event("startup")
def on_startup():
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    profile_db = settings.data_dir / "profile.sqlite3"
    store = ProfileStore(profile_db)
    set_profile_store(store)
    app.state.profile_store = store

    graph_runtime.start()
    app.state.graph = build_graph(graph_runtime.checkpointer, app.state.profile_store)
    logger.info("Startup complete")

@app.on_event("shutdown")
def on_shutdown():
    try:
        app.state.profile_store.close()
    except Exception:
        pass
    graph_runtime.stop()
    logger.info("Shutdown complete")

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(memory.router)
