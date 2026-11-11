#!/usr/bin/env python3
"""
generate_synthetic_logs.py — Area 2: Synthetic Data & Database
SentinelAI Capstone Project

Generates realistic cybersecurity log entries for diverse Sudbury-area
institutions, healthcare networks, regional banks, and corporate IT
infrastructure.  Exports to both JSON and CSV inside the project's data/
directory, then computes an analytics summary saved to data/log_summary.json.

The script is idempotent: re-running it overwrites all output files cleanly
and writes the CSV from scratch (no duplicate headers or appended rows).

Usage:
    python scripts/generate_synthetic_logs.py              # 500 records (default)
    python scripts/generate_synthetic_logs.py --count 2000 # custom count
    python scripts/generate_synthetic_logs.py --seed 42    # reproducible output
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
# Configuration — organisations, event templates, and severity profiles
# ---------------------------------------------------------------------------

# Sudbury-area educational institutions
EDUCATIONAL_ORGS = [
    "Laurentian University",
    "Collège Boréal",
    "Sudbury Secondary School",
    "Cambrian College",
    "Lo-Ellen Park Secondary School",
    "Lasalle Secondary School",
]

# Local / regional healthcare networks
HEALTHCARE_ORGS = [
    "Health Sciences North",
    "Sudbury Community Health Centre",
    "Northern Ontario School of Medicine",
    "Manitoulin Health Centre",
    "Sudbury District Nurse Practitioner Clinics",
]

# Regional banks and financial services
FINANCIAL_ORGS = [
    "Sudbury Credit Union",
    "Northern Savings Bank",
    "Greater Sudbury Municipal Finance",
    "Cambrian Financial Services",
]

# Corporate / industrial IT infrastructure
CORPORATE_ORGS = [
    "Vale Canada – Sudbury Operations",
    "Glencore Sudbury Integrated Nickel Operations",
    "KGHM International – Sudbury",
    "Sudbury Hydro IT Division",
    "City of Greater Sudbury – IT Services",
    "Dynamic Earth – Science North",
]

ALL_ORGANIZATIONS = (
    EDUCATIONAL_ORGS
    + HEALTHCARE_ORGS
    + FINANCIAL_ORGS
    + CORPORATE_ORGS
)

# Sector lookup for analytics
ORG_SECTOR: dict[str, str] = {}
for _org in EDUCATIONAL_ORGS:
    ORG_SECTOR[_org] = "Education"
for _org in HEALTHCARE_ORGS:
    ORG_SECTOR[_org] = "Healthcare"
for _org in FINANCIAL_ORGS:
    ORG_SECTOR[_org] = "Financial Services"
for _org in CORPORATE_ORGS:
    ORG_SECTOR[_org] = "Corporate / Industrial"

# Event types paired with plausible severity distributions.
# Each tuple: (event_type, allowed_severities_with_weights)
EVENT_PROFILES: list[tuple[str, list[tuple[str, int]]]] = [
    ("Unauthorized Access Attempt",  [("Medium", 3), ("High", 5), ("Critical", 2)]),
    ("Brute Force Login",            [("Medium", 2), ("High", 5), ("Critical", 3)]),
    ("Malware Detected",             [("High", 4), ("Critical", 6)]),
    ("Suspicious API Call",          [("Low", 2), ("Medium", 5), ("High", 3)]),
    ("Successful Admin Login",       [("Low", 7), ("Medium", 3)]),
    ("Phishing Email Reported",      [("Medium", 4), ("High", 4), ("Critical", 2)]),
    ("Data Exfiltration Attempt",    [("High", 3), ("Critical", 7)]),
    ("Firewall Rule Violation",      [("Low", 3), ("Medium", 5), ("High", 2)]),
    ("Privilege Escalation",         [("High", 4), ("Critical", 6)]),
    ("Anomalous Network Traffic",    [("Low", 2), ("Medium", 4), ("High", 3), ("Critical", 1)]),
    ("Failed MFA Verification",      [("Low", 3), ("Medium", 5), ("High", 2)]),
    ("Ransomware Indicator",         [("Critical", 10)]),
    ("Port Scan Detected",           [("Low", 4), ("Medium", 5), ("High", 1)]),
    ("SQL Injection Attempt",        [("High", 5), ("Critical", 5)]),
    ("Insider Threat Alert",         [("Medium", 3), ("High", 4), ("Critical", 3)]),
]

# Action responses mapped by severity — higher severity triggers stronger actions
ACTIONS_BY_SEVERITY: dict[str, list[str]] = {
    "Low":      ["Logged"],
    "Medium":   ["Logged", "Alert Sent"],
    "High":     ["Blocked", "Alert Sent", "Escalated"],
    "Critical": ["Blocked", "Alert Sent", "Escalated"],
}

# User-ID templates — mixed roles from different org types
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

# ---------------------------------------------------------------------------
# Internal-use realistic IPv4 address pools (RFC 1918 + documentation ranges)
# ---------------------------------------------------------------------------

# We use several private/documentation ranges so the IPs look varied but are
# never routable on the public internet.
IP_PREFIXES = [
    "10.0.",       # internal LAN – education
    "10.1.",       # internal LAN – healthcare
    "10.2.",       # internal LAN – finance
    "10.10.",      # internal LAN – corporate
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
    """Return a realistic-looking private/documentation IPv4 address."""
    prefix = random.choice(IP_PREFIXES)
    # Determine how many octets are already present
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
    return template  # fallback


def _random_timestamp(*, days_back: int = 30) -> str:
    """Return an ISO-8601 timestamp within the last *days_back* days."""
    now = datetime.now(tz=timezone.utc)
    offset = timedelta(
        seconds=random.randint(0, days_back * 86_400),
    )
    dt = now - offset
    return dt.isoformat(timespec="seconds")


def _pick_severity(profile: list[tuple[str, int]]) -> str:
    """Weighted random choice of severity from an event profile."""
    severities, weights = zip(*profile)
    return random.choices(severities, weights=weights, k=1)[0]


def _pick_action(severity: str) -> str:
    """Choose an action appropriate for the given severity level."""
    return random.choice(ACTIONS_BY_SEVERITY[severity])


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------

def generate_log_entry() -> dict:
    """Build and return a single synthetic cybersecurity log record."""
    event_type, severity_profile = random.choice(EVENT_PROFILES)
    severity = _pick_severity(severity_profile)

    return {
        "log_id":            str(uuid.uuid4()),
        "timestamp":         _random_timestamp(),
        "organization_name": random.choice(ALL_ORGANIZATIONS),
        "source_ip":         _random_ip(),
        "user_id":           _random_user_id(),
        "event_type":        event_type,
        "severity":          severity,
        "action_taken":      _pick_action(severity),
    }


def generate_logs(count: int = 500, *, seed: int | None = None) -> list[dict]:
    """
    Generate *count* synthetic log entries.

    Parameters
    ----------
    count : int
        Number of records to create.
    seed : int | None
        Optional RNG seed for reproducible output.
    """
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
]


def export_json(records: list[dict], path: Path) -> None:
    """Write records to a JSON file (overwrites cleanly on re-run)."""
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Exported {len(records)} records → {path}")


def export_csv(records: list[dict], path: Path) -> None:
    """
    Write records to a CSV file.

    The file is opened in write-mode ('w') so re-running the script always
    produces a single header row — no duplicate headers or appended rows.
    """
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
    Analyse the generated log records and return a structured summary dict.

    The summary is designed to be consumed by the backend dashboard team
    and serves as a quick statistical validation for capstone evaluators.
    """
    now = datetime.now(tz=timezone.utc)

    # --- Severity breakdown ------------------------------------------------
    severity_counter = Counter(r["severity"] for r in records)
    severity_breakdown = {
        level: severity_counter.get(level, 0)
        for level in ("Low", "Medium", "High", "Critical")
    }

    # --- Top targeted organizations (sorted descending) --------------------
    org_counter = Counter(r["organization_name"] for r in records)
    top_targeted_organizations = [
        {"organization_name": name, "event_count": count}
        for name, count in org_counter.most_common()
    ]

    # --- Top event types (sorted descending) -------------------------------
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

    # --- Unique counts -----------------------------------------------------
    unique_ips = len({r["source_ip"] for r in records})
    unique_users = len({r["user_id"] for r in records})
    unique_orgs = len({r["organization_name"] for r in records})

    # --- Threat score (simple metric for dashboard) ------------------------
    # Weighted sum: Critical=4, High=3, Medium=2, Low=1, normalized to 0–100
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

    return {
        "total_logs_generated": len(records),
        "severity_breakdown": severity_breakdown,
        "action_breakdown": action_breakdown,
        "top_targeted_organizations": top_targeted_organizations,
        "top_event_types": top_event_types,
        "sector_breakdown": sector_breakdown,
        "unique_source_ips": unique_ips,
        "unique_user_ids": unique_users,
        "unique_organizations": unique_orgs,
        "threat_index": threat_index,
        "time_range": {
            "earliest": earliest,
            "latest": latest,
        },
        "last_updated": now.isoformat(timespec="seconds"),
        "generator": "SentinelAI Area 2 — generate_synthetic_logs.py",
    }


