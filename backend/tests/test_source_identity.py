import subprocess
from pathlib import Path

import pytest

from app import source_identity as source


@pytest.fixture()
def checkout(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.email", "test@example.test")
    git("config", "user.name", "Test")
    for path in source._TARGET_FILES:
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((source._ROOT / path).read_bytes())
    git("add", "backend")
    git("commit", "-qm", "Built-in assistant")
    monkeypatch.setattr(source, "_ROOT", tmp_path)
    monkeypatch.setattr(source, "_LOADED_BYTES", source._working_bytes())
    return tmp_path, git


def test_pinned_excerpts_survive_checkout_change(checkout):
    root, git = checkout
    (root / "README.md").write_text("Unrelated local notes")
    receipt = source.source_receipt()
    assert receipt["status"] == "verified"
    assert receipt["revision"] == git("rev-parse", "HEAD")

    path = root / "backend/app/gateway.py"
    path.write_text("# updated version\n" + path.read_text())
    assert source.source_receipt()["status"] == "unavailable"
    git("commit", "-qam", "Update gateway")
    # Files on disk now agree with HEAD, but differ from this process's loaded source.
    assert source.source_receipt()["status"] == "unavailable"

    excerpts = source.verified_sources(receipt)
    assert {e["id"] for e in excerpts} == {"gateway.scope", "bank.lab_read", "runtime.dispatch"}
    for excerpt in excerpts:
        contents = git("show", f"{receipt['revision']}:{excerpt['path']}").splitlines()
        assert excerpt["text"] == "\n".join(contents[excerpt["start"] - 1 : excerpt["end"]])
        assert len(excerpt["text"]) <= 2000

    assert source.verified_sources({**receipt, "digest": "0" * 64}) == []
    assert source.verified_sources({**receipt, "revision": "f" * 40}) == []


@pytest.mark.parametrize("receipt", [None, {}, {"status": "verified", "revision": "../etc"}])
def test_unavailable_receipts_do_not_resolve(receipt):
    assert source.verified_sources(receipt) == []


def test_missing_git_does_not_stop_assistant(checkout, monkeypatch):
    monkeypatch.setenv("PATH", str(Path("/nonexistent")))
    assert source.source_receipt() == {"status": "unavailable", "revision": None, "digest": None}
