import os

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-secret-key-not-for-production-123456789",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import app
from app.database import Base, get_db
from app import models  # noqa: F401


@pytest.fixture
def client():
    # 每个测试使用独立的 SQLite 内存数据库
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=test_engine)

    TestingSession = sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )

    def override_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        test_engine.dispose()


@pytest.fixture
def auth_headers(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 201, response.text

    response = client.post(
        "/auth/login",
        data={
            "username": "testuser",
            "password": "TestPass123!",
        },
    )
    assert response.status_code == 200, response.text

    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}

from app import cache


@pytest.fixture(autouse=True)
def disable_real_redis(monkeypatch):
    """自动化测试默认不连接真实 Redis。"""
    monkeypatch.setattr(
        cache,
        "get_task_cache_version",
        lambda user_id: None,
    )
    monkeypatch.setattr(
        cache,
        "invalidate_task_cache",
        lambda user_id: None,
    )