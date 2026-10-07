---
description: Research an unfamiliar library, API, framework behavior, dependency, or current technical documentation.
agent: researcher
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Load the `tracker-architecture` skill when repository architecture is relevant.

Research `$ARGUMENTS`.

Use primary sources first:

* official documentation
* official changelogs
* release notes
* installed dependency metadata
* repository code

Every external factual claim must have a source URL and version/date where relevant.

Separate:

* Verified
* Inference

End with:

* recommended approach
* relevant API/version
* short implementation sketch when useful
* exact local verification the parent should perform

Never edit files or run shell commands.
