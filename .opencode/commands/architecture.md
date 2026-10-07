---
description: Analyze architecture, coupling, boundaries, and safe refactoring strategy.
agent: architect
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Load the `tracker-architecture` skill.

Analyze `$ARGUMENTS` when provided; otherwise analyze the current architecture and current changes.

Evaluate:

* responsibility boundaries
* dependency direction
* coupling
* hidden side effects
* state ownership
* duplicated business logic
* refactoring risk
* architectural drift

For each meaningful recommendation provide:

1. current boundary
2. problem
3. target boundary
4. migration sequence
5. regression risks

Prefer incremental and reversible changes over rewrites.

End with:
ARCHITECTURE VERDICT: SOUND / NEEDS REFACTOR / HIGH RISK
