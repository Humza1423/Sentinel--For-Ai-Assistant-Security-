import json
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_upgrade_preserves_existing_campaign_events_and_bank_rows(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "migrations"))
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0002_synthetic_transactions")
    engine = create_engine(database_url)
    legacy_report = json.dumps({"legacy": "preserved"})
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO campaigns (campaign_id, created_at, report_json) "
                "VALUES ('old-campaign', '2026-10-23T12:00:00', :report)"
            ),
            {"report": legacy_report},
        )
        connection.execute(
            text(
                "INSERT INTO run_events (campaign_id, phase, sequence, event_json) "
                "VALUES ('old-campaign', 'baseline', 1, '{}')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO transactions "
                "(transaction_id, customer_id, merchant, amount, date, memo, memo_provenance) "
                "VALUES ('old-transaction', 'C-own', 'Existing', 12.34, '2026-10-22', 'keep me', 'external_untrusted')"
            )
        )
    command.upgrade(config, "head")
    assert {"observed_runs", "observed_events"} <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT report_json FROM campaigns")) == legacy_report
        assert connection.scalar(text("SELECT count(*) FROM run_events")) == 1
        assert connection.scalar(text("SELECT memo FROM transactions")) == "keep me"
        assert connection.scalar(text("SELECT count(*) FROM observed_events")) == 0
    engine.dispose()
