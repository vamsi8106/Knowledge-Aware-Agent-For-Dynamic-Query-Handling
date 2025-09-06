from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.api.deps import get_graph
from app.services.graph_runtime import current_user_id_ctx
from app.core.tracking import traceable

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatBody(BaseModel):
    message: str

@router.post("/{user_id}")
@traceable(name="http_chat_turn")
def chat(user_id: str, body: ChatBody, graph = Depends(get_graph)):
    # scope the user id to this request
    token = current_user_id_ctx.set(user_id)
    try:
        # one-shot run (simpler than streaming for Postman)
        result = graph.invoke(
            {"messages": [("user", body.message)]},
            config={"configurable": {"thread_id": user_id}},
        )
        msgs = result.get("messages", [])
        final = None
        if msgs:
            last = msgs[-1]
            final = getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else None)
        return {"answer": final}
    finally:
        current_user_id_ctx.reset(token)
