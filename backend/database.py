"""SQLAlchemy engine/session setup. The database is brought up to date (migrated) on start."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for all ORM models (added in later phases)."""


def normalize_url(database_url: str) -> str:
    """Hosted databases (Neon, Render) give postgres:// or postgresql:// addresses; use the psycopg driver."""
    for prefix in ("postgres://", "postgresql://"):
        if database_url.startswith(prefix):
            return "postgresql+psycopg://" + database_url[len(prefix) :]
    return database_url


def make_engine(database_url: str) -> Engine:
    database_url = normalize_url(database_url)
    if database_url.startswith("sqlite"):
        return create_engine(database_url, connect_args={"check_same_thread": False})
    # A hosted database may close idle connections (Neon sleeps after a few minutes): test each before use.
    return create_engine(database_url, pool_pre_ping=True)


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
# The first migration: the tables as they were before migrations were introduced.
BASELINE_REVISION = "0001"


def _alembic_config(connection) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.attributes["connection"] = connection
    return cfg


def init_db(engine: Engine) -> None:
    """Bring the database up to date. Safe to call on every start; existing data is kept."""
    with engine.begin() as connection:
        cfg = _alembic_config(connection)
        tables = set(inspect(connection).get_table_names())
        if "alembic_version" not in tables and "analyses" in tables:
            # A database from before migrations existed: add any tables it lacks (as the app
            # used to on start), then record that it matches the first migration.
            import models  # noqa: F401  (registers every table)

            Base.metadata.create_all(bind=connection)
            command.stamp(cfg, BASELINE_REVISION)
        command.upgrade(cfg, "head")


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def check_db(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
