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
