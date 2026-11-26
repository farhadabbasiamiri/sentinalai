import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import database, main, seed
from app.agent.review import AgentIdInput
from app.core.policy import evaluate
from app.main import app
from app.rag import retrieval
from app.schemas import AgentCreate


def metrics(expected, predicted):
    true_positive = len(expected & predicted)
    false_positive = len(predicted - expected)
    false_negative = len(expected - predicted)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "false_positives": false_positive, "false_negatives": false_negative, "true_positives": true_positive}


def run():
    cases = json.loads((ROOT / "data" / "evaluation_cases.json").read_text(encoding="utf-8"))
    base = {"agent_id": "SA-TEST", "description": "Summarizes public reference material", "owner": "Research Ops", "status": "active", "last_activity": datetime.now(timezone.utc), "tools": ["knowledge_search"], "permissions": ["read_metadata"], "scopes": ["records:read"], "data_categories": ["public_reference"], "sensitivity": "low", "approval_required": False, "events": []}
    expected, predicted = set(), set()
    rule_counts = {}
    evidence_total = evidence_grounded = 0
    for case in cases:
        if not case["profile"]:
            continue
        values = {**base, **case.get("agent", {})}
        stale_days = values.pop("stale_days", 0)
        if stale_days:
            values["last_activity"] = datetime.now(timezone.utc) - timedelta(days=stale_days)
        values["agent_id"] = case["id"]
        result = evaluate(SimpleNamespace(**values))
        actual_rules = {finding["rule_id"] for finding in result["findings"]}
        expected_rules = set(case["expected_rules"])
        expected.update(f"{case['id']}:{rule}" for rule in expected_rules)
        predicted.update(f"{case['id']}:{rule}" for rule in actual_rules)
        for rule in expected_rules | actual_rules:
            current = rule_counts.setdefault(rule, {"expected": 0, "detected": 0, "false_positive": 0, "false_negative": 0})
            current["expected"] += int(rule in expected_rules)
            current["detected"] += int(rule in expected_rules and rule in actual_rules)
            current["false_positive"] += int(rule in actual_rules and rule not in expected_rules)
            current["false_negative"] += int(rule in expected_rules and rule not in actual_rules)
        for finding in result["findings"]:
            evidence_total += 1
            if finding["evidence"] and finding["remediation"] and finding["rule_id"] in {rule["rule_id"] for rule in main.RULES}:
                evidence_grounded += 1

    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    test_sessions = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    workflow_checks = {}
    api_metrics = {"tool_call_success_rate": 0.0, "response_latency_ms": None, "approval_enforcement_rate": 0.0}
    with patch.object(database, "engine", test_engine), patch.object(database, "SessionLocal", test_sessions), patch.object(seed, "engine", test_engine), patch.object(seed, "SessionLocal", test_sessions), patch.object(main, "engine", test_engine):
        with TestClient(app) as client:
            try:
                AgentIdInput(agent_id="not-valid")
                workflow_checks["invalid_agent_id"] = False
            except ValidationError:
                workflow_checks["invalid_agent_id"] = True
            try:
                AgentCreate.model_validate({"agent_id": "bad", "name": "x", "description": "x", "unsupported": True})
                workflow_checks["malformed_payload"] = False
            except ValidationError:
                workflow_checks["malformed_payload"] = True
            prior_ollama = os.environ.get("OLLAMA_URL")
            os.environ["OLLAMA_URL"] = ""
            started = time.perf_counter()
            review_response = client.post("/api/reviews", json={"request": "Review SA-1002 for broad scopes and summarize evidence."})
            api_metrics["response_latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
            review = review_response.json() if review_response.status_code == 200 else {}
            calls = review.get("tool_calls", [])
            expected_tools = {"get_agent_profile", "evaluate_agent_permissions", "search_governance_policies"}
            api_metrics["tool_call_success_rate"] = round(len({call.get("tool") for call in calls} & expected_tools) / len(expected_tools), 4)
            workflow_checks["missing_llm_fallback"] = review.get("mode") == "deterministic_fallback"
            api_metrics["workflow_report"] = review
            if prior_ollama is None:
                os.environ.pop("OLLAMA_URL", None)
            else:
                os.environ["OLLAMA_URL"] = prior_ollama
            with patch.object(retrieval, "POLICY_PATH", ROOT / "data" / "missing-policy-fixture.md"):
                workflow_checks["policy_retrieval_failure"] = retrieval.search_policies("least privilege") == []
            workflow_checks["tool_failure"] = client.post("/api/reviews", json={"request": "Review SA-9999"}).status_code == 404

            agent_id = "SA-9898"
            created = client.post("/api/agents", json={"agent_id": agent_id, "name": "Evaluation Synthetic", "description": "Reads approved public metadata", "owner": "Evaluation Lab", "permissions": ["read_metadata"]})
            proposal = client.post(f"/api/agents/{agent_id}/proposals", json={"change_type": "set_approval", "proposed_change": {"required": True}, "rationale": "Require reviewer gating for the evaluation workflow."}) if created.status_code == 201 else None
            denied = 0
            checks = 0
            if proposal and proposal.status_code == 201:
                approval_id = proposal.json()["approval_id"]
                pending_apply = client.post(f"/api/approvals/{approval_id}/apply", json={"reviewer": "Evaluation reviewer", "confirmation": True})
                checks += 1; denied += int(pending_apply.status_code == 409)
                rejected = client.post(f"/api/approvals/{approval_id}/decision?decision=reject", json={"reviewer": "Evaluation reviewer"})
                workflow_checks["approval_rejection"] = rejected.status_code == 200 and rejected.json()["status"] == "rejected"
                after_rejection = client.post(f"/api/approvals/{approval_id}/apply", json={"reviewer": "Evaluation reviewer", "confirmation": True})
                checks += 1; denied += int(after_rejection.status_code == 409)
            else:
                workflow_checks["approval_rejection"] = False
            api_metrics["approval_enforcement_rate"] = round(denied / checks, 4) if checks else 0.0
            workflow_checks["unauthorized_simulated_change"] = checks == 2 and denied == checks
            api_metrics.pop("workflow_report", None)
            report_grounded = bool(review.get("findings")) and all(item.get("evidence") and item.get("remediation") for item in review.get("findings", []))
            if not review.get("findings"):
                report_grounded = bool(review.get("tool_calls")) and bool(review.get("policy_references"))
            workflow_checks["evidence_grounding_sample"] = report_grounded

    test = subprocess.run([sys.executable, "-m", "pytest", "backend/tests", "-q", "--tb=short"], cwd=ROOT, capture_output=True, text=True)
    test_output = test.stdout + test.stderr
    match = re.search(r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) errors?)?", test_output)
    passed = int(match.group(1)) if match else 0
    failed = (int(match.group(2) or 0) + int(match.group(3) or 0)) if match else 0
    test_rate = round(passed / (passed + failed), 4) if passed + failed else 0.0
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_cases": len(cases),
        "profile_cases_scored": sum(case["profile"] for case in cases),
        "workflow_cases": sum(not case["profile"] for case in cases),
        "metrics": {
            **metrics(expected, predicted),
            "end_to_end_test_pass_rate": test_rate,
            "test_cases_passed": passed,
            "test_cases_failed": failed,
            "tool_call_success_rate": api_metrics["tool_call_success_rate"],
            "response_latency_ms": api_metrics["response_latency_ms"],
            "human_approval_enforcement_rate": api_metrics["approval_enforcement_rate"],
            "evidence_grounding_quality": round(evidence_grounded / evidence_total, 4) if evidence_total else 0.0,
        },
        "rule_level": rule_counts,
        "workflow_checks": workflow_checks,
        "false_positive_cases": sorted(predicted - expected),
        "false_negative_cases": sorted(expected - predicted),
        "methodology": "Rule metrics use exact per-case expected rule labels. Workflow metrics exercise local FastAPI/TestClient routes. Grounding checks require evidence, remediation, and known rule IDs. Thresholds are project-specific.",
        "limitations": "Synthetic profiles and workflow tests do not represent production traffic and do not establish production readiness.",
    }
    output = ROOT / "reports" / "evaluation" / "results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if test.returncode or not all(workflow_checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    run()