def export_summary(summary: dict, path: Path) -> None:
    """Write the analytics summary to a JSON file (overwrites on re-run)."""
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ Exported analytics summary → {path}")


def print_summary_table(summary: dict) -> None:
    """
    Print a formatted terminal summary table.

    Designed for quick professor demo: shows generation stats, severity
    breakdown, top threats, and top targeted institutions at a glance.
    """
    sep = "─" * 62

    print(f"\n  {sep}")
    print(f"  {'SentinelAI — Area 2: Log Analytics Summary':^62}")
    print(f"  {sep}")

    # --- Overview stats ----------------------------------------------------
    print(f"  {'Total logs generated':<36} {summary['total_logs_generated']:>24,}")
    print(f"  {'Unique source IPs':<36} {summary['unique_source_ips']:>24,}")
    print(f"  {'Unique user IDs':<36} {summary['unique_user_ids']:>24,}")
    print(f"  {'Monitored organizations':<36} {summary['unique_organizations']:>24}")
    print(f"  {'Threat index (0–100)':<36} {summary['threat_index']:>24}")

    # --- Severity breakdown ------------------------------------------------
    print(f"\n  {sep}")
    print(f"  {'SEVERITY BREAKDOWN':^62}")
    print(f"  {sep}")
    total = summary["total_logs_generated"]
    for level in ("Critical", "High", "Medium", "Low"):
        count = summary["severity_breakdown"][level]
        pct = (count / total * 100) if total else 0
        bar = "█" * int(pct / 2.5)
        print(f"  {level:<12} {count:>6}  ({pct:5.1f}%)  {bar}")

    # --- Action breakdown --------------------------------------------------
    print(f"\n  {sep}")
    print(f"  {'ACTION TAKEN BREAKDOWN':^62}")
    print(f"  {sep}")
    for action in ("Blocked", "Alert Sent", "Escalated", "Logged"):
        count = summary["action_breakdown"].get(action, 0)
        pct = (count / total * 100) if total else 0
        print(f"  {action:<16} {count:>6}  ({pct:5.1f}%)")

    # --- Sector breakdown --------------------------------------------------
    print(f"\n  {sep}")
    print(f"  {'SECTOR BREAKDOWN':^62}")
    print(f"  {sep}")
    for entry in summary["sector_breakdown"]:
        pct = (entry["event_count"] / total * 100) if total else 0
        print(f"  {entry['sector']:<28} {entry['event_count']:>6}  ({pct:5.1f}%)")

    # --- Top 5 targeted organizations --------------------------------------
    print(f"\n  {sep}")
    print(f"  {'TOP 5 TARGETED ORGANIZATIONS':^62}")
    print(f"  {sep}")
    for entry in summary["top_targeted_organizations"][:5]:
        print(f"  {entry['organization_name']:<44} {entry['event_count']:>6} events")

    # --- Top 5 event types -------------------------------------------------
    print(f"\n  {sep}")
    print(f"  {'TOP 5 THREAT EVENT TYPES':^62}")
    print(f"  {sep}")
    for entry in summary["top_event_types"][:5]:
        print(f"  {entry['event_type']:<44} {entry['count']:>6} events")

    # --- Time range & metadata ---------------------------------------------
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
        description="SentinelAI — Generate synthetic cybersecurity log data with analytics",
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

    # Resolve the project's data/ directory (one level up from scripts/)
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # --- Phase 1: Generate synthetic logs ----------------------------------
    print(f"Generating {args.count} synthetic cyber-security log entries …")
    records = generate_logs(args.count, seed=args.seed)

    # Sort chronologically for readability
    records.sort(key=lambda r: r["timestamp"])

    export_json(records, data_dir / "cyber_logs.json")
    export_csv(records,  data_dir / "cyber_logs.csv")

    # --- Phase 2: Compute analytics summary --------------------------------
    print("\nComputing analytics summary …")
    summary = compute_summary(records)
    export_summary(summary, data_dir / "log_summary.json")

    # --- Phase 3: Print terminal report ------------------------------------
    print_summary_table(summary)
    print("  All Area 2 outputs generated successfully ✓")


if __name__ == "__main__":
    main()
