---
description: Review current changes for correctness, regressions, maintainability, and missing tests.
agent: reviewer
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Load the `tracker-architecture` and `tracker-testing` skills before reviewing.

Review the current working-tree changes, or the stated topic in `$ARGUMENTS` when provided.

Follow the `reviewer` agent policy.

Prioritize:

* blockers
* correctness defects
* invariant violations
* regressions
* security-impacting mistakes
* missing tests
* maintainability concerns
* minor nits last

Use precise `file:line` references.

Run the relevant test suite when behavior is affected.

Never modify, commit, push, or deploy.

End with:
VERDICT: PASS / PASS WITH CONCERNS / NEEDS CHANGES
