# app/tools/memory_tools.py
from __future__ import annotations
from typing import Any
from pydantic import BaseModel
from langchain.tools import tool
from app.db.profile_store import ProfileStore

# This is set on startup from app.main
PROFILE_STORE: ProfileStore | None = None

def set_profile_store(store: ProfileStore) -> None:
    """Inject the process-wide ProfileStore instance used by the memory tools."""
    global PROFILE_STORE
    PROFILE_STORE = store

class RememberSchema(BaseModel):
    key: str
    value: Any  # accept any JSON-serializable type

@tool(args_schema=RememberSchema)
def remember_tool(key: str, value: Any) -> str:
    """Save or update a user-specific fact or preference in persistent memory (SQLite user_profile)."""
    if PROFILE_STORE is None:
        return "Memory store not initialized."
    # Late import to avoid circulars on module import
    from app.services.graph_runtime import current_user_id_ctx
    uid = current_user_id_ctx.get()
    PROFILE_STORE.upsert(uid, {key: value})
    return f"Saved: {key} = {value}"

class RecallSchema(BaseModel):
    key: str

@tool(args_schema=RecallSchema)
def recall_tool(key: str) -> str:
    """Fetch a previously saved user-specific fact or preference from persistent memory."""
    if PROFILE_STORE is None:
        return "Memory store not initialized."
    from app.services.graph_runtime import current_user_id_ctx
    uid = current_user_id_ctx.get()
    val = PROFILE_STORE.get_profile(uid).get(key)
    return val if val is not None else f"No value saved for '{key}'."

