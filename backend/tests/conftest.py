"""A fresh migrated database and zero real provider calls for the default suite."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pytest
from alembic import command
from alembic.config import Config

# Set these before test collection imports app.store/app.main. Never use a
# developer's database or load an external credential file in the default suite.
_test_directory = TemporaryDirectory(prefix="sentinel-tests-")
_database_url = f"sqlite:///{Path(_test_directory.name) / 'test.db'}"
os.environ["WORKBENCH_DATABASE_URL"] = _database_url
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("OPENAI_ENV_FILE", None)


def pytest_sessionstart(session):
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    config.set_main_option("sqlalchemy.url", _database_url)
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def block_provider_requests(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail("Real provider HTTP calls are forbidden in the default test suite")

    async def blocked_async(*args, **kwargs):
        pytest.fail("Real provider HTTP calls are forbidden in the default test suite")

    # TestClient uses its own in-process transport and remains usable.
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked_async)


def pytest_sessionfinish(session, exitstatus):
    from app.store import engine

    engine.dispose()
    _test_directory.cleanup()
