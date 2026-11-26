# Synthetic Data Card

## Purpose
Demonstrate explainable permission governance and repeatable evaluation for a graduate capstone MVP.

## Composition
The generator creates 36 agents for a fictional organization using deterministic names, team labels, dates, tools, scopes, and sensitivity labels. It includes clean examples and seeded cases for wildcard scopes, missing ownership, sensitive data, stale access, administrative tools, dangerous combinations, and unapproved activity. The records contain no real university, student, employee, patient, customer, bank, or production-system information.

## Generation and Export
On first API startup, `backend/app/seed.py` creates the local SQLite inventory once. Repeated starts do not duplicate the seeded IDs. Generate portable JSON and CSV snapshots with:

```powershell
python scripts/export_synthetic_data.py
```

The script writes `data/synthetic_agents.json` and `data/synthetic_agents.csv`. They can be regenerated from the local seed set.

## Limitations
The profiles are hand-designed synthetic cases, not representative population data. Labels encode the rules deliberately included in the generator. Results do not establish real-world prevalence, production readiness, or absence of compromise.
