"""Run once after backing up MySQL. Existing tasks are assigned to a disabled archive user."""
from sqlalchemy import inspect, text
from app.database import Base, engine
from app.models import UserDB, TaskDB  # noqa: F401
from app.auth import password_hash
import secrets

Base.metadata.create_all(bind=engine, tables=[UserDB.__table__])
with engine.begin() as conn:
    cols = {col["name"] for col in inspect(conn).get_columns("tasks")}
    if "user_id" not in cols:
        conn.execute(text("ALTER TABLE tasks ADD COLUMN user_id INT NULL"))

with engine.begin() as conn:
    existing = conn.execute(text("SELECT id FROM users WHERE username = :name"), {"name": "__legacy_archive__"}).scalar()
    if existing is None:
        conn.execute(text("INSERT INTO users (username, password_hash) VALUES (:name, :hash)"), {"name": "__legacy_archive__", "hash": password_hash.hash(secrets.token_urlsafe(48))})
    archive_id = conn.execute(text("SELECT id FROM users WHERE username = :name"), {"name": "__legacy_archive__"}).scalar_one()
    conn.execute(text("UPDATE tasks SET user_id = :uid WHERE user_id IS NULL"), {"uid": archive_id})

with engine.begin() as conn:
    cols = {col["name"]: col for col in inspect(conn).get_columns("tasks")}
    if cols["user_id"]["nullable"]:
        conn.execute(text("ALTER TABLE tasks MODIFY COLUMN user_id INT NOT NULL"))
    indexes = {idx["name"] for idx in inspect(conn).get_indexes("tasks")}
    if "ix_tasks_user_id" not in indexes:
        conn.execute(text("CREATE INDEX ix_tasks_user_id ON tasks (user_id)"))
    fks = inspect(conn).get_foreign_keys("tasks")
    if not any(fk["constrained_columns"] == ["user_id"] for fk in fks):
        conn.execute(text("ALTER TABLE tasks ADD CONSTRAINT fk_tasks_user_id FOREIGN KEY (user_id) REFERENCES users(id)"))
print("Day 3 migration complete. Old tasks belong to disabled archive user.")
