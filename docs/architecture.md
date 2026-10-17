# SentinelAI Architecture

## Application Flow

```mermaid
flowchart LR
    Analyst[Security analyst] --> UI[React + TypeScript dashboard]
    UI --> API[FastAPI REST API]
    API --> DB[(SQLite: synthetic agents, findings, proposals, audit)]
    API --> PE[Deterministic policy engine]
    API --> Agent[Bounded review workflow]
    Agent --> Tools[Profile, evaluation, policy search tools]
    Tools --> DB
    Tools --> Policy[Local Markdown policy corpus]
    Agent -. optional local narrative .-> Ollama[Ollama on localhost]
    Agent --> Audit[Audit event writer]
    Audit --> DB
```

The deterministic engine is the authority for rule matches and numerical scores. The optional Ollama endpoint can summarize only the structured evidence already returned by the tools. If unavailable or malformed, the workflow returns a clearly labeled deterministic fallback.

## Data Model

```mermaid
erDiagram
    AGENT ||--o{ FINDING : produces
    AGENT ||--o{ APPROVAL : has_proposal
    AGENT {
      string agent_id PK
      string owner
      string status
      json tools
      json permissions
      json scopes
      json data_categories
      int risk_score
      string risk_level
    }
    FINDING {
      string finding_id PK
      string agent_id FK
      string rule_id
      string severity
      json evidence
      string status
    }
    APPROVAL {
      string approval_id PK
      string agent_id FK
      string status
      json current_configuration
      json proposed_change
      string reviewer
      datetime decision_at
      datetime applied_at
    }
    AUDIT_EVENT {
      string event_id PK
      string action
      string object_type
      string object_id
      json details
      datetime created_at
    }
```

`AUDIT_EVENT` is append-only through application routes and is intentionally independent of user PII. SQLite initializes at `backend/sentinelai.db` and seed creation is idempotent.

## Boundaries

- The agent has three fixed, schema-validated tools; no shell, arbitrary filesystem, external scanning, or live account mutation tools exist.
- Policy citations point to sections in `backend/app/policies/governance.md`.
- Proposals are inert records. Approval and explicit apply confirmation are separate requests.
- Apply operations mutate only local synthetic SQLite rows and are recorded in audit events.
