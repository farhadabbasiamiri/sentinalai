# SentinelAI

SentinelAI is a local-first AI governance and permission monitoring MVP designed for synthetic cybersecurity education and capstone demonstration. The system inventories AI agents, evaluates their permissions against governance rules, exposes audit-ready evidence, and supports a human approval workflow before simulated remediation is applied.

This repository is part of the Laurentian University capstone theme: Agent Governance and Permission Monitoring System. It is intentionally defensive and educational: all records are synthetic, no production credentials are used, and the system does not connect to live cloud accounts or real enterprise systems.

## Project purpose

Modern AI systems can accumulate broad permissions faster than ownership and review processes can track them. SentinelAI addresses this gap by providing a compact governance dashboard and policy engine that helps analysts understand:

- which agents exist and how risky they are
- which permissions or scopes are overly broad
- which rules were triggered
- what evidence supports each finding
- whether the workflow requires human approval before a simulated change is applied

## Theme alignment

This project aligns with the Agent Governance theme in the capstone brief. It focuses on:

- least-privilege review
- governance evidence and remediation
- policy-based detection for excessive access
- auditability and approval checks
- a demonstration workflow suitable for a student MVP

## Core capabilities

- Agent registry with searchable inventory and filters
- Risk scoring and rule-based governance evaluation
- 10 deterministic governance rules covering excess permission, stale access, broad scopes, sensitive data handling, admin capabilities, conflicting duties, and approval gaps
- Human approval and simulated remediation workflow
- Policy retrieval and evidence-linked explanations
- SQLite persistence and audit log history
- CSV/JSON/Markdown export endpoints
- React dashboard for overview and agent inspection
- Optional local Ollama narrative layer with deterministic fallback when unavailable
- Synthetic evaluation runner and labeled test cases

## Architecture

The system is split into a backend API, a policy engine, a database layer, and a React dashboard.

```text
User / Analyst
      |
      v
React Frontend (Vite + TypeScript)
      |
      v
FastAPI Backend
      |
      +--> Policy Engine (GOV-001 through GOV-010)
      +--> SQLAlchemy + SQLite Database
      +--> Review Agent and Retrieval Layer
      +--> Audit and Approval Records
```

## Repository structure

```text
backend/
  app/
    agent/
    core/
    policies/
    rag/
    __init__.py
    database.py
    main.py
    models.py
    schemas.py
    seed.py
  tests/
frontend/
  src/
  package.json
  vite.config.ts
  tsconfig.json
data/
  evaluation_cases.json
  synthetic_agents.csv
  synthetic_agents.json
docs/
  architecture.md
  data-card.md
  demo.md
  security.md
  final-report.md
reports/
  evaluation/
  results.json
scripts/
  export_synthetic_data.py
  run_evaluation.py
requirements.txt
README.md
AGENTS.md
CLAUDE.md
```

## Technology stack

- Backend: Python, FastAPI, SQLAlchemy, Pydantic, SQLite
- Frontend: React, TypeScript, Vite, Recharts, Lucide
- Optional AI narrative: Ollama local HTTP endpoint
- Testing: pytest
- Data export: CSV and JSON
- Deployment/demo: local development server and optional Docker Compose setup

## Governance and risk rules

The project applies the project-specific rule set GOV-001 to GOV-010, covering:

- purpose mismatch
- wildcard API scopes
- sensitive data without approval
- dangerous tool combinations
- missing owner
- stale access
- admin capability on ordinary agents
- missing approval for sensitive actions
- conflicting duties
- unapproved sensitive activity

The project intentionally keeps risk scoring deterministic and explainable. LLM output does not override the rule engine.

## Data and synthetic evaluation

Synthetic data is deterministic and idempotent by agent ID. The project stores the main samples in:

- data/synthetic_agents.json
- data/synthetic_agents.csv
- data/evaluation_cases.json

The evaluation runner executes labeled checks, policy validation, API flow checks, and report generation.

## Local setup

### Requirements

- Python 3.10+
- Node.js 20+
- Git

### Windows PowerShell

```powershell
cd "<repo-root>"
py -3.10-64 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Start the backend

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Start the frontend

```powershell
cd frontend
npm install
npm run dev
```

### Start the optional Gradio dashboard

```powershell
cd backend
python gradio_app.py
```

The app is then available at:

- Frontend: http://127.0.0.1:5173
- Backend API: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs
- Gradio dashboard: http://127.0.0.1:7860

## Optional local Ollama configuration

The default mode works without LLM access. If you want the review agent to use a local Ollama model, set:

```powershell
$env:OLLAMA_URL = "http://127.0.0.1:11434"
$env:OLLAMA_MODEL = "llama3.2"
```

If Ollama is unavailable, the system automatically falls back to deterministic policy output and clearly labels that mode.

## Usage examples

### Health check

```bash
curl http://127.0.0.1:8000/api/health
```

### Review a specific agent

```bash
curl -X POST http://127.0.0.1:8000/api/reviews \
  -H "Content-Type: application/json" \
  -d '{"request":"Review SA-1002 and explain its governance risks."}'
```

### Run the evaluation pipeline

```powershell
cd scripts
python run_evaluation.py
```

## Validation and verification

The repository has been validated in the local environment with fresh verification:

- Backend tests: 10 passed
- Frontend production build: successful
- npm dependency audit: 0 vulnerabilities

## Demo expectations

The final capstone demo should show:

1. input data or agent profile
2. the governance review pipeline
3. risk score and findings evidence
4. approval step and remediation simulation
5. dashboard output and human-in-the-loop decision making

## Report and presentation

A detailed project report is available in [docs/final-report.md](docs/final-report.md). This report covers the capstone problem statement, architecture, testing and evaluation, results, limitations, and recommendations.

## Contribution workflow

- Work on a separate branch for each feature
- Open pull requests to the main branch
- Use a CONTRIBUTIONS.md file to track team responsibilities and changes
- Keep all documentation and setup instructions reproducible

## Limitations

This is a defensive educational MVP, not a production security platform. The following are intentionally out of scope:

- real multi-tenant authentication and authorization
- live enterprise identity integration
- production security monitoring with external systems
- deployment in untrusted or internet-exposed production environments

## License

This project is distributed under the MIT license. See the LICENSE file in the repository for details.

## Team and contact

This project is designed for a graduate capstone team working on the Agent Governance theme. Contributions should be documented in the project repository and presented during the final demo period.
