# app/api/deps.py
from fastapi import Request
from app.db.profile_store import ProfileStore

def get_profile_store(request: Request) -> ProfileStore:
    """Return the process-wide ProfileStore stored on app.state."""
    return request.app.state.profile_store

def get_graph(request: Request):
    """Return the compiled LangGraph app stored on app.state."""
    return request.app.state.graph
