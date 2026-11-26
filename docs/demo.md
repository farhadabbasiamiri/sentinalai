# SentinelAI Demo Runbook (8 minutes)

## Preparation
1. Start the backend and frontend using the README commands.
2. Open `http://127.0.0.1:5173` and confirm the dashboard shows the seeded inventory.
3. Use `SA-1002` as the wildcard-scope example. Use `SA-1004` for sensitive data without approval. Use `SA-1006` for the stale agent example.

## Live Walkthrough
1. (0:00–1:00) Overview: show total agents, risk distribution, findings, and recent audit events.
2. (1:00–2:00) Registry: search `SA-1002`, inspect tools/scopes and deterministic risk score.
3. (2:00–3:15) Run review: request `Review SA-1002`; expand actual profile, evaluation, and policy-search tool calls; point to policy source section.
4. (3:15–4:15) Findings: open the wildcard-scope evidence and remediation recommendation.
5. (4:15–6:15) Propose a remediation. Reject one proposal, then create another, approve it, and separately confirm simulated application. Show the audit record and updated synthetic profile.
6. (6:15–7:00) Policy explorer and audit exports: search “human approval” and download the CSV.
7. (7:00–8:00) Reports: show generated evaluation metrics and state that the test data is synthetic and not production validation.

## Offline Backup
No LLM or internet is needed. Start the API and UI with the local requirements already installed; reviews use deterministic fallback and keyword policy retrieval. If the UI server cannot start, use API docs at `http://127.0.0.1:8000/docs` and run `POST /api/reviews` with `{"request":"Review SA-1002"}`. If dependencies are not installed, run the setup commands in README before the presentation.
