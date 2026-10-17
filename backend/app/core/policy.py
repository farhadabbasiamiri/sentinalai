from datetime import datetime, timezone
from uuid import uuid4

SEVERITY_WEIGHT = {"low": 5, "medium": 12, "high": 22, "critical": 32}
SENSITIVE = {"high", "restricted"}
ADMIN_TOOLS = {"admin_console", "identity_admin", "deployment_control"}
DANGEROUS_COMBINATIONS = [({"email_sender", "external_http"}, "Outbound messaging combined with unrestricted external access"), ({"file_reader", "external_http"}, "Local file access combined with external transfer"), ({"payment_tool", "vendor_manager"}, "Payment execution combined with vendor management")]
RULES = [
    {"rule_id": "GOV-001", "title": "Purpose and permission mismatch", "severity": "high", "description": "Reduce permissions not needed for the declared business purpose."},
    {"rule_id": "GOV-002", "title": "Wildcard API scope", "severity": "critical", "description": "Avoid wildcard or organization-wide API scopes."},
    {"rule_id": "GOV-003", "title": "Sensitive data lacks approval", "severity": "critical", "description": "Sensitive data access requires an explicit human approval control."},
    {"rule_id": "GOV-004", "title": "Dangerous tool combination", "severity": "high", "description": "Separate tools that enable unsafe data movement or conflicting duties."},
    {"rule_id": "GOV-005", "title": "Missing accountable owner", "severity": "medium", "description": "Every agent must have a responsible owner or team."},
    {"rule_id": "GOV-006", "title": "Stale agent retains access", "severity": "high", "description": "Inactive agents should be reviewed and have unused access removed."},
    {"rule_id": "GOV-007", "title": "Administrative tool on ordinary agent", "severity": "critical", "description": "Administrative capabilities require restricted agent classification and approval."},
    {"rule_id": "GOV-008", "title": "Sensitive action lacks approval", "severity": "high", "description": "High-impact actions must be gated by human approval."},
    {"rule_id": "GOV-009", "title": "Conflicting duties", "severity": "high", "description": "One agent should not both initiate and approve the same sensitive workflow."},
    {"rule_id": "GOV-010", "title": "Unapproved sensitive activity", "severity": "critical", "description": "Sensitive actions without approval evidence must be escalated."},
]


def evaluate(agent):
    findings = []
    def add(rule_id, severity, title, evidence, rationale, remediation, approval=True):
        findings.append({"finding_id": str(uuid4()), "agent_id": agent.agent_id, "rule_id": rule_id, "severity": severity, "title": title, "evidence": evidence, "rationale": rationale, "remediation": remediation, "approval_required": approval, "status": "open", "created_at": datetime.now(timezone.utc)})

    purpose = agent.description.lower()
    broad = [scope for scope in (agent.scopes or []) if "*" in scope or scope.lower() in {"admin", "all", "full_access"}]
    if broad:
        add("GOV-002", "critical", "Wildcard or broad API scope", [f"Scope: {scope}" for scope in broad], "A wildcard or organization-wide scope exceeds a narrowly defined task boundary.", "Replace each broad scope with the smallest read or action scope required.")
    excess = [permission for permission in (agent.permissions or []) if permission.lower() in {"delete_records", "manage_users", "export_all", "write_any", "approve_transactions"} and not any(word in purpose for word in ("manage", "administr", "delete", "approve"))]
    if excess:
        add("GOV-001", "high", "Permissions exceed declared purpose", [f"Permission: {permission}" for permission in excess], "The permission list contains capabilities that are not justified by the declared purpose.", "Remove unjustified permissions and document a narrow business justification for any exception.")
    if agent.sensitivity in SENSITIVE and not agent.approval_required:
        add("GOV-003", "critical", "Sensitive data access lacks approval", [f"Sensitivity: {agent.sensitivity}", f"Data categories: {', '.join(agent.data_categories or []) or 'none listed'}", "Approval required: false"], "Sensitive or restricted data is accessible without an explicit human approval requirement.", "Enable approval gating and restrict data access to the minimum necessary.")
    tools = set(agent.tools or [])
    for pair, explanation in DANGEROUS_COMBINATIONS:
        if pair.issubset(tools):
            add("GOV-004", "high", "Dangerous tool combination", [f"Assigned tools: {', '.join(sorted(pair))}"], explanation + ".", "Remove one capability or isolate the workflow behind an approved, audited boundary.")
    if not agent.owner or not agent.owner.strip():
        add("GOV-005", "medium", "Agent has no accountable owner", ["Owner: missing"], "No responsible person or team is recorded for this agent.", "Assign a named accountable team and review access ownership.", False)
    last_activity = agent.last_activity
    if agent.status == "inactive" and (agent.permissions or agent.scopes or agent.tools):
        stale_days = 91
    elif last_activity:
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)
        stale_days = (datetime.now(timezone.utc) - last_activity).days
    else:
        stale_days = 999
    if stale_days > 90 and (agent.permissions or agent.scopes or agent.tools):
        add("GOV-006", "high", "Stale agent retains permissions", [f"Days since activity: {stale_days}", f"Status: {agent.status}"], "This project-specific check flags agents inactive for more than 90 days while access remains assigned.", "Confirm business need, then deactivate the agent or remove retained permissions.")
    privileged = sorted(tools & ADMIN_TOOLS)
    if privileged and agent.sensitivity not in SENSITIVE:
        add("GOV-007", "critical", "Administrative tool assigned to ordinary agent", [f"Administrative tools: {', '.join(privileged)}", f"Sensitivity classification: {agent.sensitivity}"], "An administrative capability is assigned without a restricted classification.", "Remove the administrative tool or reclassify, isolate, and require explicit human approval.")
    action_tools = tools & {"payment_tool", "email_sender", "deployment_control", "identity_admin", "vendor_manager"}
    if action_tools and not agent.approval_required:
        add("GOV-008", "high", "Sensitive action lacks approval", [f"Action tools: {', '.join(sorted(action_tools))}", "Approval required: false"], "One or more high-impact tools can act without a human approval gate.", "Require explicit approval before each sensitive action.")
    if {"request_access", "approve_access"}.issubset(set(agent.permissions or [])) or {"submit_payment", "approve_payment"}.issubset(set(agent.permissions or [])):
        add("GOV-009", "high", "Conflicting duties in one agent", [f"Conflicting permissions: {', '.join(sorted(set(agent.permissions) & {'request_access', 'approve_access', 'submit_payment', 'approve_payment'}))}"], "The same agent can initiate and approve a sensitive workflow.", "Separate initiation and approval into distinct principals and require reviewer attribution.")
    for event in agent.events or []:
        if event.get("sensitive") and not event.get("approved"):
            add("GOV-010", "critical", "Unapproved sensitive action observed", [f"Event: {event.get('action', 'unknown')}", f"Timestamp: {event.get('timestamp', 'unknown')}", "Approval evidence: missing"], "Synthetic activity evidence records a sensitive action without approval.", "Suspend the action path, preserve the audit evidence, and require human review.")
            break

    score = min(100, sum(SEVERITY_WEIGHT[item["severity"]] for item in findings))
    level = "critical" if score >= 70 else "high" if score >= 40 else "medium" if score >= 15 else "low"
    return {"findings": findings, "risk_score": score, "risk_level": level}
