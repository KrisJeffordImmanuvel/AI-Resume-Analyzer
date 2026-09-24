"""SQLAlchemy engine/session setup. Tables are created on backend start."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for all ORM models (added in later phases)."""


def make_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    """Create any missing tables. Safe to call on every start."""
    Base.metadata.create_all(bind=engine)
    # Touch the database so the SQLite file exists even before any models do.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def check_db(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
