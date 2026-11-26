#!/usr/bin/env python3
"""
generate_synthetic_logs.py - Area 2: Synthetic Data & Database
SentinelAI Capstone Project - Laurentian University, Fall 2026

Generates realistic, industry-standard cybersecurity log entries for diverse
Greater Sudbury institutions, healthcare networks, regional banks, and
corporate IT/industrial infrastructure.

Features:
- MITRE ATT&CK framework mapping (Technique ID and Tactic / Threat Category)
- Realistic regional network zones (Campus-Wi-Fi, Clinical-EHR, SCADA, etc.)
- Export to JSON and CSV in data/
- Automated statistical summary with threat index exported to data/log_summary.json
- Formatted ASCII terminal presentation table for live evaluation

Usage:
    python scripts/generate_synthetic_logs.py              # 500 records (default)
    python scripts/generate_synthetic_logs.py --count 1000 # custom record count
    python scripts/generate_synthetic_logs.py --seed 42    # reproducible generation
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration - organisations, sectors, and network zones
# ---------------------------------------------------------------------------

EDUCATIONAL_ORGS = [
    "Laurentian University",
    "Collège Boréal",
    "Sudbury Secondary School",
    "Cambrian College",
    "Lo-Ellen Park Secondary School",
    "Lasalle Secondary School",
]

HEALTHCARE_ORGS = [
    "Health Sciences North",
    "Sudbury Community Health Centre",
    "Northern Ontario School of Medicine",
    "Manitoulin Health Centre",
    "Sudbury District Nurse Practitioner Clinics",
]

FINANCIAL_ORGS = [
    "Sudbury Credit Union",
    "Northern Savings Bank",
    "Greater Sudbury Municipal Finance",
    "Cambrian Financial Services",
]

CORPORATE_ORGS = [
    "Vale Canada - Sudbury Operations",
    "Glencore Sudbury Integrated Nickel Operations",
    "KGHM International - Sudbury",
    "Sudbury Hydro IT Division",
    "City of Greater Sudbury - IT Services",
    "Dynamic Earth - Science North",
]

ALL_ORGANIZATIONS = (
    EDUCATIONAL_ORGS
    + HEALTHCARE_ORGS
    + FINANCIAL_ORGS
    + CORPORATE_ORGS
)

ORG_SECTOR: dict[str, str] = {}
for _org in EDUCATIONAL_ORGS:
    ORG_SECTOR[_org] = "Education"
for _org in HEALTHCARE_ORGS:
    ORG_SECTOR[_org] = "Healthcare"
for _org in FINANCIAL_ORGS:
    ORG_SECTOR[_org] = "Financial Services"
for _org in CORPORATE_ORGS:
    ORG_SECTOR[_org] = "Corporate / Industrial"

# Regional Network Zones paired with sectors for authentic SIEM telemetry
SECTOR_NETWORK_ZONES = {
    "Education": [
        "Campus-Wi-Fi",
        "Student-Portal-VLAN",
        "Research-LAN",
        "Academic-Core-Net",
    ],
    "Healthcare": [
        "Clinical-EHR-Zone",
        "Hospital-Core-LAN",
        "Telemetry-VLAN",
        "Patient-Kiosk-Net",
    ],
    "Financial Services": [
        "Core-Banking-Zone",
        "ATM-Branch-VLAN",
        "Treasury-Secure-LAN",
        "Client-Portal-Net",
    ],
    "Corporate / Industrial": [
        "SCADA-Industrial-Net",
        "Smelter-Operations-LAN",
        "Corporate-DMZ",
        "Mine-Automation-VLAN",
    ],
}

# ---------------------------------------------------------------------------
# Event profiles with MITRE ATT&CK Framework Mapping
# Tuple structure:
# (event_type, mitre_id, threat_category, severity_distribution_weights)
# ---------------------------------------------------------------------------

EVENT_METADATA: list[tuple[str, str, str, list[tuple[str, int]]]] = [
    ("Unauthorized Access Attempt",  "T1078",     "Initial Access",       [("Medium", 3), ("High", 5), ("Critical", 2)]),
    ("Brute Force Login",            "T1110",     "Credential Access",    [("Medium", 2), ("High", 5), ("Critical", 3)]),
    ("Malware Detected",             "T1204",     "Execution",            [("High", 4), ("Critical", 6)]),
    ("Suspicious API Call",          "T1059",     "Execution",            [("Low", 2), ("Medium", 5), ("High", 3)]),
    ("Successful Admin Login",       "T1078.002", "Defense Evasion",      [("Low", 7), ("Medium", 3)]),
    ("Phishing Email Reported",      "T1566",     "Initial Access",       [("Medium", 4), ("High", 4), ("Critical", 2)]),
    ("Data Exfiltration Attempt",    "T1048",     "Exfiltration",         [("High", 3), ("Critical", 7)]),
    ("Firewall Rule Violation",      "T1562",     "Defense Evasion",      [("Low", 3), ("Medium", 5), ("High", 2)]),
    ("Privilege Escalation",         "T1068",     "Privilege Escalation", [("High", 4), ("Critical", 6)]),
    ("Anomalous Network Traffic",    "T1071",     "Command & Control",    [("Low", 2), ("Medium", 4), ("High", 3), ("Critical", 1)]),
    ("Failed MFA Verification",      "T1111",     "Credential Access",    [("Low", 3), ("Medium", 5), ("High", 2)]),
    ("Ransomware Indicator",         "T1486",     "Impact",               [("Critical", 10)]),
    ("Port Scan Detected",           "T1046",     "Discovery",            [("Low", 4), ("Medium", 5), ("High", 1)]),
    ("SQL Injection Attempt",        "T1190",     "Initial Access",       [("High", 5), ("Critical", 5)]),
    ("Insider Threat Alert",         "T1087",     "Discovery",            [("Medium", 3), ("High", 4), ("Critical", 3)]),
]

ACTIONS_BY_SEVERITY: dict[str, list[str]] = {
    "Low":      ["Logged"],
    "Medium":   ["Logged", "Alert Sent"],
    "High":     ["Blocked", "Alert Sent", "Escalated"],
    "Critical": ["Blocked", "Alert Sent", "Escalated"],
}

USER_ID_TEMPLATES = [
    "user_{n}",
    "admin_{dept}",
    "svc_{app}",
    "student_{n}",
    "nurse_{n}",
    "analyst_{n}",
    "dev_{n}",
    "guest_{n}",
]

DEPT_TAGS = ["sec", "net", "db", "hr", "fin", "ops", "dev", "infra"]
APP_TAGS  = ["portal", "erp", "vpn", "backup", "monitor", "api_gw", "ldap"]

# Realistic IPv4 address pools (RFC 1918 + RFC 5737 documentation ranges)
IP_PREFIXES = [
    "10.0.",       # internal LAN - education
    "10.1.",       # internal LAN - healthcare
    "10.2.",       # internal LAN - finance
    "10.10.",      # internal LAN - corporate
    "172.16.",     # private range
    "172.17.",     # private range
    "192.168.1.",  # small-office
    "192.168.50.", # campus Wi-Fi
    "198.51.100.", # RFC 5737 TEST-NET-2 (documentation)
    "203.0.113.",  # RFC 5737 TEST-NET-3 (documentation)
]

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _random_ip() -> str:
    """Return a realistic private/documentation IPv4 address."""
    prefix = random.choice(IP_PREFIXES)
    existing_octets = prefix.count(".")
    remaining = 4 - existing_octets
    suffix = ".".join(str(random.randint(1, 254)) for _ in range(remaining))
    return prefix + suffix


def _random_user_id() -> str:
    """Generate a plausible user identifier."""
    template = random.choice(USER_ID_TEMPLATES)
    if "{n}" in template:
        return template.replace("{n}", str(random.randint(100, 9999)))
    if "{dept}" in template:
        return template.replace("{dept}", random.choice(DEPT_TAGS))
    if "{app}" in template:
        return template.replace("{app}", random.choice(APP_TAGS))
    return template


def _random_timestamp(*, days_back: int = 30) -> str:
    """Return an ISO-8601 timestamp within the last days_back days."""
    now = datetime.now(tz=timezone.utc)
    offset = timedelta(seconds=random.randint(0, days_back * 86_400))
    dt = now - offset
    return dt.isoformat(timespec="seconds")


def _pick_severity(profile: list[tuple[str, int]]) -> str:
    """Weighted random choice of severity."""
    severities, weights = zip(*profile)
    return random.choices(severities, weights=weights, k=1)[0]


def _pick_action(severity: str) -> str:
    """Choose defensive action based on severity."""
    return random.choice(ACTIONS_BY_SEVERITY[severity])


def _pick_network_zone(org_name: str) -> str:
    """Choose a network zone corresponding to the organization's sector."""
    sector = ORG_SECTOR.get(org_name, "Education")
    return random.choice(SECTOR_NETWORK_ZONES.get(sector, ["General-LAN"]))


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------

