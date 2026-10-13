$ErrorActionPreference = 'Stop'
Set-Location 'D:\PythonProjects\task-manager-backend'
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw '未找到 .venv，请先创建虚拟环境' }
& .\.venv\Scripts\python.exe -m pip install fastapi 'uvicorn[standard]' httpx pytest
New-Item -ItemType Directory -Force -Path 'app' | Out-Null
Set-Content -Path 'app\__init__.py' -Value '' -Encoding UTF8
@'
from datetime import datetime, timezone
from threading import Lock
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, ConfigDict

app = FastAPI(title="Task Manager API", version="0.1.0", description="15天后端项目冲刺 Day 1")

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

_tasks: dict[int, Task] = {}
_next_id = 1
_lock = Lock()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate):
    global _next_id
    if not payload.title.strip():
        raise HTTPException(status_code=422, detail="任务标题不能全为空格")
    with _lock:
        task = Task(id=_next_id, title=payload.title.strip(), description=payload.description,
                    completed=False, created_at=datetime.now(timezone.utc))
        _tasks[_next_id] = task
        _next_id += 1
        return task

@app.get("/tasks", response_model=list[Task])
def list_tasks(completed: bool | None = None, skip: int = Query(default=0, ge=0),
               limit: int = Query(default=20, ge=1, le=100)):
    with _lock:
        items = list(_tasks.values())
    if completed is not None:
        items = [t for t in items if t.completed == completed]
    return items[skip:skip + limit]

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int):
    with _lock:
        task = _tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate):
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes and (changes["title"] is None or not changes["title"].strip()):
        raise HTTPException(status_code=422, detail="任务标题不能为空")
    if "description" in changes and changes["description"] is None:
        raise HTTPException(status_code=422, detail="描述不能为 null")
    if "completed" in changes and changes["completed"] is None:
        raise HTTPException(status_code=422, detail="完成状态不能为 null")
    if "title" in changes:
        changes["title"] = changes["title"].strip()
    with _lock:
        task = _tasks.get(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        updated = task.model_copy(update=changes)
        _tasks[task_id] = updated
        return updated

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    with _lock:
        if task_id not in _tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        del _tasks[task_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
'@ | Set-Content -Path 'app\api.py' -Encoding UTF8
@'
from app.api import app
'@ | Set-Content -Path 'main.py' -Encoding UTF8
@'
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
'@ | Set-Content -Path 'test_api.py' -Encoding UTF8
& .\.venv\Scripts\python.exe -m pip freeze | Set-Content -Path 'requirements.txt' -Encoding UTF8
Write-Host '项目代码创建完成。运行: .\.venv\Scripts\python.exe -m pytest -q'
Write-Host '启动服务: .\.venv\Scripts\python.exe -m uvicorn app.api:app --reload'
