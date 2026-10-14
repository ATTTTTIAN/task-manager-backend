from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TaskDB, UserDB
from app.auth import create_access_token, get_current_user, password_hash

app = FastAPI(title="Task Manager API", version="0.3.0", description="Day 3: JWT and user isolation")

class RegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

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

class TaskPage(BaseModel):
    items: list[Task]
    total: int
    page: int
    page_size: int
    total_pages: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(payload: RegisterInput, db: Session = Depends(get_db)):
    if payload.username.startswith("__legacy_archive__"):
        raise HTTPException(422, "用户名不可用")
    user = UserDB(username=payload.username, password_hash=password_hash.hash(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "用户名已存在")
    db.refresh(user)
    return user

@app.post("/auth/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(UserDB).where(UserDB.username == form.username))
    if user is None or user.username.startswith("__legacy_archive__") or not password_hash.verify(form.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误", headers={"WWW-Authenticate": "Bearer"})
    return TokenOut(access_token=create_access_token(user.id))

@app.get("/auth/me", response_model=UserOut)
def me(current_user: UserDB = Depends(get_current_user)):
    return current_user

@app.post("/tasks", response_model=Task, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(422, "任务标题不能全为空格")
    task = TaskDB(title=title, description=payload.description, user_id=user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@app.get("/tasks", response_model=TaskPage)
def list_tasks(
    completed: bool | None = None,
    keyword: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at", pattern="^(created_at|id)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: UserDB = Depends(get_current_user),
):
    # 1. 只查询当前登录用户的任务
    stmt = select(TaskDB).where(TaskDB.user_id == user.id)

    # 2. 按完成状态筛选
    if completed is not None:
        stmt = stmt.where(TaskDB.completed == completed)

    # 3. 按标题关键词搜索
    if keyword and keyword.strip():
        stmt = stmt.where(TaskDB.title.contains(keyword.strip()))

    # 4. 统计筛选后的任务总数
    count_stmt = select(func.count()).select_from(
        stmt.order_by(None).subquery()
    )
    total = db.scalar(count_stmt) or 0

    # 5. 设置排序字段
    sort_column = (
        TaskDB.created_at
        if sort_by == "created_at"
        else TaskDB.id
    )

    if sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc(), TaskDB.id.desc())
    else:
        stmt = stmt.order_by(sort_column.asc(), TaskDB.id.asc())

    # 6. 分页查询
    offset = (page - 1) * page_size
    items = db.scalars(
        stmt.offset(offset).limit(page_size)
    ).all()

    # 7. 返回分页结果
    return TaskPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
def own_task(db: Session, task_id: int, user_id: int):
    task = db.scalar(select(TaskDB).where(TaskDB.id == task_id, TaskDB.user_id == user_id))
    if task is None:
        raise HTTPException(404, "任务不存在")
    return task

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: int, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user)):
    return own_task(db, task_id, user.id)

@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user)):
    task = own_task(db, task_id, user.id)
    changes = payload.model_dump(exclude_unset=True)
    if "title" in changes and (changes["title"] is None or not changes["title"].strip()):
        raise HTTPException(422, "任务标题不能为空")
    if "description" in changes and changes["description"] is None:
        raise HTTPException(422, "描述不能为 null")
    if "completed" in changes and changes["completed"] is None:
        raise HTTPException(422, "完成状态不能为 null")
    if "title" in changes:
        changes["title"] = changes["title"].strip()
    for key, value in changes.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db), user: UserDB = Depends(get_current_user)):
    task = own_task(db, task_id, user.id)
    db.delete(task)
    db.commit()
    return Response(status_code=204)
