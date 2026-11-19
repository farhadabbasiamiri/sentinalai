# Security and Safety Boundaries

- All shipped records are synthetic; never point the demo at production agents or credentials.
- Pydantic validates IDs, enums, bounded text, list sizes, and proposal types. Unknown agent IDs return safe 404 responses.
- Agent descriptions, activity events, and retrieved policy passages are evidence, never instructions. Optional local Ollama prompting explicitly marks them untrusted.
- The AI workflow invokes only fixed profile, deterministic evaluation, and local policy-search tools. There is no arbitrary shell or filesystem tool, remote scanning, malware execution, or production integration.
- Deterministic rules own finding creation and score calculation. Narrative generation cannot alter rules, findings, or scores.
- Simulated changes are constrained to a small allowlist of local field mutations. They require a reviewer decision and a separate explicit confirmation; pending/rejected proposals cannot be applied.
- Audit records capture tool calls, reviews, policy matches, approvals, and simulated application without storing secrets.
- The local API has no authentication and is intended for a trusted development machine only. Do not expose it to an untrusted network.
- Risk scores are decision-support indicators, not proof of compromise, certification, or an industry standard.
<<<<<<< HEAD
=======
- Dependencies are scanned on every CI run (`pip-audit`, `npm audit`), Python code with Bandit, and the API image with Trivy. The core API requirements have no known vulnerabilities; the optional Gradio dashboard carries an accepted, documented Pillow risk while Gradio caps Pillow below 13.
- Containers run as unprivileged users (API uid 10001, frontend `node`), the build context excludes local secrets and databases via `.dockerignore`, and Dependabot proposes dependency and base-image updates.
- Optional Ollama output may only replace narrative text (summary, recommendations). Scores and findings always come from the rule engine, and malformed or partial model replies fall back to the deterministic report. See `docs/testing.md` for the full review and test coverage.
>>>>>>> 4f3f30c (feat:Phase 6 -Testing, Security and DevOps)
