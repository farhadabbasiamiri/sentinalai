import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from .database import Base, SessionLocal, engine
from .models import Agent, AuditEvent, CyberLog, Finding
from .core.policy import evaluate

ROOT = Path(__file__).resolve().parents[2]

# Realistic Sudbury institutions and local entities
SUDBURY_ORGS = [
    {"org": "Laurentian University", "dept": "Registrar & Academic Tech", "prefix": "LU"},
    {"org": "Collège Boréal", "dept": "Services aux étudiants", "prefix": "CB"},
    {"org": "Sudbury Secondary School", "dept": "Rainbow District School Board", "prefix": "RDSB"},
    {"org": "Cambrian College", "dept": "Applied Research & Tech", "prefix": "CC"},
    {"org": "Health Sciences North", "dept": "EHR & Clinical Informatics", "prefix": "HSN"},
    {"org": "Northern Ontario School of Medicine", "dept": "Health Data Commons", "prefix": "NOSM"},
    {"org": "Sudbury Community Health Centre", "dept": "Patient Care Systems", "prefix": "SCHC"},
    {"org": "Sudbury Credit Union", "dept": "Member Banking Systems", "prefix": "SCU"},
    {"org": "Northern Savings Bank", "dept": "Commercial Lending", "prefix": "NSB"},
    {"org": "Greater Sudbury Municipal Finance", "dept": "Treasury & Revenues", "prefix": "GSMF"},
    {"org": "Vale Canada – Sudbury Operations", "dept": "Mining Automation & SCADA", "prefix": "VALE"},
    {"org": "Glencore Sudbury Integrated Nickel", "dept": "Smelter Operations IT", "prefix": "GLEN"},
    {"org": "City of Greater Sudbury – IT Services", "dept": "Municipal Public Services", "prefix": "CGS"},
    {"org": "Dynamic Earth – Science North", "dept": "Visitor Engagement Tech", "prefix": "SN"},
]

