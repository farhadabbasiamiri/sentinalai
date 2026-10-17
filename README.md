# SentinelAI

**AI Agent Governance and Permission Monitoring System** is a local-first capstone MVP for inventorying synthetic AI agents, identifying excessive access, explaining rule matches, and proposing safe human-reviewed remediations.

> All records are synthetic. Scores are project-specific decision-support indicators, not proof of compromise or a security certification. No production accounts, credentials, or external agents are connected.

## Problem and Users

Agent capabilities often grow faster than ownership and review processes. SentinelAI gives security analysts and platform governance teams a compact inventory, deterministic least-privilege checks, policy-linked evidence, and an auditable approval workflow. The MVP is designed for a classroom demonstration and repeatable synthetic evaluation.

## Scope

Included: 36 idempotently seeded agents, SQLite persistence, 10 deterministic governance rules, risk scoring, optional local Ollama narrative, keyword policy retrieval, review tool traces, findings, synthetic approval/apply simulation, audit log, CSV/JSON exports, dashboard charts, and a labeled evaluation runner.

Out of scope: production integrations, authentication/authorization, real account changes, external scanning, hosted LLMs, production readiness, vector-database installation, and comprehensive legal/compliance mapping. The local API is intended for a trusted development machine only.

## Features

- **Overview:** live inventory metrics, risk distribution, findings by rule, highest-risk agents, and audit activity.
- **Agent registry/details:** search by name/ID, filter by owner/status/risk/tool/sensitivity, inspect scopes/tools/data categories, and run evaluations.
- **Governance findings:** evidence, severity, policy rule, remediation, reviewed state, and remediation proposals.
- **Review workflow:** the bounded agent invokes `get_agent_profile`, `evaluate_agent_permissions`, and `search_governance_policies`; the UI shows arguments and returned data. Ollama is optional; deterministic fallback is labeled honestly.
- **Policy explorer:** editable Markdown source, deterministic rule catalogue, keyword retrieval, and local section references.
- **Approval queue:** pending, approved, rejected, and applied-in-simulation states. Approval and explicit application confirmation are separate. Only synthetic SQLite records change.
- **Audit and reports:** review/tool/policy/approval events, audit CSV, findings CSV/JSON, and measured evaluation output.
- **Settings:** API/database status, active review mode, and safe local configuration guidance. No secret values are displayed.

## Stack and Layout

- Frontend: React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, SQLite, pytest.
- Optional local narrative: Ollama via HTTP; no API key required.
- Retrieval: local keyword matching by default. Sentence Transformers/Chroma are intentionally not installed because the MVP must run offline without downloading embedding models.

```text
backend/app/       API, models, policy engine, review agent, retrieval, policy text
backend/tests/     API, policy, safety and workflow tests
frontend/src/      React dashboard and API client
data/              labeled evaluation cases and generated sample exports
scripts/            data export and evaluation runners
docs/               architecture, security, data card, demo
reports/evaluation/ generated actual metrics
```

See [docs/architecture.md](docs/architecture.md), [docs/security.md](docs/security.md), [docs/data-card.md](docs/data-card.md), and [CONTRIBUTIONS.md](CONTRIBUTIONS.md).

## Local Setup

Requirements: Python 3.10+ and Node.js 20+ (validated here with Python 3.10.10 and Node 22.15.0).

### Windows PowerShell

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Terminal 1, backend:

```powershell
Push-Location backend
python -m uvicorn app.main:app --reload --port 8000
```

Terminal 2, frontend:

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

Open <http://127.0.0.1:5173>. API health is <http://127.0.0.1:8000/api/health>; interactive OpenAPI docs are <http://127.0.0.1:8000/docs>. SQLite and 36 seed records initialize on the first API startup.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

In one terminal:

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

In another terminal at the repository root:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

### Optional Ollama

The no-LLM fallback is the default and needs no configuration. To use a locally installed Ollama model, set `OLLAMA_URL` to the local Ollama API endpoint and `OLLAMA_MODEL` to a model available locally. Example PowerShell values:

```powershell
$env:OLLAMA_URL = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "llama3.2"
```

No credentials should be entered. The review agent passes only synthetic profile evidence. If Ollama is absent, times out, or returns invalid JSON, the workflow uses and labels deterministic fallback mode. `.env.example` lists the optional variables.

### Docker (Optional)

Docker was unavailable in the implementation environment, so this path is supplied but not runtime-verified:

```bash
docker compose up --build
```

The UI is at port 5173 and API at port 8000. SQLite is stored in the named `sentinel-data` volume. No destructive volume-removal command is included.

## Governance and Risk Method

