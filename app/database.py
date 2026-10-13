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
