"""
Database Engine & Async Session Management
Provides async database connections, session lifecycle, and automatic table schema generation.
Compatible with SQLite (aiosqlite) and PostgreSQL (asyncpg).
"""

import os
from pathlib import Path
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.logging import logger
from app.db.models import Base

# Ensure backend storage directory exists
storage_dir = Path(__file__).resolve().parent.parent.parent / "storage"
storage_dir.mkdir(parents=True, exist_ok=True)

# Format database URL
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    # Ensure SQLite DB file is placed safely in backend/storage
    db_file = (storage_dir / "road_detection.db").resolve()
    # Replace backslashes with forward slashes for standard URI format
    posix_path = db_file.as_posix()
    async_db_url = f"sqlite+aiosqlite:///{posix_path}"
    sync_db_url = f"sqlite:///{posix_path}"
else:
    async_db_url = db_url
    sync_db_url = db_url.replace("+aiosqlite", "").replace("+asyncpg", "")

logger.info(f"Connecting to database at: {sync_db_url}")

# Create Async Engine
async_engine: AsyncEngine = create_async_engine(
    async_db_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in async_db_url else {}
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

# Sync Engine & Session Factory (for background ingestion threads)
sync_engine = create_engine(
    sync_db_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in sync_db_url else {}
)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autoflush=False
)

# Enable WAL Mode for SQLite concurrency
if "sqlite" in sync_db_url:
    @event.listens_for(sync_engine, "connect")
    def set_sync_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


async def init_db():
    """Initializes database schema and ensures all tables exist."""
    try:
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
        raise e


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async database access outside of request lifecycle."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Session:
    """Returns a synchronous database session for background threads."""
    return SyncSessionLocal()
