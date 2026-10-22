---
description: Perform a final release-readiness assessment without publishing anything.
agent: reviewer
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Load:

* `release-readiness`
* `tracker-security`
* `tracker-testing`
* `git-hygiene`

Audit the current working tree and `$ARGUMENTS` when provided.

Perform a final release gate covering:

Correctness:

* requirement satisfied
* no unintended behavior
* project invariants preserved

Tests:

* relevant tests
* regression coverage
* understood failures

Security:

* secrets
* unsafe HTML
* SQL
* shell/process use
* dependencies

Data:

* schema compatibility
* migrations
* dedupe
* retention
* concurrency

Operations:

* startup behavior
* scheduler behavior
* refresh behavior
* configuration/documentation

Repository hygiene:

* intended diff only
* generated artifacts
* temporary/debug files
* documentation drift

Never push, deploy, commit, reset, clean, or otherwise mutate the repository.

Classify:
READY
READY WITH EXPLICIT CAVEATS
NOT READY

Every blocker must include exact file:line evidence and remediation.
