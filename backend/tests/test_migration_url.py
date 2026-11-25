"""Explicit migration destinations must not replace the configured database."""

from argparse import Namespace
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_explicit_database_url_migrates_only_the_selected_database(tmp_path, monkeypatch):
    backend = Path(__file__).resolve().parents[1]
    configured = f"sqlite:///{tmp_path / 'configured.db'}"
    selected = f"sqlite:///{tmp_path / 'selected.db'}"
    environment = f"sqlite:///{tmp_path / 'environment.db'}"
    monkeypatch.setenv("WORKBENCH_DATABASE_URL", environment)
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    config.set_main_option("sqlalchemy.url", configured)
    configured_engine = create_engine(configured)
    with configured_engine.begin() as db:
        db.execute(text("CREATE TABLE existing_record (value TEXT)"))
        db.execute(text("INSERT INTO existing_record VALUES ('preserved')"))
    config.cmd_opts = Namespace(x=[f"database_url={selected}"])
    command.upgrade(config, "head")
    selected_engine = create_engine(selected)
    assert "chat_sessions" in inspect(selected_engine).get_table_names()
    assert "assessments" in inspect(selected_engine).get_table_names()
    with configured_engine.connect() as db:
        assert db.execute(text("SELECT value FROM existing_record")).scalar_one() == "preserved"
    assert "alembic_version" not in inspect(configured_engine).get_table_names()
    assert not (tmp_path / "environment.db").exists()
    selected_engine.dispose()
    configured_engine.dispose()