The engine applies explicit rules `GOV-001` through `GOV-010` for purpose mismatch, broad scopes, sensitive data without approval, dangerous tools, ownership, stale access, admin tools, missing action approvals, conflicting duties, and unapproved sensitive events. Policy text is editable at `backend/app/policies/governance.md`.

Project-specific score formula:

```text
risk score = min(100, sum of matched finding weights)
low = 0–14; medium = 15–39; high = 40–69; critical = 70–100
weights: low 5, medium 12, high 22, critical 32
```

These weights/bands are capstone evaluation choices, not industry thresholds. The deterministic engine owns risk/finding results; the LLM cannot override them. Remediations remain proposals until a human approves and separately confirms local simulation.

## Review-Agent Workflow

```text
Request -> validate agent ID -> get_agent_profile -> evaluate_agent_permissions
        -> search_governance_policies -> structured report -> audit tool calls
```

Profile descriptions, logs, and retrieved policy text are untrusted evidence, never instructions. The agent can call only the three fixed tools; it has no arbitrary shell, filesystem, network scanning, or external mutation capability. Policy references always identify the local policy file and section. No match is reported as no evidence, not an invented citation.

## REST API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health`, `/api/ready` | Health and readiness |
| GET/POST/PUT | `/api/agents` | Paginated/filterable synthetic registry, create and update |
| GET | `/api/agents/{agent_id}` | Profile and findings |
| POST | `/api/agents/{agent_id}/evaluate` | Deterministic review |
| POST | `/api/reviews` | Bounded governance review with tool traces |
| GET | `/api/findings` | Filtered findings |
| PATCH | `/api/findings/{finding_id}/review` | Mark reviewed |
| GET | `/api/policies`, `/api/policies/search?q=...` | Rules and local retrieval |
| POST | `/api/agents/{agent_id}/proposals` | Create inert remediation proposal |
| GET | `/api/approvals` | Approval queue |
| POST | `/api/approvals/{id}/decision?decision=approve\|reject` | Reviewer decision |
| POST | `/api/approvals/{id}/apply` | Explicitly confirmed synthetic application |
| GET | `/api/audit` | Audit event query |
| GET | `/api/audit/export.csv` | Audit CSV export |
| GET | `/api/reports/findings.csv`, `/api/reports/findings.json`, `/api/reports/findings.md` | CSV, JSON, and readable Markdown report exports |
| GET | `/api/evaluation` | Generated evaluation metrics |

Example review:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/reviews `
  -ContentType 'application/json' -Body '{"request":"Review SA-1002 and explain its governance risks."}'
```

Proposal application is guarded by status and confirmation. `POST /apply` returns 409 unless already approved and 422 unless the body includes `{"reviewer":"Analyst","confirmation":true}`. The Swagger UI at `/docs` includes request schemas.

## Data and Evaluation

Seed generation is deterministic in shape and idempotent by agent ID. Export snapshots with:

```powershell
python scripts/export_synthetic_data.py
```

This writes `data/synthetic_agents.json` and `.csv`. The labeled 20-case dataset is `data/evaluation_cases.json`.

Run all backend tests and regenerate measurements:

```powershell
python scripts/run_evaluation.py
```

The script evaluates exact labeled rule matches, runs pytest, exercises the local review/API/approval path, and writes `reports/evaluation/results.json`. The UI reads that generated file; it does not fabricate evaluation values. The current measured run:

| Metric | Result |
|---|---:|
| Labeled profile cases / total cases | 14 / 20 |
| Rule precision / recall / F1 | 1.0000 / 1.0000 / 1.0000 |
| False positives / false negatives | 0 / 0 |
| Backend tests passing | 10 / 10 (100%) |
| Tool-call success | 100% (3 of 3 expected tools) |
| Review response latency | 12.77 ms for the measured local fallback request |
| Human-approval enforcement | 100% (2 of 2 unauthorized attempts blocked) |
| Evidence-grounding rubric | 100% (evidence, remediation, known rule ID) |

Latency is a single local run and should not be treated as a benchmark. These results use synthetic labels and test-only workflow checks; they do not establish production readiness. Coverage percentage is not reported because a coverage plugin was not run. The final frontend dependency audit reports zero vulnerabilities.

Backend tests only:

```powershell
Push-Location backend
python -m pytest -q
Pop-Location
```

## Demo

Follow [docs/demo.md](docs/demo.md) for the 8-minute walkthrough and offline backup. Useful examples include `SA-1002` (broad scope), `SA-1004` (restricted data without approval), and `SA-1006` (stale access). Local fallback works without internet or Ollama.

## Team Contributions and License

Record actual work in [CONTRIBUTIONS.md](CONTRIBUTIONS.md); the template intentionally contains no invented names or contribution claims. Distributed under the MIT License; see [LICENSE](LICENSE).
