"""Regression checks for CI's isolated database and no-provider-call guarantee."""

import asyncio
from pathlib import Path

import httpx
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.store import DATABASE_URL, engine


def test_suite_uses_a_temporary_database_with_actual_migrations():
    path = Path(DATABASE_URL.removeprefix("sqlite:///"))
    assert path.parent.name.startswith("sentinel-tests-")
    assert {"campaigns", "run_events", "transactions", "alembic_version"} <= set(
        inspect(engine).get_table_names()
    )
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            ScriptDirectory.from_config(config).get_current_head()
        )


def test_real_sync_http_requests_fail_before_network_access():
    with httpx.Client() as client, pytest.raises(pytest.fail.Exception, match="forbidden"):
        client.get("https://api.openai.com/v1/models")


def test_real_async_http_requests_fail_before_network_access():
    async def attempt_request():
        async with httpx.AsyncClient() as client:
            await client.get("https://api.openai.com/v1/models")

    with pytest.raises(pytest.fail.Exception, match="forbidden"):
        asyncio.run(attempt_request())
