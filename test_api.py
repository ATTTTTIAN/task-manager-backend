from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_task_lifecycle():
    r = client.post("/tasks", json={"title": "学习 FastAPI", "description": "完成 CRUD"})
    assert r.status_code == 201
    task_id = r.json()["id"]
    assert client.get(f"/tasks/{task_id}").status_code == 200
    assert any(t["id"] == task_id for t in client.get("/tasks").json())
    r = client.patch(f"/tasks/{task_id}", json={"completed": True})
    assert r.status_code == 200 and r.json()["completed"] is True
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404

def test_validation():
    assert client.post("/tasks", json={"title": "   "}).status_code == 422
    assert client.post("/tasks", json={"title": 123}).status_code == 422
    assert client.get("/tasks?limit=101").status_code == 422