def generate_log_entry() -> dict:
    """Build and return a single synthetic cybersecurity log record."""
    event_type, mitre_id, threat_category, severity_profile = random.choice(EVENT_METADATA)
    severity = _pick_severity(severity_profile)
    org_name = random.choice(ALL_ORGANIZATIONS)

    return {
        "log_id":            str(uuid.uuid4()),
        "timestamp":         _random_timestamp(),
        "organization_name": org_name,
        "source_ip":         _random_ip(),
        "user_id":           _random_user_id(),
        "event_type":        event_type,
        "severity":          severity,
        "action_taken":      _pick_action(severity),
        "mitre_id":          mitre_id,
        "threat_category":   threat_category,
        "network_zone":      _pick_network_zone(org_name),
    }


def generate_logs(count: int = 500, *, seed: int | None = None) -> list[dict]:
    """Generate count synthetic log entries with reproducible RNG support."""
    if seed is not None:
        random.seed(seed)
    return [generate_log_entry() for _ in range(count)]


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

FIELDNAMES = [
    "log_id",
    "timestamp",
    "organization_name",
    "source_ip",
    "user_id",
    "event_type",
    "severity",
    "action_taken",
    "mitre_id",
    "threat_category",
    "network_zone",
]


def export_json(records: list[dict], path: Path) -> None:
    """Write records to a JSON file (clean overwrite on re-run)."""
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Exported {len(records)} records → {path}")


