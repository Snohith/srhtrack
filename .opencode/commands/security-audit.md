---
description: Audit current changes and relevant code paths for security vulnerabilities and unsafe trust boundaries.
agent: security
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Load the `tracker-security` skill.

Audit `$ARGUMENTS` when provided; otherwise audit the current changes and the security-sensitive execution paths they touch.

Trace untrusted data through ingestion, database storage, rendering, user input, URLs, shell/process boundaries, and secrets.

Report:

* severity
* finding
* exploit/exposure mechanism
* precise file:line evidence
* remediation

Never include real secret values or weaponized exploit payloads.

End with:
SECURITY VERDICT: CLEAR / CONCERNS / HIGH RISK
