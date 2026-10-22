---
description: Analyze test coverage, regression risk, and testing strategy for the current change or feature.
agent: test-engineer
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Load the `tracker-testing` skill.

Analyze `$ARGUMENTS` when provided; otherwise analyze the current working-tree changes.

Do not focus on line coverage alone.

Identify:

* required regression tests
* missing boundary cases
* negative cases
* isolation problems
* brittle tests
* network/time/shared-state dependencies
* tests that should fail before the fix
* highest-value additions first

Because this specialist is read-only, provide test designs rather than editing test files.

End with a prioritized test plan.
