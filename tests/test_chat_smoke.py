from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_smoke():
    r = client.post("/chat/alice", json={"message": "remember that I like sources at the end"})
    assert r.status_code == 200
    assert "answer" in r.json()
