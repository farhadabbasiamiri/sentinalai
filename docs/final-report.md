# SentinelAI Final Project Report

## 1. Introduction

This report documents the completed SentinelAI MVP, a local-first governance and permission monitoring system for synthetic AI agents. The project addresses a core governance problem in AI operations: permissions and tool access often outpace review and accountability. SentinelAI provides a structured way to inventory agents, identify governance violations, and support human approval before changes are simulated.

The project was developed as part of the Agent Governance theme in the applied AI agents for cybersecurity operations capstone brief. It is intentionally designed as a defensive, research-oriented MVP rather than a production-grade enterprise platform.

## 2. Problem statement

AI systems increasingly combine broad scopes, sensitive data categories, and autonomous actions. Without a clear governance layer, the risk of over-privileged agents and unsafe workflow combinations increases. This project addresses that challenge by creating a deterministic rule engine that evaluates agent behavior against governance checks and presents the results in an auditable way.

## 3. Project objectives

The key project goals were to:

- inventory synthetic AI agents and their permissions
- evaluate governance risks using deterministic policies
- provide explainable evidence for each finding
- support a human approval queue and simulated remediation
- expose results in a dashboard interface
- enable evaluation and documentation for capstone presentation

## 4. System overview

The SentinelAI system has four main layers:

1. Data layer: SQLite database seeded with synthetic agent profiles and audit events.
2. Policy engine: deterministic rules that compute governance findings and risk scores.
3. API layer: FastAPI endpoints for queries, approval decisions, and report exports.
4. Frontend layer: React dashboard for inspection, review, and navigation.
5. Optional Gradio layer: lightweight dashboard for demo use and agent review execution.

## 5. Architecture and design

The architecture follows a simple request-response design with explicit evidence and review flow. Each synthetic agent is represented by a profile containing metadata such as name, tools, permissions, scopes, sensitivity, owner, activity, and events.

The policy engine computes structured findings such as:

- broad scopes or wildcard permissions
- sensitive data access without approval
- dangerous tool combinations
- stale access and inactive agents
- missing ownership or approval gaps
- conflicting duties in a single agent

The final output is a risk score and a risk level, together with remediation suggestions and evidence items.

## 6. Data sources and database design

The project uses synthetic data instead of live enterprise information. The database is seeded with realistic but non-sensitive agent records that simulate operational use cases from a governance perspective.

The database stores:

- agents
- findings
- approvals
- audit events

This design makes the project reproducible, easy to evaluate, and suitable for student demos.

## 7. Model and AI workflow

The project uses a hybrid approach:

- deterministic policy logic as the primary decision engine
- optional local Ollama integration for narrative summarization
- keyword policy retrieval for references and local evidence grounding

The central design principle is that the rule engine is authoritative. The LLM is used only for narrative support and explanation when available, while the governance result remains grounded in deterministic logic.

## 8. Backend implementation

The backend is implemented in Python with FastAPI. It exposes REST endpoints for:

- health and readiness checks
- agent listing and filtering
- agent profile retrieval
- risk evaluation
- findings review
- policy search
- approval proposals and decisions
- audit log access
- report export in CSV, JSON, and Markdown formats

This layer handles validation, database access, and evidence generation. It is also responsible for the final approval simulation and audit events.

## 9. Frontend implementation

The frontend is implemented with React and Vite. It provides:

- overview charts and summary metrics
- agent registry views
- agent detail pages
- governance findings and filters
- policy explorer sections
- approval queue and actions
- evaluation and reporting access

This interface makes the model output understandable to a human reviewer and supports the capstone demo narrative.

## 10. Gradio dashboard

A lightweight Gradio interface is included to support a simpler demo surface. It allows a reviewer to:

- enter an agent ID
- query the API
- inspect the agent summary
- review generated findings and governance output

This dashboard complements the React UI and makes it easier to demonstrate the workflow in a local environment.

## 11. Testing and evaluation

The project includes automated tests for:

- backend API behavior
- risk evaluation logic
- policy detection
- approval flow enforcement
- review request handling

The verification run confirms the backend and frontend are working in the local environment. The backend suite passed successfully, and the React frontend built successfully in production mode.

## 12. Results and findings

The system produced structured results including:

- risk score per agent
- governance findings with severity and evidence
- remediation suggestions
- approval queue information
- audit records for all significant actions

These outputs demonstrate that the MVP can support real governance workflows in a controlled educational setting.

## 13. Limitations

This project is intentionally limited to a defensive demonstration. It does not claim to be a production-ready security platform. Limitations include:

- synthetic data only
- no live enterprise integrations
- no production authentication or authorization layer
- no external scanning or privileged platform access
- no real-world incident response automation

## 14. Future improvements

The next major improvements could include:

- stronger CI and automated release checks
- more complete Gradio + dashboard integration
- richer reporting and visual analysis
- structured dependency and container security review
- improved documentation and demo capture for presentation

## 15. Conclusion

SentinelAI demonstrates a successful prototype of an AI governance monitoring system. It combines deterministic risk evaluation, auditability, approval flows, and user-friendly reporting in a compact project structure. The system is well aligned with the capstone theme and provides a compelling demonstration of how AI governance tools can help analysts understand and manage over-privileged agents.
