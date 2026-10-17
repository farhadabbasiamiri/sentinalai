from datetime import datetime, timedelta, timezone

from .database import Base, SessionLocal, engine
from .models import Agent, AuditEvent
from .core.policy import evaluate
from uuid import uuid4

TEAMS = ["Research Ops", "Platform Assurance", "Knowledge Systems", "Service Design", "Data Stewardship", "Automation Lab"]
NAMES = ["Atlas", "Beacon", "Cedar", "Delta", "Ember", "Fathom", "Glacier", "Harbor", "Ion", "Juniper", "Keystone", "Lumen", "Mosaic", "Northstar", "Orbit", "Pioneer", "Quartz", "Relay", "Summit", "Tandem", "Umber", "Vector", "Waypoint", "Xenon", "Yarrow", "Zephyr"]
PURPOSES = ["Summarizes approved internal knowledge requests", "Routes routine service requests to the correct team", "Classifies synthetic documents for retention review", "Prepares draft status updates for human review", "Finds duplicate records in a limited synthetic dataset", "Extracts non-sensitive metadata from approved files"]


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Agent).count():
            return
        now = datetime.now(timezone.utc)
        for index in range(36):
            scenario = index % 9
            agent_id = f"SA-{1001 + index}"
            name = f"{NAMES[index % len(NAMES)]} {['Assistant', 'Router', 'Analyst'][index % 3]}"
            tools = ["knowledge_search"]
            permissions = ["read_metadata"]
            scopes = ["records:read"]
            categories = ["public_reference"]
            sensitivity = "low"
            approval = False
            owner = TEAMS[index % len(TEAMS)]
            status = "active"
            last_activity = now - timedelta(days=index % 20)
            events = []
            description = PURPOSES[index % len(PURPOSES)]
            if scenario == 1:
                scopes = ["*"]
            elif scenario == 2:
                owner = None
            elif scenario == 3:
                sensitivity, categories = "restricted", ["confidential_planning"]
                scopes, approval = ["planning:read"], False
            elif scenario == 4:
                tools = ["file_reader", "external_http"]
            elif scenario == 5:
                status, last_activity = "inactive", now - timedelta(days=150 + index)
                tools = ["knowledge_search", "email_sender"]
            elif scenario == 6:
                tools, sensitivity, approval = ["identity_admin"], "low", False
            elif scenario == 7:
                tools, approval = ["email_sender"], False
                events = [{"action": "send_external_notice", "sensitive": True, "approved": False, "timestamp": (now - timedelta(hours=2)).isoformat()}]
            elif scenario == 8:
                permissions = ["read_metadata", "delete_records", "approve_payment"]
                description = "Summarizes approved internal knowledge requests"
                tools = ["payment_tool", "vendor_manager"]
            if index % 4 == 0 and scenario not in {3, 6}:
                categories, sensitivity, approval = ["internal_metrics"], "moderate", True
            agent = Agent(agent_id=agent_id, name=name, description=description, owner=owner, status=status, created_at=now - timedelta(days=40 + index), last_activity=last_activity, tools=tools, permissions=permissions, scopes=scopes, data_categories=categories, sensitivity=sensitivity, approval_required=approval, events=events)
            result = evaluate(agent)
            agent.risk_score, agent.risk_level = result["risk_score"], result["risk_level"]
            db.add(agent)
        db.add(AuditEvent(event_id=str(uuid4()), action="synthetic_seed", object_type="system", object_id=None, details={"agents_created": 36, "source": "local synthetic generator"}))
        db.commit()
    finally:
        db.close()
