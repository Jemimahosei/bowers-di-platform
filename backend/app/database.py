"""Database setup.

DATABASE_URL defaults to a local SQLite file (``sqlite:///./bowers.db``).
Set DATABASE_URL to a Postgres URL for shared/multi-user deployments,
e.g. a Neon Postgres URL on Render:

    DATABASE_URL=postgresql://user:pass@host:5432/db uvicorn app.main:app

The models use only portable column types, so the same code runs on both.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./bowers.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # SQLite needs this flag for use with FastAPI's threaded server.
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
