---
description: Perform disciplined root-cause analysis for a bug, failure, or regression.
agent: debugger
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Load the `tracker-architecture` and `tracker-testing` skills.

Investigate `$ARGUMENTS`.

Follow this sequence exactly:

1. symptom
2. reproduction conditions
3. observed evidence
4. execution/data flow
5. candidate causes
6. falsifying evidence
7. most likely root cause
8. minimal corrective strategy
9. regression verification

Clearly label:

* Confirmed
* High-confidence hypothesis
* Unverified possibility

Do not jump directly to a fix.

End with a concrete reproduction and verification plan.
