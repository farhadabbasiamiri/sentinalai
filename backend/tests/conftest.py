"""Shared pytest fixtures for the SentinelAI backend tests."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import database, main, seed
from app.main import app


@pytest.fixture
def client(monkeypatch):
    """FastAPI client backed by a fresh in-memory SQLite database (seeded with 36 synthetic agents)."""
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", test_sessions)
    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(seed, "engine", test_engine)
    monkeypatch.setattr(seed, "SessionLocal", test_sessions)
    # Never reach a real model during tests unless a test opts in explicitly.
    monkeypatch.setenv("OLLAMA_URL", "")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_profile():
    """Factory for a clean, low-risk agent profile; pass keyword overrides to build a scenario."""

    def build(**overrides):
        values = {
            "agent_id": "SA-9001",
            "description": "Summarizes public reference material",
            "owner": "Research Ops",
            "status": "active",
            "last_activity": datetime.now(timezone.utc),
            "tools": ["knowledge_search"],
            "permissions": ["read_metadata"],
            "scopes": ["records:read"],
            "data_categories": ["public_reference"],
            "sensitivity": "low",
            "approval_required": False,
            "events": [],
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    return build


@pytest.fixture
def new_agent(client):
    """Create a fresh synthetic agent through the API and return its ID."""

    def create(agent_id="SA-7001", **overrides):
        body = {
            "agent_id": agent_id,
            "name": "Test Synthetic Agent",
            "description": "Reads approved public metadata",
            "owner": "QA Lab",
            "permissions": ["read_metadata"],
        }
        body.update(overrides)
        response = client.post("/api/agents", json=body)
        assert response.status_code == 201, response.text
        return agent_id

    return create
