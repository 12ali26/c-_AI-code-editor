from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.db_models import Base


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./storage/reserving.db")


def create_app_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_database_url()
    if url.startswith("sqlite:///"):
        db_path = url.replace("sqlite:///", "", 1)
        if db_path not in {":memory:", ""}:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = create_app_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(target_engine: Engine = engine) -> None:
    Base.metadata.create_all(bind=target_engine)

