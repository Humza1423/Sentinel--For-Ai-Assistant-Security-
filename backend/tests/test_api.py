from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_scenarios_and_campaign_report_routes():
    scenarios = client.get("/api/scenarios")
    assert scenarios.status_code == 200
    assert len(scenarios.json()) == 2
    result = client.post("/api/campaigns", json={"scenario_id": "cross-customer"})
    assert result.status_code == 200
    campaign_id = result.json()["campaign_id"]
    assert (
        client.get(f"/api/campaigns/{campaign_id}/report").json()["replay"]["verdict"] == "blocked"
    )
    assert client.get(f"/api/campaigns/{campaign_id}/events").status_code == 200


def test_client_cannot_supply_unknown_fields():
    result = client.post(
        "/api/campaigns", json={"scenario_id": "memo-phishing", "customer_id": "C-200"}
    )
    assert result.status_code == 422


def test_health_is_honest_about_live_model():
    response = client.get("/api/health").json()
    assert response["default_mode"] == "scripted"
    assert isinstance(response["live_agent_configured"], bool)
