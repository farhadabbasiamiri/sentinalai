# SentinelAI Local Governance Policies

These project policies are decision-support rules for synthetic records, not a legal or industry certification.

## Least Privilege
Grant each agent only the tools, permissions, API scopes, and data categories needed for its declared purpose. Wildcards and organization-wide scopes require removal or a documented exception. Reference: GOV-001, GOV-002.

## Separation of Duties
An agent that initiates a sensitive workflow must not approve the same workflow. Separate duties across principals and preserve reviewer attribution. Reference: GOV-004, GOV-009.

## Sensitive Data Access
High and restricted sensitivity data require a named owner, a narrowly scoped purpose, and an explicit human approval gate for sensitive operations. Reference: GOV-003, GOV-008.

## Human Approval
Email delivery, payment, deployment, identity administration, and other high-impact actions require a human decision before execution. SentinelAI only simulates proposed governance changes; it never changes external accounts or services. Reference: GOV-008, GOV-010.

## Ownership and Lifecycle
Every agent must have an accountable owner. Review agents inactive for more than 90 days; remove retained permissions or deactivate them when no longer required. The 90-day value is a project-specific evaluation threshold, not an industry standard. Reference: GOV-005, GOV-006.

## Tool Combinations
Avoid combinations that enable unreviewed data transfer or conflicting duties, including file access plus unrestricted external access, outbound messaging plus unrestricted external access, and payment plus vendor administration. Reference: GOV-004, GOV-009.

## Audit Logging and Accountability
Record review requests, bounded tool invocations, policy matches, approval decisions, and simulated applications. Exclude secrets and avoid copying unnecessary free text into logs. Reference: GOV-010.
