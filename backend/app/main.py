import csv
import io
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .agent.review import run_review
from .core.policy import RULES, evaluate
from .database import Base, engine, get_db
from .models import Agent, Approval, AuditEvent, Finding
from .schemas import AgentCreate, DecisionRequest, ProposalRequest, ReviewRequest
from .seed import seed_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    with next(get_db()) as db:
        if db.query(Finding).count() == 0:
            for agent in db.query(Agent).all():
                result = evaluate(agent)
                agent.risk_score, agent.risk_level = result["risk_score"], result["risk_level"]
                db.add_all(Finding(**finding) for finding in result["findings"])
            db.commit()
    yield


app = FastAPI(title="SentinelAI Governance API", version="1.0.0", description="Synthetic AI agent governance and permission monitoring MVP.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])


def iso(value):
    return value.isoformat() if value else None


def csv_safe(value):
    text = "" if value is None else str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def agent_json(agent: Agent):
    return {"agent_id": agent.agent_id, "name": agent.name, "description": agent.description, "owner": agent.owner, "status": agent.status, "created_at": iso(agent.created_at), "last_activity": iso(agent.last_activity), "tools": agent.tools, "permissions": agent.permissions, "scopes": agent.scopes, "data_categories": agent.data_categories, "sensitivity": agent.sensitivity, "approval_required": agent.approval_required, "risk_score": agent.risk_score, "risk_level": agent.risk_level, "last_review": iso(agent.last_review), "events": agent.events}


def finding_json(finding: Finding):
    return {"finding_id": finding.finding_id, "agent_id": finding.agent_id, "rule_id": finding.rule_id, "severity": finding.severity, "title": finding.title, "evidence": finding.evidence, "rationale": finding.rationale, "remediation": finding.remediation, "approval_required": finding.approval_required, "status": finding.status, "created_at": iso(finding.created_at)}


def approval_json(item: Approval):
    return {"approval_id": item.approval_id, "agent_id": item.agent_id, "finding_id": item.finding_id, "change_type": item.change_type, "current_configuration": item.current_configuration, "proposed_change": item.proposed_change, "rationale": item.rationale, "evidence": item.evidence, "status": item.status, "reviewer": item.reviewer, "decision_at": iso(item.decision_at), "applied_at": iso(item.applied_at), "created_at": iso(item.created_at)}


def log_event(db: Session, action: str, object_type: str, object_id: str | None, details: dict):
    db.add(AuditEvent(event_id=str(uuid4()), action=action, object_type=object_type, object_id=object_id, details=details))


@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version, "ai_mode": "ollama_optional_deterministic_fallback"}


