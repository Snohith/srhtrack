---
name: Release Readiness
description: Final pre-merge and pre-deployment verification checklist for Tracker changes.
---

Apply this release gate to the change under review. Release readiness is an assessment, not authorization to publish: do not automatically push or deploy.

### Correctness

- Implementation matches the stated requirement.
- No unrelated behavior changes.
- Documented invariants preserved (`AGENTS.md` contract: dedupe, defaults, aliases, retention, scheduler isolation, roster source of truth).
- Edge cases reviewed.

### Tests

- Relevant tests executed with results reported.
- New behavior has regression coverage.
- Failures are understood rather than ignored.

### Security

- No secrets added; no credential-bearing URLs.
- No unsafe HTML/SQL/shell regressions (escaping, scheme validation, parameterization intact).
- Dependencies reviewed (no unnecessary packages, no suspicious install behavior).

### Data

- Schema compatibility considered; migrations safe and compatibility-sensitive.
- Retention, dedupe, and concurrency semantics preserved.

### Operations

- Startup behavior considered (side effects, cold-start cost).
- Scheduler behavior verified (one-shot cycle, no redundant initialization).
- Background/manual refresh interaction considered.
- Environment configuration documented (new variables in `.env.example`, defaults sane).

### Repository hygiene

- Diff contains only intended changes.
- Ignored/generated artifacts handled correctly.
- Docs are not stale relative to the change.
- No debug prints or temporary files.

### Final decision

Classify the result as exactly one of:

- READY
- READY WITH EXPLICIT CAVEATS
- NOT READY

Every blocker must include exact file/line evidence and the required remediation. Caveats must state what was not verified and why it is acceptable to proceed.