def export_csv(records: list[dict], path: Path) -> None:
    """Write records to a CSV file (clean header, no row appending)."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)
    print(f"  ✓ Exported {len(records)} records → {path}")


# ---------------------------------------------------------------------------
# Analytics & Summary Generator (Area 2 reporting feature)
# ---------------------------------------------------------------------------

def compute_summary(records: list[dict]) -> dict:
    """
    Analyse log records and produce an advanced analytics summary
    including MITRE ATT&CK coverage, threat categories, and campaign clusters.
    """
    now = datetime.now(tz=timezone.utc)

    # --- Severity breakdown ------------------------------------------------
    severity_counter = Counter(r["severity"] for r in records)
    severity_breakdown = {
        level: severity_counter.get(level, 0)
        for level in ("Low", "Medium", "High", "Critical")
    }

    # --- Top targeted organizations ----------------------------------------
    org_counter = Counter(r["organization_name"] for r in records)
    top_targeted_organizations = [
        {"organization_name": name, "event_count": count}
        for name, count in org_counter.most_common()
    ]

    # --- Top event types ---------------------------------------------------
    event_counter = Counter(r["event_type"] for r in records)
    top_event_types = [
        {"event_type": name, "count": count}
        for name, count in event_counter.most_common()
    ]

    # --- Action taken distribution -----------------------------------------
    action_counter = Counter(r["action_taken"] for r in records)
    action_breakdown = {
        action: action_counter.get(action, 0)
        for action in ("Logged", "Blocked", "Alert Sent", "Escalated")
    }

    # --- Sector-level aggregation ------------------------------------------
    sector_counter: Counter[str] = Counter()
    for r in records:
        sector = ORG_SECTOR.get(r["organization_name"], "Unknown")
        sector_counter[sector] += 1
    sector_breakdown = [
        {"sector": sector, "event_count": count}
        for sector, count in sector_counter.most_common()
    ]

    # --- MITRE ATT&CK framework distribution -------------------------------
    mitre_counter = Counter(r["mitre_id"] for r in records)
    mitre_attack_distribution = [
        {"mitre_id": k, "count": v}
        for k, v in mitre_counter.most_common()
    ]

    threat_category_counter = Counter(r["threat_category"] for r in records)
    threat_category_breakdown = [
        {"threat_category": k, "count": v}
        for k, v in threat_category_counter.most_common()
    ]

    # --- Network Zone breakdown --------------------------------------------
    zone_counter = Counter(r["network_zone"] for r in records)
    network_zone_breakdown = [
        {"network_zone": k, "count": v}
        for k, v in zone_counter.most_common()
    ]

    # --- Unique counts -----------------------------------------------------
    unique_ips = len({r["source_ip"] for r in records})
    unique_users = len({r["user_id"] for r in records})
    unique_orgs = len({r["organization_name"] for r in records})

    # --- Threat index (normalized 0-100) -----------------------------------
    max_possible = len(records) * 4
    weighted = (
        severity_breakdown["Critical"] * 4
        + severity_breakdown["High"] * 3
        + severity_breakdown["Medium"] * 2
        + severity_breakdown["Low"] * 1
    )
    threat_index = round((weighted / max_possible) * 100, 1) if max_possible else 0

    # --- Timestamp range ---------------------------------------------------
    timestamps = sorted(r["timestamp"] for r in records)
    earliest = timestamps[0] if timestamps else None
    latest = timestamps[-1] if timestamps else None

    # --- Simulated Attack Campaign Detection -------------------------------
    # Highlight top impacted institution with high severity incidents
    high_critical_orgs = Counter(
        r["organization_name"] for r in records if r["severity"] in ("High", "Critical")
    )
    top_threat_target, threat_count = high_critical_orgs.most_common(1)[0] if high_critical_orgs else ("None", 0)

    simulated_campaigns = [
        {
            "campaign_name": f"{top_threat_target} Credential & Ransomware Wave",
            "primary_target": top_threat_target,
            "critical_high_events": threat_count,
            "mitre_vectors": ["T1110 (Brute Force)", "T1486 (Ransomware)", "T1048 (Exfiltration)"],
            "status": "Contained & Monitored",
        }
    ]

    return {
        "total_logs_generated": len(records),
        "severity_breakdown": severity_breakdown,
        "action_breakdown": action_breakdown,
        "top_targeted_organizations": top_targeted_organizations,
        "top_event_types": top_event_types,
        "sector_breakdown": sector_breakdown,
        "mitre_attack_distribution": mitre_attack_distribution,
        "threat_category_breakdown": threat_category_breakdown,
        "network_zone_breakdown": network_zone_breakdown,
        "simulated_campaigns": simulated_campaigns,
        "unique_source_ips": unique_ips,
        "unique_user_ids": unique_users,
        "unique_organizations": unique_orgs,
        "threat_index": threat_index,
        "time_range": {
            "earliest": earliest,
            "latest": latest,
        },
        "last_updated": now.isoformat(timespec="seconds"),
        "compliance_standards": ["MITRE ATT&CK v14", "NIST SP 800-53", "NIST AI RMF 1.0"],
        "generator": "SentinelAI Area 2 - generate_synthetic_logs.py",
    }


def export_summary(summary: dict, path: Path) -> None:
    """Write analytics summary to JSON."""
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Exported analytics summary → {path}")


def print_summary_table(summary: dict) -> None:
    """Print a formatted terminal summary table for live capstone demonstration."""
    sep = "─" * 66

    print(f"\n  {sep}")
    print(f"  {'SentinelAI - Area 2: Cybersecurity Log Analytics':^66}")
    print(f"  {'Frameworks: MITRE ATT&CK • NIST AI RMF • Greater Sudbury SIEM':^66}")
    print(f"  {sep}")

    print(f"  {'Total logs generated':<38} {summary['total_logs_generated']:>26,}")
    print(f"  {'Unique source IPs (RFC 1918/5737)':<38} {summary['unique_source_ips']:>26,}")
    print(f"  {'Monitored regional institutions':<38} {summary['unique_organizations']:>26}")
    print(f"  {'Threat severity index (0–100)':<38} {summary['threat_index']:>26}")

    # Severity
    print(f"\n  {sep}")
    print(f"  {'SEVERITY LEVEL BREAKDOWN':^66}")
    print(f"  {sep}")
    total = summary["total_logs_generated"]
    for level in ("Critical", "High", "Medium", "Low"):
        count = summary["severity_breakdown"][level]
        pct = (count / total * 100) if total else 0
        bar = "█" * int(pct / 2.5)
        print(f"  {level:<12} {count:>6}  ({pct:5.1f}%)  {bar}")

    # MITRE ATT&CK Categories
    print(f"\n  {sep}")
    print(f"  {'MITRE ATT&CK TACTICS & CATEGORIES':^66}")
    print(f"  {sep}")
    for item in summary["threat_category_breakdown"][:5]:
        pct = (item["count"] / total * 100) if total else 0
        print(f"  {item['threat_category']:<32} {item['count']:>6} events ({pct:5.1f}%)")

    # Network Zones
    print(f"\n  {sep}")
    print(f"  {'REGIONAL NETWORK ZONES MONITORED':^66}")
    print(f"  {sep}")
    for item in summary["network_zone_breakdown"][:5]:
        pct = (item["count"] / total * 100) if total else 0
        print(f"  {item['network_zone']:<32} {item['count']:>6} events ({pct:5.1f}%)")

    # Top targeted institutions
    print(f"\n  {sep}")
    print(f"  {'TOP 5 TARGETED SUDBURY INSTITUTIONS':^66}")
    print(f"  {sep}")
    for entry in summary["top_targeted_organizations"][:5]:
        print(f"  {entry['organization_name']:<48} {entry['event_count']:>6} events")

    # Detected campaign
    if summary.get("simulated_campaigns"):
        camp = summary["simulated_campaigns"][0]
        print(f"\n  {sep}")
        print(f"  {'ACTIVE ATTACK CAMPAIGN CLUSTER DETECTED':^66}")
        print(f"  {sep}")
        print(f"  Target:     {camp['primary_target']}")
        print(f"  Incidents:  {camp['critical_high_events']} High/Critical events")
        print(f"  Vectors:    {', '.join(camp['mitre_vectors'])}")
        print(f"  Status:     {camp['status']}")

    # Time range
    print(f"\n  {sep}")
    tr = summary["time_range"]
    print(f"  {'Time range':<18} {tr['earliest'] or 'N/A'}  →  {tr['latest'] or 'N/A'}")
    print(f"  {'Report generated':<18} {summary['last_updated']}")
    print(f"  {sep}\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="SentinelAI - Generate synthetic cybersecurity log data with MITRE ATT&CK telemetry",
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=500,
        help="Number of log entries to generate (default: 500)",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="RNG seed for reproducible output (optional)",
    )
    args = parser.parse_args()

    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.count} synthetic cybersecurity log entries with MITRE ATT&CK mapping …")
    records = generate_logs(args.count, seed=args.seed)

    records.sort(key=lambda r: r["timestamp"])

    export_json(records, data_dir / "cyber_logs.json")
    export_csv(records,  data_dir / "cyber_logs.csv")

    print("\nComputing MITRE ATT&CK analytics summary …")
    summary = compute_summary(records)
    export_summary(summary, data_dir / "log_summary.json")

    print_summary_table(summary)
    print("  All Area 2 synthetic data and analytics generated successfully ✓")


if __name__ == "__main__":
    main()
