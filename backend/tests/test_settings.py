import os

import pytest

from app.settings import load_external_env_file


def test_external_env_file_must_be_private(tmp_path, monkeypatch):
    env_file = tmp_path / "private.env"
    env_file.write_text("OPENAI_API_KEY=synthetic-test-secret\n")
    env_file.chmod(0o644)
    monkeypatch.setenv("OPENAI_ENV_FILE", str(env_file))
    with pytest.raises(RuntimeError, match="private"):
        load_external_env_file()


def test_explicit_private_env_file_loads_without_changing_the_file(tmp_path, monkeypatch):
    env_file = tmp_path / "private.env"
    content = "OPENAI_API_KEY=synthetic-test-secret\n"
    env_file.write_text(content)
    env_file.chmod(0o600)
    monkeypatch.setenv("OPENAI_ENV_FILE", str(env_file))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    load_external_env_file()
    assert os.environ["OPENAI_API_KEY"] == "synthetic-test-secret"
    assert env_file.read_text() == content
