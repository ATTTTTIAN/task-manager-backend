import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api import app
from app.database import Base, get_db
from app.models import TaskDB

@pytest.fixture
def client():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    def override_db():
        with Session() as db:
            yield db
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}

def test_task_lifecycle(client):
    r = client.post("/tasks", json={"title": "学习 SQLAlchemy", "description": "数据库持久化"})
    assert r.status_code == 201, r.text
    task_id = r.json()["id"]
    assert client.get(f"/tasks/{task_id}").status_code == 200
    assert any(t["id"] == task_id for t in client.get("/tasks").json())
    r = client.patch(f"/tasks/{task_id}", json={"completed": True})
    assert r.status_code == 200 and r.json()["completed"] is True
    assert len(client.get("/tasks?completed=true").json()) == 1
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404

def test_validation(client):
    assert client.post("/tasks", json={"title": "   "}).status_code == 422
    assert client.post("/tasks", json={"title": 123}).status_code == 422
    assert client.get("/tasks?limit=101").status_code == 422
    assert client.post("/tasks", json={"title": "OK"}).status_code == 201
    assert client.patch("/tasks/1", json={"completed": None}).status_code == 422
