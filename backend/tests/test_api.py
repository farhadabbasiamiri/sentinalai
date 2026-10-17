from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database, main, seed
from app.main import app



@pytest.fixture
def client(monkeypatch):
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", test_sessions)
    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(seed, "engine", test_engine)
    monkeypatch.setattr(seed, "SessionLocal", test_sessions)
    with TestClient(app) as test_client:
        yield test_client


def test_seeded_inventory_and_health(client):
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["agents"] == 36
    assert client.get("/api/health").json()["status"] == "ok"


def test_filters_and_validation(client):
    result = client.get("/api/agents", params={"risk": "high", "page_size": 100})
    assert result.status_code == 200
    assert result.json()["total"] > 0
    assert client.get("/api/agents", params={"page": 0}).status_code == 422
    assert client.post("/api/agents", json={"agent_id": "x", "name": "x", "description": "short"}).status_code == 422


def test_evaluation_and_review_tools_return_traceable_results(client):
    evaluation = client.post("/api/agents/SA-1002/evaluate")
    assert evaluation.status_code == 200
    assert "GOV-002" in {finding["rule_id"] for finding in evaluation.json()["findings"]}
    review = client.post("/api/reviews", json={"request": "Review SA-1002 and explain the wildcard scope."})
    assert review.status_code == 200
    assert review.json()["mode"] == "deterministic_fallback"
    assert [call["tool"] for call in review.json()["tool_calls"]] == ["get_agent_profile", "evaluate_agent_permissions", "search_governance_policies"]
    assert review.json()["policy_references"]
    assert client.post("/api/reviews", json={"request": "Review SA-9999"}).status_code == 404


def test_nonlocal_ollama_endpoint_is_ignored(client, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "https://example.invalid/api")
    response = client.post("/api/reviews", json={"request": "Review SA-1002"})
    assert response.status_code == 200
    assert response.json()["mode"] == "deterministic_fallback"


def test_proposal_requires_decision_and_separate_confirmation(client):
    existing = {agent["agent_id"] for agent in client.get("/api/agents", params={"page_size": 100}).json()["items"]}
    agent_id = next(f"SA-{number}" for number in range(9000, 10000) if f"SA-{number}" not in existing)
    created = client.post("/api/agents", json={"agent_id": agent_id, "name": "Test Synth", "description": "Reads approved public metadata", "owner": "QA Lab", "permissions": ["read_metadata"]})
    assert created.status_code == 201
    proposal = client.post(f"/api/agents/{agent_id}/proposals", json={"change_type": "remove_permission", "proposed_change": {"permission": "read_metadata"}, "rationale": "Remove unused metadata access from the test profile."})
    assert proposal.status_code == 201
    approval_id = proposal.json()["approval_id"]
    assert client.post(f"/api/approvals/{approval_id}/apply", json={"reviewer": "Reviewer", "confirmation": True}).status_code == 409
    approved = client.post(f"/api/approvals/{approval_id}/decision?decision=approve", json={"reviewer": "Reviewer"})
    assert approved.status_code == 200 and approved.json()["status"] == "approved"
    assert client.post(f"/api/approvals/{approval_id}/apply", json={"reviewer": "Reviewer", "confirmation": False}).status_code == 422
    applied = client.post(f"/api/approvals/{approval_id}/apply", json={"reviewer": "Reviewer", "confirmation": True})
    assert applied.status_code == 200 and applied.json()["approval"]["status"] == "applied"
    assert "read_metadata" not in applied.json()["agent"]["permissions"]
    assert client.get("/api/audit", params={"page_size": 100}).json()["total"] > 0


def test_policy_and_exports(client):
    assert len(client.get("/api/policies").json()["rules"]) == 10
    assert client.get("/api/policies/search", params={"q": "human approval"}).json()["results"]
    assert "finding_id" in client.get("/api/reports/findings.csv").text
    assert client.get("/api/reports/findings.json").status_code == 200
    assert "# SentinelAI Governance Report" in client.get("/api/reports/findings.md").text
