"""Runs the independently labelled cases in data/evaluation_cases.json through the policy engine.

Each profile case lists the exact rules a reviewer expects. A mismatch in either direction
(missed rule = false negative, extra rule = false positive) fails the test for that case,
so CI catches rule regressions before scripts/run_evaluation.py reports them as metrics.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.policy import RULES, evaluate

CASES_FILE = Path(__file__).resolve().parents[2] / "data" / "evaluation_cases.json"
ALL_CASES = json.loads(CASES_FILE.read_text(encoding="utf-8"))
PROFILE_CASES = [case for case in ALL_CASES if case.get("profile")]

BASE_PROFILE = {
    "agent_id": "SA-TEST",
    "description": "Summarizes public reference material",
    "owner": "Research Ops",
    "status": "active",
    "tools": ["knowledge_search"],
    "permissions": ["read_metadata"],
    "scopes": ["records:read"],
    "data_categories": ["public_reference"],
    "sensitivity": "low",
    "approval_required": False,
    "events": [],
}


def build_agent(case):
    """Same construction as scripts/run_evaluation.py so both report identical results."""
    values = {**BASE_PROFILE, "last_activity": datetime.now(timezone.utc), **case.get("agent", {})}
    stale_days = values.pop("stale_days", 0)
    if stale_days:
        values["last_activity"] = datetime.now(timezone.utc) - timedelta(days=stale_days)
    values["agent_id"] = case["id"]
    return SimpleNamespace(**values)


def test_dataset_is_well_formed():
    known = {rule["rule_id"] for rule in RULES}
    assert len({case["id"] for case in ALL_CASES}) == len(ALL_CASES), "case IDs must be unique"
    assert PROFILE_CASES, "expected at least one labelled profile case"
    for case in PROFILE_CASES:
        assert set(case["expected_rules"]) <= known, f"{case['id']} references an unknown rule"
    # every rule should be covered by at least one labelled positive case
    covered = {rule for case in PROFILE_CASES for rule in case["expected_rules"]}
    assert covered == known, f"rules without a labelled case: {sorted(known - covered)}"


@pytest.mark.parametrize("case", PROFILE_CASES, ids=[f"{case['id']}-{case['label']}" for case in PROFILE_CASES])
def test_labelled_case_matches_expected_rules(case):
    result = evaluate(build_agent(case))
    actual = sorted({finding["rule_id"] for finding in result["findings"]})
    assert actual == sorted(case["expected_rules"]), (
        f"{case['id']} ({case['label']}): expected {sorted(case['expected_rules'])}, got {actual}"
    )
    if not case["expected_rules"]:
        assert result["risk_score"] == 0 and result["risk_level"] == "low"
