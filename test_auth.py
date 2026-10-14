import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production-123456789")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.api import app
from app.database import Base, get_db
from app import models  # noqa: F401

engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)

def override_db():
    with TestingSession() as db:
        yield db

app.dependency_overrides[get_db] = override_db
client = TestClient(app)

def test_auth_isolation():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    assert client.get("/health").status_code == 200
    assert client.get("/tasks").status_code == 401
    for username in ("alice", "bob"):
        r = client.post("/auth/register", json={"username": username, "password": "pass12345"})
        assert r.status_code == 201, r.text
    assert client.post("/auth/register", json={"username": "alice", "password": "pass12345"}).status_code == 409
    tokens = {}
    for username in ("alice", "bob"):
        r = client.post("/auth/login", data={"username": username, "password": "pass12345"})
        assert r.status_code == 200, r.text
        tokens[username] = {"Authorization": "Bearer " + r.json()["access_token"]}
    assert client.post("/auth/login", data={"username": "alice", "password": "wrongpass"}).status_code == 401
    assert client.get("/auth/me", headers=tokens["alice"]).json()["username"] == "alice"
    r = client.post("/tasks", json={"title": "private"}, headers=tokens["alice"])
    assert r.status_code == 201, r.text
    task_id = r.json()["id"]
    assert len(client.get("/tasks", headers=tokens["alice"]).json()) == 1
    assert client.get("/tasks", headers=tokens["bob"]).json() == []
    assert client.get(f"/tasks/{task_id}", headers=tokens["bob"]).status_code == 404
    assert client.patch(f"/tasks/{task_id}", json={"completed": True}, headers=tokens["bob"]).status_code == 404
    assert client.delete(f"/tasks/{task_id}", headers=tokens["bob"]).status_code == 404
    assert client.patch(f"/tasks/{task_id}", json={"completed": True}, headers=tokens["alice"]).json()["completed"] is True
    assert client.delete(f"/tasks/{task_id}", headers=tokens["alice"]).status_code == 204
