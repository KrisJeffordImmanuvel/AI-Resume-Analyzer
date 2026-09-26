"""Alembic environment. The app runs migrations itself at start (database.init_db);
developers create new ones with: alembic revision --autogenerate -m "what changed"
"""

from alembic import context
from sqlalchemy import engine_from_config, pool

import models  # noqa: F401  (registers every table on Base.metadata)
from config import get_settings
from database import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url, target_metadata=target_metadata, literal_binds=True, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")  # given by init_db when the app starts
    if connection is not None:
        _run(connection)
        return
    engine = engine_from_config(
        {"sqlalchemy.url": get_settings().database_url}, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with engine.connect() as conn:
        _run(conn)


def _run(connection) -> None:
    # render_as_batch: SQLite can change columns only by rebuilding the table; batch mode does that.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
