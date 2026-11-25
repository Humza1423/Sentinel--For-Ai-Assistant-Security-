"""Identify the built-in assistant's reviewed source at a local Git revision."""

import hashlib
import re
import subprocess
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TARGET_FILES = tuple(
    f"backend/app/{name}.py"
    for name in (
        "assistant",
        "bank",
        "defenses",
        "evidence",
        "execution_receipt",
        "execution_control",
        "fixture_model",
        "gateway",
        "live_model",
        "runtime",
        "runtime_context",
        "store",
        "target_contracts",
        "targets",
    )
)
# Trusted anchors delimit small snippets; user/model input cannot choose paths.
_SNIPPETS = (
    ("gateway.scope", "backend/app/gateway.py", 'elif profile == "vulnerable_lookup_v1":', 6),
    ("bank.lab_read", "backend/app/bank.py", "class VulnerableSnapshotLabRepository:", 16),
    ("runtime.dispatch", "backend/app/runtime.py", "context_event = recorder.append(", 31),
)


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", "--no-replace-objects", "-C", str(_ROOT), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=2,
    ).stdout


def _working_bytes() -> tuple[bytes, ...]:
    return tuple((_ROOT / path).read_bytes() for path in _TARGET_FILES)


try:
    _LOADED_BYTES = _working_bytes()
except OSError:
    _LOADED_BYTES = ()


@lru_cache(maxsize=32)
def _tree(root: Path, revision: str) -> dict[str, str]:
    # Only immutable object names are cached. Include the repo for isolated tests.
    result = {}
    for row in _git("ls-tree", "-r", revision, "--", *_TARGET_FILES).decode().splitlines():
        metadata, path = row.split("\t")
        mode, kind, oid = metadata.split()
        if kind == "blob" and mode in ("100644", "100755"):
            result[path] = oid
    if set(result) != set(_TARGET_FILES):
        raise ValueError("Built-in target source is incomplete")
    return result


def _tree_digest(tree: dict[str, str]) -> str:
    return hashlib.sha256("".join(f"{p}\0{tree[p]}\n" for p in _TARGET_FILES).encode()).hexdigest()


def source_receipt() -> dict:
    """Bind source loaded at startup to a commit, tolerating unrelated local edits."""
    try:
        revision = _git("rev-parse", "--verify", "HEAD^{commit}").decode().strip()
        tree = _tree(_ROOT, revision)
        contents = _working_bytes()
        if contents == _LOADED_BYTES:
            algorithm = "sha256" if len(revision) == 64 else "sha1"
            for path, data in zip(_TARGET_FILES, contents, strict=True):
                header = f"blob {len(data)}\0".encode()
                if hashlib.new(algorithm, header + data).hexdigest() != tree[path]:
                    break
            else:
                return {"status": "verified", "revision": revision, "digest": _tree_digest(tree)}
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return {"status": "unavailable", "revision": None, "digest": None}


def verified_sources(receipt: object) -> list[dict]:
    """Resolve bounded excerpts from the recorded tree, never from the working tree."""
    if not isinstance(receipt, dict) or receipt.get("status") != "verified":
        return []
    revision = receipt.get("revision")
    if not isinstance(revision, str) or not re.fullmatch(
        r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision
    ):
        return []
    try:
        tree = _tree(_ROOT, revision)
        if receipt.get("digest") != _tree_digest(tree):
            return []
        excerpts = []
        for identifier, path, anchor, size in _SNIPPETS:
            lines = _git("cat-file", "blob", tree[path]).decode().splitlines()
            starts = [i for i, line in enumerate(lines) if line.strip() == anchor]
            if len(starts) != 1:
                continue
            start = starts[0]
            end = min(start + size, len(lines))
            snippet = "\n".join(lines[start:end])
            if len(snippet) <= 2000:
                excerpts.append(
                    {
                        "id": identifier,
                        "path": path,
                        "start": start + 1,
                        "end": end,
                        "text": snippet,
                    }
                )
        return excerpts
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
