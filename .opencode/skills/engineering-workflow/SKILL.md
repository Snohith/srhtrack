---
name: Engineering Workflow
description: Disciplined phased engineering workflow for Tracker work: understand, research, architect, implement, verify, review, and release-gate.
---

Follow this decision framework for Tracker implementation work. It is a framework, not mandatory ceremony: invoke specialists only when the decision table says so. Optimize for correctness and signal, not maximum agent usage.

Use the specialist command/agent in the current session when needed. Do not require background child sessions. With the current OpenCode Zen free-tier model, prefer sequential same-session specialist execution for reliability.

## Phase 0 — Understand

Before editing:

- Read `AGENTS.md`.
- Inspect git status and the relevant diff.
- Identify the exact user requirement.
- Identify affected modules.
- Identify invariants that could be affected.
- Do not make speculative changes.

## Phase 1 — Research, only when needed

Run `/research` when an API or library behavior is unfamiliar, a dependency or version question exists, current external documentation matters, or framework behavior may have changed. Use primary sources first. Do NOT run `/research` merely to produce ceremony for a straightforward local change.

## Phase 2 — Architecture, conditionally

Use `/architecture` when multiple modules are affected, responsibilities are moving, a refactor is involved, database/application boundaries change, new abstractions are introduced, or the existing architecture appears insufficient. For small isolated bug fixes, skip unnecessary architecture work.

## Phase 3 — Implement

Build performs the actual implementation:

- Make the smallest correct change.
- Preserve existing invariants.
- Do not rewrite unrelated code.
- Do not silently change product behavior outside the requirement.
- Keep changes reversible.
- Explain assumptions when ambiguity exists.

## Phase 4 — Verify

After implementation: run the narrowest relevant tests first, then the broader test suite when practical. Inspect failures rather than suppressing them. Inspect the final diff. If tests cannot be run, explicitly state why.

## Phase 5 — Specialist review

Only after implementation is complete and the working tree is stable, run relevant read-only specialist commands. Do not run specialist audits while Build is still modifying the working tree. The user remains in control of the sequence: run one specialist command at a time, review its output, then proceed.

Always consider `/review` and `/security-audit`. Conditionally run `/db-audit` for DB/schema/concurrency/retention changes, `/test` for meaningful behavior or test changes, `/architecture` for substantial structural changes, and `/debug` for defect investigations.

## Phase 6 — Final release gate

Run `/release-check` for meaningful feature/refactor work or changes crossing important boundaries. Do not require `/release-check` for tiny typo or documentation-only changes unless the user requests it.

## Decision table

- Research: unfamiliar or current external behavior → YES; ordinary local code → NO.
- Architecture: cross-module, refactor, or design change → YES; isolated bug fix → usually NO.
- Security: always for externally supplied data, HTML, URLs, auth/secrets, shell, SQL, filesystem, dependencies; otherwise use judgment.
- Data engineer: any schema, query, transaction, concurrency, retention, or DB-initialization change → YES; otherwise NO.
- Test engineer: behavior change or insufficient existing coverage → YES.
- Reviewer: meaningful implementation → YES.
- Release check: feature, refactor, security, data, or operational change → YES.
