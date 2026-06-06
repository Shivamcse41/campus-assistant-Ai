"""
app/database.py
───────────────
SQLAlchemy engine, session factory, and base class for MySQL.
All ORM models inherit from `Base`.
All route handlers get a DB session via the `get_db` dependency.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# pool_pre_ping=True automatically reconnects on stale connections.
# pool_recycle=3600 recycles connections every hour (recommended for MySQL).
engine = create_engine(
    settings.MYSQL_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,  # Set to True to log all SQL queries (useful for debugging)
)

# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Declarative Base ──────────────────────────────────────────────────────────
Base = declarative_base()


# ── FastAPI Dependency ────────────────────────────────────────────────────────
def get_db():
    """
    Yields a database session for each request and closes it when done.
    Usage in route:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