@app.get("/api/ready")
def ready(db: Session = Depends(get_db)):
    try:
        return {"ready": True, "agents": db.query(Agent).count(), "database": "sqlite"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc


@app.get("/api/summary")
def summary(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    findings = db.query(Finding).filter(Finding.status == "open").all()
    by_risk = {level: sum(agent.risk_level == level for agent in agents) for level in ["low", "medium", "high", "critical"]}
    by_category = {}
    for finding in findings:
        by_category[finding.rule_id] = by_category.get(finding.rule_id, 0) + 1
    recent = db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(8).all()
    return {"total_agents": len(agents), "risk_distribution": by_risk, "open_findings": len(findings), "over_privileged_agents": len({f.agent_id for f in findings if f.rule_id in {"GOV-001", "GOV-002", "GOV-007"}}), "pending_approvals": db.query(Approval).filter(Approval.status == "pending").count(), "sensitive_findings": sum(f.rule_id in {"GOV-003", "GOV-010"} for f in findings), "findings_by_category": by_category, "highest_risk_agents": [agent_json(agent) for agent in sorted(agents, key=lambda item: item.risk_score, reverse=True)[:6]], "recent_events": [{"event_id": event.event_id, "action": event.action, "object_type": event.object_type, "object_id": event.object_id, "details": event.details, "created_at": iso(event.created_at)} for event in recent]}


@app.get("/api/agents")
def list_agents(q: str = Query(default="", max_length=120), owner: str = Query(default="", max_length=120), status: str = Query(default="", pattern="^(|active|inactive|suspended)$"), risk: str = Query(default="", pattern="^(|low|medium|high|critical)$"), tool: str = Query(default="", max_length=120), sensitivity: str = Query(default="", pattern="^(|low|moderate|high|restricted)$"), sort_by: str = Query(default="risk_score", pattern="^(name|risk_score|created_at|last_activity)$"), order: str = Query(default="desc", pattern="^(asc|desc)$"), page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(Agent)
    if q:
        query = query.filter(or_(Agent.name.ilike(f"%{q}%"), Agent.agent_id.ilike(f"%{q}%")))
    if owner:
        query = query.filter(Agent.owner.ilike(f"%{owner}%"))
    if status:
        query = query.filter(Agent.status == status)
    if risk:
        query = query.filter(Agent.risk_level == risk)
    if sensitivity:
        query = query.filter(Agent.sensitivity == sensitivity)
    agents = query.all()
    if tool:
        agents = [agent for agent in agents if tool in (agent.tools or [])]
    total = len(agents)
    agents.sort(key=lambda agent: (getattr(agent, sort_by) is None, getattr(agent, sort_by) if getattr(agent, sort_by) is not None else ""), reverse=order == "desc")
    start = (page - 1) * page_size
    return {"items": [agent_json(agent) for agent in agents[start:start + page_size]], "total": total, "page": page, "page_size": page_size, "pages": (total + page_size - 1) // page_size}


@app.get("/api/agents/{agent_id}")
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    result = agent_json(agent)
    result["findings"] = [finding_json(item) for item in db.query(Finding).filter(Finding.agent_id == agent_id).order_by(Finding.created_at.desc()).all()]
    return result


@app.post("/api/agents", status_code=201)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    if db.get(Agent, payload.agent_id):
        raise HTTPException(status_code=409, detail="Agent ID already exists")
    now = datetime.now(timezone.utc)
    agent = Agent(**payload.model_dump(), created_at=now, last_activity=now)
    result = evaluate(agent)
    agent.risk_score, agent.risk_level = result["risk_score"], result["risk_level"]
    db.add(agent)
    db.flush()
    log_event(db, "agent_created", "agent", agent.agent_id, {"source": "synthetic_record"})
    db.commit()
    return agent_json(agent)


@app.put("/api/agents/{agent_id}")
def update_agent(agent_id: str, payload: AgentCreate, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if payload.agent_id != agent_id:
        raise HTTPException(status_code=422, detail="Path and body agent IDs must match")
    for key, value in payload.model_dump(exclude={"agent_id"}).items():
        setattr(agent, key, value)
    result = evaluate(agent)
    agent.risk_score, agent.risk_level = result["risk_score"], result["risk_level"]
    log_event(db, "agent_updated", "agent", agent_id, {"source": "synthetic_record"})
    db.commit()
    return agent_json(agent)


@app.post("/api/agents/{agent_id}/evaluate")
def evaluate_endpoint(agent_id: str, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    result = evaluate(agent)
    db.query(Finding).filter(Finding.agent_id == agent_id, Finding.status == "open").delete(synchronize_session=False)
    db.add_all(Finding(**item) for item in result["findings"])
    agent.risk_score, agent.risk_level, agent.last_review = result["risk_score"], result["risk_level"], datetime.now(timezone.utc)
    log_event(db, "governance_review", "agent", agent_id, {"risk_score": result["risk_score"], "finding_count": len(result["findings"])})
    for finding in result["findings"]:
        log_event(db, "policy_match", "finding", finding["finding_id"], {"agent_id": agent_id, "rule_id": finding["rule_id"], "severity": finding["severity"]})
    db.commit()
    return result


@app.get("/api/findings")
def list_findings(severity: str = Query(default="", pattern="^(|low|medium|high|critical)$"), rule_id: str = Query(default="", max_length=32), agent_id: str = Query(default="", max_length=32), status: str = Query(default="", pattern="^(|open|reviewed|resolved)$"), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(Finding)
    if severity: query = query.filter(Finding.severity == severity)
    if rule_id: query = query.filter(Finding.rule_id == rule_id)
    if agent_id: query = query.filter(Finding.agent_id == agent_id)
    if status: query = query.filter(Finding.status == status)
    total = query.count()
    items = query.order_by(Finding.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [finding_json(item) for item in items], "total": total, "page": page, "page_size": page_size}


@app.patch("/api/findings/{finding_id}/review")
def review_finding(finding_id: str, db: Session = Depends(get_db)):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.status = "reviewed"
    log_event(db, "finding_reviewed", "finding", finding_id, {"agent_id": finding.agent_id, "rule_id": finding.rule_id})
    db.commit()
    return finding_json(finding)


@app.get("/api/policies")
def policies():
    return {"rules": RULES, "document": "backend/app/policies/governance.md"}


@app.get("/api/policies/search")
def policy_search(q: str = Query(min_length=2, max_length=500)):
    from .rag.retrieval import search_policies
    return {"query": q, "results": search_policies(q), "retrieval": "keyword"}


@app.post("/api/reviews")
def governance_review(payload: ReviewRequest, db: Session = Depends(get_db)):
    try:
        result = run_review(db, payload.request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_event(db, "governance_review_request", "review", None, {"mode": result["mode"], "finding_count": len(result["findings"])})
    db.commit()
    return result


@app.get("/api/approvals")
def list_approvals(status: str = Query(default="", pattern="^(|pending|approved|rejected|applied)$"), db: Session = Depends(get_db)):
    query = db.query(Approval)
    if status: query = query.filter(Approval.status == status)
    return {"items": [approval_json(item) for item in query.order_by(Approval.created_at.desc()).all()]}


@app.post("/api/agents/{agent_id}/proposals", status_code=201)
def create_proposal(agent_id: str, payload: ProposalRequest, db: Session = Depends(get_db)):
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    current = agent_json(agent)
    approval = Approval(approval_id=str(uuid4()), agent_id=agent_id, finding_id=payload.finding_id, change_type=payload.change_type, current_configuration=current, proposed_change=payload.proposed_change, rationale=payload.rationale, evidence=payload.evidence, status="pending")
    db.add(approval)
    log_event(db, "approval_proposed", "approval", approval.approval_id, {"agent_id": agent_id, "change_type": payload.change_type})
    db.commit()
    return approval_json(approval)


@app.post("/api/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, payload: DecisionRequest, decision: str = Query(pattern="^(approve|reject)$"), db: Session = Depends(get_db)):
    item = db.get(Approval, approval_id)
    if not item:
        raise HTTPException(status_code=404, detail="Approval proposal not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending proposals can receive a decision")
    item.status = "approved" if decision == "approve" else "rejected"
    item.reviewer, item.decision_at = payload.reviewer, datetime.now(timezone.utc)
    action = "approval_approved" if decision == "approve" else "approval_rejected"
    log_event(db, action, "approval", approval_id, {"agent_id": item.agent_id, "reviewer": payload.reviewer})
    db.commit()
    return approval_json(item)


@app.post("/api/approvals/{approval_id}/apply")
def apply_approval(approval_id: str, payload: DecisionRequest, db: Session = Depends(get_db)):
    item = db.get(Approval, approval_id)
    if not item:
        raise HTTPException(status_code=404, detail="Approval proposal not found")
    if item.status != "approved":
        raise HTTPException(status_code=409, detail="Proposal must be approved before applying")
    if not payload.confirmation:
        raise HTTPException(status_code=422, detail="Explicit confirmation is required to apply a simulated change")
    agent = db.get(Agent, item.agent_id)
    change = item.proposed_change
    if item.change_type == "remove_permission":
        value = change.get("permission")
        if value not in (agent.permissions or []): raise HTTPException(status_code=422, detail="Proposed permission is not currently assigned")
        agent.permissions = [entry for entry in agent.permissions if entry != value]
    elif item.change_type == "restrict_scope":
        value = change.get("scope")
        if value not in (agent.scopes or []): raise HTTPException(status_code=422, detail="Proposed scope is not currently assigned")
        agent.scopes = [entry for entry in agent.scopes if entry != value]
    elif item.change_type == "restrict_data":
        value = change.get("category")
        if value not in (agent.data_categories or []): raise HTTPException(status_code=422, detail="Proposed category is not currently assigned")
        agent.data_categories = [entry for entry in agent.data_categories if entry != value]
    elif item.change_type == "set_approval":
        if change.get("required") is not True: raise HTTPException(status_code=422, detail="The simulation only permits enabling approval requirements")
        agent.approval_required = True
    elif item.change_type == "deactivate_agent":
        agent.status = "inactive"
    else:
        raise HTTPException(status_code=422, detail="Unsupported simulated change")
    item.status, item.applied_at = "applied", datetime.now(timezone.utc)
    item.reviewer = payload.reviewer
    score = evaluate(agent)
    agent.risk_score, agent.risk_level = score["risk_score"], score["risk_level"]
    db.query(Finding).filter(Finding.agent_id == agent.agent_id, Finding.status == "open").delete(synchronize_session=False)
    db.add_all(Finding(**finding) for finding in score["findings"])
    log_event(db, "simulated_change_applied", "approval", approval_id, {"agent_id": agent.agent_id, "change_type": item.change_type, "reviewer": payload.reviewer})
    db.commit()
    return {"approval": approval_json(item), "agent": agent_json(agent)}


@app.get("/api/audit")
def audit_logs(action: str = Query(default="", max_length=80), page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    query = db.query(AuditEvent)
    if action: query = query.filter(AuditEvent.action == action)
    total = query.count()
    items = query.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"event_id": event.event_id, "action": event.action, "object_type": event.object_type, "object_id": event.object_id, "details": event.details, "created_at": iso(event.created_at)} for event in items], "total": total, "page": page}


@app.get("/api/audit/export.csv")
def export_audit(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "action", "object_type", "object_id", "details"])
    for event in db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).all():
        writer.writerow([csv_safe(iso(event.created_at)), csv_safe(event.action), csv_safe(event.object_type), csv_safe(event.object_id), csv_safe(json.dumps(event.details))])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sentinelai-audit.csv"})


@app.get("/api/reports/findings.json")
def export_findings_json(db: Session = Depends(get_db)):
    return {"methodology": "Deterministic project-specific policy weights, capped at 100; not proof of compromise.", "limitations": "All records are synthetic. Results do not establish production readiness.", "findings": [finding_json(item) for item in db.query(Finding).order_by(Finding.created_at.desc()).all()]}


@app.get("/api/reports/findings.csv")
def export_findings_csv(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["finding_id", "agent_id", "rule_id", "severity", "title", "status", "evidence", "remediation"])
    for item in db.query(Finding).order_by(Finding.created_at.desc()).all():
        writer.writerow([csv_safe(item.finding_id), csv_safe(item.agent_id), csv_safe(item.rule_id), csv_safe(item.severity), csv_safe(item.title), csv_safe(item.status), csv_safe(json.dumps(item.evidence)), csv_safe(item.remediation)])
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sentinelai-findings.csv"})


@app.get("/api/reports/findings.md")
def export_readable_report(db: Session = Depends(get_db)):
    findings = db.query(Finding).order_by(Finding.severity.desc(), Finding.created_at.desc()).all()
    lines = ["# SentinelAI Governance Report", "", "## Methodology", "Deterministic project-specific rule weights, capped at 100. Risk scores are decision-support indicators, not proof of compromise.", "", "## Limitations", "All records are synthetic. This evaluation does not establish production readiness.", "", f"## Findings ({len(findings)})", ""]
    for item in findings:
        lines.extend([f"### {item.title}", f"- Agent: `{item.agent_id}`", f"- Rule: `{item.rule_id}`", f"- Severity: {item.severity}", f"- Status: {item.status}", f"- Evidence: {'; '.join(item.evidence)}", f"- Rationale: {item.rationale}", f"- Recommended action: {item.remediation}", ""])
    return Response("\n".join(lines), media_type="text/markdown", headers={"Content-Disposition": "attachment; filename=sentinelai-governance-report.md"})


@app.get("/api/evaluation")
def evaluation_metrics():
    result_file = Path(__file__).resolve().parents[2] / "reports" / "evaluation" / "results.json"
    if not result_file.exists():
        return {"available": False, "message": "Evaluation results have not been generated. Run: python scripts/run_evaluation.py"}
    return {"available": True, **json.loads(result_file.read_text(encoding="utf-8"))}
