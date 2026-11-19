"""
Database session configuration
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, with_loader_criteria
from sqlalchemy.pool import QueuePool
from typing import Generator

from app.core.config import settings

# Create engine with optimized pool settings
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_pre_ping=True,      # Verify connections before use
    pool_size=20,            # Base pool size
    max_overflow=30,         # Additional connections when pool is full
    pool_timeout=30,         # Seconds to wait for connection
    pool_recycle=1800,       # Recycle connections after 30 minutes
    echo=False,              # Disable SQL logging in production
)


# Optimize SQLAlchemy queries
@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Add query timeout for PostgreSQL (30 seconds)
    if settings.database_url.startswith("postgresql"):
        cursor.execute("SET statement_timeout = 30000")


# Session factory with optimizations
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Don't expire objects after commit (reduces queries)
)


def get_db() -> Generator:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@event.listens_for(Session, "do_orm_execute")
def exclude_deleted_workspaces(state):
    """Hide logically removed workspaces in web requests and background jobs alike."""
    if state.is_select or state.is_update or state.is_delete:
        from app.db.models.workspace import Workspace
        state.statement = state.statement.options(with_loader_criteria(Workspace, Workspace.deleted_at.is_(None), include_aliases=True))
