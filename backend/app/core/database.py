import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

# Engine setup
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # Ensure SQLite database directory exists
    if ":///" in settings.DATABASE_URL:
        db_raw_path = settings.DATABASE_URL.split(":///", 1)[1]
        db_file = Path(db_raw_path).resolve()
        db_file.parent.mkdir(parents=True, exist_ok=True)

# Ensure storage directory exists
try:
    Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
except Exception:
    pass

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

