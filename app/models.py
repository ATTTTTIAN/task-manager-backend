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
