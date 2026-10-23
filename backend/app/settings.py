"""Small, explicit environment loader; secret values are never logged or serialized."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from dotenv import load_dotenv


def load_external_env_file() -> None:
    """Load a user-selected env file without copying it into the repository.

    The file must be explicitly selected with OPENAI_ENV_FILE and private to the
    current user on POSIX systems. Existing process variables take precedence.
    """
    selected_file = os.getenv("OPENAI_ENV_FILE")
    if not selected_file:
        return
    path = Path(selected_file).expanduser()
    if not path.is_file():
        raise RuntimeError("OPENAI_ENV_FILE does not point to a readable file.")
    if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise RuntimeError("The selected environment file must be private (chmod 600).")
    load_dotenv(path, override=False)
