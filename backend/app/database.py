import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Architecture calls for PostgreSQL in deployment (see docker-compose.yml).
# DATABASE_URL is read from the environment so the same code runs against
# Postgres in Docker or SQLite for zero-setup local development/testing.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dockit.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
