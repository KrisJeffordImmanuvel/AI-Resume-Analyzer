"""Database migrations (Alembic): new databases, databases from before migrations, and drift."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

import models  # noqa: F401  (registers every table)
from database import BASELINE_REVISION, MIGRATIONS_DIR, Base, init_db, make_engine


def head_revision() -> str:
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return ScriptDirectory.from_config(cfg).get_current_head()


def current_revision(engine) -> str:
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def test_new_database_gets_every_table_at_the_latest_version(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'new.db').as_posix()}")
    init_db(engine)
    assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())
    assert current_revision(engine) == head_revision()
    init_db(engine)  # safe on every start
    assert current_revision(engine) == head_revision()


def test_database_from_before_migrations_keeps_its_data(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    # An older app version: only some tables, created without migrations, with data in them.
    Base.metadata.tables["analyses"].create(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO analyses (created_at, resume_filename, resume_text, jd_source, jd_text, score, result) "
                "VALUES ('2026-01-01', 'cv.txt', 'Python', 'paste', 'Python', 100, '{}')"
            )
        )
    init_db(engine)
    assert set(Base.metadata.tables) <= set(inspect(engine).get_table_names())  # missing tables added
    with engine.connect() as conn:
        assert conn.execute(text("SELECT resume_filename FROM analyses")).scalar() == "cv.txt"
    assert current_revision(engine) == head_revision()


def test_migrations_match_the_models(tmp_path):
    # Fails when models.py changes without a new migration: run
    # "alembic revision --autogenerate -m ..." in the backend folder.
    engine = make_engine(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    init_db(engine)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []


def test_baseline_is_the_first_migration():
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    base = ScriptDirectory.from_config(cfg).get_base()
    assert base == BASELINE_REVISION
