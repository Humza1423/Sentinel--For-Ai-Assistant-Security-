from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.budget import UsageBroker
from app.store import CampaignRow


def test_usage_migration_preserves_existing_campaigns(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0005_chat_sessions")
    engine = create_engine(url)
    sessions = sessionmaker(engine)
    with sessions.begin() as db:
        db.add(
            CampaignRow(
                campaign_id="legacy", created_at=datetime.now(UTC), report_json='{"original":true}'
            )
        )
    command.upgrade(config, "head")
    with sessions() as db:
        assert db.get(CampaignRow, "legacy").report_json == '{"original":true}'
    summary = UsageBroker(sessions).summary()
    assert summary["initialized"] is False
    assert summary["remaining_micro_usd"] is None
    engine.dispose()