AGENT_TEMPLATES = [
    {
        "role": "Admissions & Enrollment Bot",
        "description": "Processes student course registration and prerequisites verification",
        "tools": ["knowledge_search", "student_record_reader"],
        "permissions": ["read_student_records"],
        "scopes": ["students:read"],
        "categories": ["student_academics"],
        "sensitivity": "moderate",
        "approval": True,
    },
    {
        "role": "Clinical EHR Triage Assistant",
        "description": "Summarizes intake notes and medical history for nurse practitioner review",
        "tools": ["ehr_lookup", "clinical_knowledge_base"],
        "permissions": ["read_ehr", "write_triage_notes"],
        "scopes": ["patient:read", "intake:write"],
        "categories": ["patient_phi", "medical_records"],
        "sensitivity": "restricted",
        "approval": True,
    },
    {
        "role": "Municipal Tax & Utility Router",
        "description": "Assists citizens with property tax balances and water billing inquiries",
        "tools": ["utility_billing_search", "knowledge_search"],
        "permissions": ["read_utility_records"],
        "scopes": ["billing:read"],
        "categories": ["public_reference", "billing_data"],
        "sensitivity": "moderate",
        "approval": False,
    },
    {
        "role": "Telemetry & SCADA Ingest Agent",
        "description": "Monitors industrial sensor streams, smelter temperatures, and equipment alerts",
        "tools": ["scada_telemetry_reader", "alert_dispatcher"],
        "permissions": ["read_sensor_telemetry"],
        "scopes": ["scada:stream:read"],
        "categories": ["industrial_telemetry"],
        "sensitivity": "moderate",
        "approval": False,
    },
    {
        "role": "Banking Member Support Bot",
        "description": "Answers retail banking questions and routes loan pre-qualification requests",
        "tools": ["account_lookup", "knowledge_search"],
        "permissions": ["read_member_profile"],
        "scopes": ["accounts:read"],
        "categories": ["financial_records"],
        "sensitivity": "high",
        "approval": True,
    },
    {
        "role": "Campus IT Helpdesk Assistant",
        "description": "Resets active directory passwords and assists with Wi-Fi onboarding",
        "tools": ["ad_user_lookup", "ticket_router"],
        "permissions": ["read_directory", "write_tickets"],
        "scopes": ["directory:read", "tickets:write"],
        "categories": ["internal_directory"],
        "sensitivity": "low",
        "approval": False,
    },
]


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if agents need re-seeding with Sudbury institutions
        current_agent = db.query(Agent).first()
        needs_agent_seed = (
            db.query(Agent).count() == 0
            or (current_agent and not any(org["org"] in (current_agent.owner or "") for org in SUDBURY_ORGS))
        )

        if needs_agent_seed:
            db.query(Finding).delete()
            db.query(Agent).delete()
            db.commit()

            now = datetime.now(timezone.utc)
            agent_count = 36

            for index in range(agent_count):
                org_info = SUDBURY_ORGS[index % len(SUDBURY_ORGS)]
                template = AGENT_TEMPLATES[index % len(AGENT_TEMPLATES)]
                scenario = index % 9

                agent_id = f"SA-{1001 + index}"
                name = f"{org_info['prefix']} {template['role']}"
                owner = f"{org_info['org']} ({org_info['dept']})"
                description = f"{template['description']} for {org_info['org']}."
                status = "active"
                last_activity = now - timedelta(days=index % 18)
                events = []

                tools = list(template["tools"])
                permissions = list(template["permissions"])
                scopes = list(template["scopes"])
                categories = list(template["categories"])
                sensitivity = template["sensitivity"]
                approval = template["approval"]

                # Intentional governance test scenarios for policy evaluation
                if scenario == 1:
                    scopes = ["*"]
                elif scenario == 2:
                    owner = f"{org_info['org']} (Unassigned Team)"
                elif scenario == 3:
                    sensitivity, categories = "restricted", ["confidential_planning", "sensitive_pii"]
                    scopes, approval = ["records:read"], False
                elif scenario == 4:
                    tools = list(tools) + ["external_http", "file_reader"]
                elif scenario == 5:
                    status, last_activity = "inactive", now - timedelta(days=160 + index)
                    tools = list(tools) + ["email_sender"]
                elif scenario == 6:
                    tools, sensitivity, approval = ["identity_admin"], "low", False
                elif scenario == 7:
                    tools, approval = list(tools) + ["email_sender"], False
                    events = [{
                        "action": "send_external_notice",
                        "sensitive": True,
                        "approved": False,
                        "timestamp": (now - timedelta(hours=2)).isoformat()
                    }]
                elif scenario == 8:
                    permissions = ["read_metadata", "delete_records", "approve_payment"]
                    tools = ["payment_tool", "vendor_manager"]
                    approval = False

                agent = Agent(
                    agent_id=agent_id,
                    name=name,
                    description=description,
                    owner=owner,
                    status=status,
                    created_at=now - timedelta(days=45 + index),
                    last_activity=last_activity,
                    tools=tools,
                    permissions=permissions,
                    scopes=scopes,
                    data_categories=categories,
                    sensitivity=sensitivity,
                    approval_required=approval,
                    events=events,
                )

                result = evaluate(agent)
                agent.risk_score, agent.risk_level = result["risk_score"], result["risk_level"]
                db.add(agent)

                # Persist findings
                for f in result["findings"]:
                    db.add(Finding(**f))

            db.add(AuditEvent(
                event_id=str(uuid4()),
                action="sudbury_agents_seed",
                object_type="system",
                object_id=None,
                details={
                    "agents_created": agent_count,
                    "region": "Greater Sudbury",
                    "source": "SentinelAI Area 2 Generator"
                }
            ))

        # Seed cyber logs if table is empty
        if db.query(CyberLog).count() == 0:
            log_file = ROOT / "data" / "cyber_logs.json"
            if log_file.exists():
                raw_logs = json.loads(log_file.read_text(encoding="utf-8"))
                for entry in raw_logs:
                    ts = entry.get("timestamp")
                    if isinstance(ts, str):
                        try:
                            parsed_ts = datetime.fromisoformat(ts)
                        except Exception:
                            parsed_ts = datetime.now(timezone.utc)
                    else:
                        parsed_ts = datetime.now(timezone.utc)
                    db.add(CyberLog(
                        log_id=entry.get("log_id", str(uuid4())),
                        timestamp=parsed_ts,
                        organization_name=entry.get("organization_name", "Unknown Org"),
                        source_ip=entry.get("source_ip", "127.0.0.1"),
                        user_id=entry.get("user_id", "user_0"),
                        event_type=entry.get("event_type", "General Alert"),
                        severity=entry.get("severity", "Low"),
                        action_taken=entry.get("action_taken", "Logged")
                    ))
                db.add(AuditEvent(
                    event_id=str(uuid4()),
                    action="cyber_logs_seed",
                    object_type="system",
                    object_id=None,
                    details={"logs_created": len(raw_logs), "source": "data/cyber_logs.json"}
                ))

        db.commit()
    finally:
        db.close()
