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
