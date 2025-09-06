# app/api/routes/memory.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.deps import get_profile_store
from app.db.profile_store import ProfileStore

router = APIRouter(prefix="/memory", tags=["memory"])

class RememberBody(BaseModel):
    key: str
    value: str

@router.get("/{user_id}")
def get_memory(user_id: str, store: ProfileStore = Depends(get_profile_store)):
    return store.get_profile(user_id)

@router.post("/{user_id}/remember")
def remember(user_id: str, body: RememberBody, store: ProfileStore = Depends(get_profile_store)):
    store.upsert(user_id, {body.key: body.value})
    return {"saved": True, "key": body.key, "value": body.value}
