"""Actual synthetic tool execution and a denial; temporary data, no model calls."""

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from alembic import command
from alembic.config import Config
from pydantic import ValidationError


def main():
    with TemporaryDirectory(prefix="sentinel-evidence-demo-") as directory:
        database_url = f"sqlite:///{Path(directory) / 'demo.db'}"
        os.environ["WORKBENCH_DATABASE_URL"] = database_url
        backend = Path(__file__).resolve().parents[1]
        config = Config(str(backend / "alembic.ini"))
        config.set_main_option("script_location", str(backend / "migrations"))
        config.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(config, "head")

        # Import only after choosing the temporary store; never use the local bank.
        from app.assistant import make_bank_tools
        from app.evidence import EvidenceRecorder, read_events
        from app.store import engine

        try:
            runs = []
            for arguments in ({}, {"customer_id": "C-200"}):
                recorder = EvidenceRecorder.start()
                tool = make_bank_tools(defended=True, evidence=recorder)[0]
                try:
                    tool.invoke(arguments)
                except ValidationError:
                    pass  # Expected forged-argument denial; evidence records it.
                runs.append(read_events(recorder.run_id).model_dump(mode="json"))
            print(json.dumps({"execution": "actual_tools_no_model", "runs": runs}, indent=2))
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
