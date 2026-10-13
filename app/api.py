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
