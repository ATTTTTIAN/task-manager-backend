$ErrorActionPreference = 'Stop'
Set-Location 'D:\PythonProjects\task-manager-backend'
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw '找不到 .venv Python' }
& .\.venv\Scripts\python.exe -m pip install sqlalchemy pymysql cryptography python-dotenv
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
$backup = 'app\api.day1.backup.py'
if (-not (Test-Path $backup)) { Copy-Item 'app\api.py' $backup }
$dbPassword = Read-Host '输入 taskuser 的 MySQL 密码（输入时可见）'
if (-not $dbPassword) { throw '密码不能为空' }
@"
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=task_manager
DB_USER=taskuser
DB_PASSWORD=$dbPassword
"@ | Set-Content -Path '.env' -Encoding UTF8
$gitignore = if (Test-Path '.gitignore') { Get-Content '.gitignore' -Raw } else { '' }
foreach ($entry in @('.env','.venv/','__pycache__/','.pytest_cache/','*.pyc','app/api.day1.backup.py')) {
    if (($gitignore -split "`r?`n") -notcontains $entry) { Add-Content -Path '.gitignore' -Value $entry -Encoding UTF8 }
}
@'
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

class Base(DeclarativeBase):
    pass

def database_url():
    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER", "taskuser"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "task_manager"),
        query={"charset": "utf8mb4"},
    )

engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db
'@ | Set-Content 'app\database.py' -Encoding UTF8
@'
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class TaskDB(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc))
'@ | Set-Content 'app\models.py' -Encoding UTF8
@'
from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import Base, engine, get_db
from app.models import TaskDB

app = FastAPI(title="Task Manager API", version="0.2.0", description="Day 2: MySQL + SQLAlchemy")

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    completed: bool | None = None

class Task(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    completed: bool
    created_at: datetime

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="任务标题不能全为空格")
    task = TaskDB(title=title, description=payload.description)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@app.get("/tasks", response_model=list[Task])
def list_tasks(completed: bool | None = None, skip: int = Query(0, ge=0),
               limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(TaskDB).order_by(TaskDB.id)
    if completed is not None:
        stmt = stmt.where(TaskDB.completed == completed)
    return db.scalars(stmt.offset(skip).limit(limit)).all()

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(TaskDB, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(TaskDB, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes and (changes["title"] is None or not changes["title"].strip()):
        raise HTTPException(status_code=422, detail="任务标题不能为空")
    if "description" in changes and changes["description"] is None:
        raise HTTPException(status_code=422, detail="描述不能为 null")
    if "completed" in changes and changes["completed"] is None:
        raise HTTPException(status_code=422, detail="完成状态不能为 null")
    if "title" in changes:
        changes["title"] = changes["title"].strip()
    for key, value in changes.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(TaskDB, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
'@ | Set-Content 'app\api.py' -Encoding UTF8
@'
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
'@ | Set-Content 'test_api.py' -Encoding UTF8
& .\.venv\Scripts\python.exe -m pip freeze | Set-Content 'requirements.txt' -Encoding UTF8
Write-Host 'Day 2 文件生成完毕。执行: .\.venv\Scripts\python.exe -m pytest -q'
Write-Host '启动服务: .\.venv\Scripts\python.exe -m uvicorn app.api:app --reload'
