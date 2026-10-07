---
description: Execute a disciplined professional implementation workflow for a Tracker feature, bug fix, or refactor.
agent: build
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Act as the lead implementation agent and follow the `engineering-workflow` skill for this task: `$ARGUMENTS`.

1. Parse the user's request from `$ARGUMENTS`.
2. Read `AGENTS.md`.
3. Inspect the repository and current git state.
4. Classify the task as feature, bug fix, refactor, or maintenance.
5. Determine which specialists are actually necessary — do NOT invoke every specialist mechanically.
6. Before coding: use `researcher` if current or external knowledge is required; use `architect` if the architecture warrants it.
7. Summarize the implementation plan internally, then implement.
8. Run relevant tests.
9. After implementation is stable: use `security` when security-sensitive surfaces are involved; use `test-engineer` when test strategy or coverage is important; use `data-engineer` for DB-related work; use `reviewer` for meaningful code changes.
10. Fix confirmed issues found by those reviews. If a specialist reports a finding, verify it against the actual code before changing anything. Distinguish confirmed defects from suggestions.
11. Re-run relevant tests after fixes.
12. Run `release-check` for meaningful changes.
13. Inspect the final diff and working-tree state.

Orchestration rules:

- Build owns implementation. Specialist agents are advisors and reviewers; do NOT ask multiple agents to modify the repository, and do NOT let read-only specialists edit files.
- Do NOT ask specialists to commit or push. Do NOT push or deploy automatically.
- Preserve the parent user's requested scope. If the task reveals a requirement ambiguity, make the safest reasonable assumption and state it rather than expanding scope.
- Use the configured subagent tool and agent mechanism. Do not use shell interpolation (`!` blocks) in this workflow.
- Never claim a test, review, or release check happened unless it actually ran.

Final response must contain:

### Result

What changed.

### Verification

Tests actually run and their results.

### Specialist findings

Only material findings from agents that were actually consulted.

### Remaining concerns

Anything unresolved.

### Git state

Whether files are modified, untracked, or staged. Never claim the work is committed, pushed, deployed, or production-ready unless that action was actually performed and verified.
