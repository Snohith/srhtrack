---
name: Git Hygiene
description: Safe repository-state, credential, diff, commit, and branch-management practices for professional Tracker development.
---

## Rules

- Never expose secrets, tokens, credential-bearing remotes, cookies, or environment values in output. Redact by location, never reproduce values.
- Treat a git remote containing credentials as a security incident; recommend rotation and removal without reproducing the secret.
- Check working-tree state (`status`, `diff`) before proposing commits; review the actual diff, not assumptions based on filenames.
- Keep unrelated changes separated; do not bundle independent work into one commit.
- Never casually delete untracked files or reset/rebase without explicit authorization.
- Treat force-push, history rewriting, branch deletion, `git clean`, and destructive resets as high-risk operations requiring explicit approval.
- Generated artifacts (bytecode, caches, logs, databases, images) should follow the repository's documented tracking/ignore policy; do not commit ignored artifacts or stage unintended generated files.
- Before commit readiness, inspect: status, diff, unintended generated files, secrets, test results, and documentation drift.
- Never claim a commit or push happened unless verified via command output.
- Never include secrets in commit messages.
- Preserve user-owned changes when cleaning up a worktree.
- Treat remote deployment connections (e.g. Streamlit Cloud linked to the repository) as a reason for extra caution around push operations: pushing can deploy.
