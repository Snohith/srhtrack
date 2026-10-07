---
name: Tracker Security
description: Security invariants and threat-model guidance for RSS content, Streamlit HTML, SQL, secrets, files, subprocesses, and dependencies in Tracker.
---

Treat RSS content, web-scraped content, user input, and spreadsheet data as untrusted or semi-trusted. Trace external data from ingestion through persistence to presentation before judging any sink safe.

## Rules

- Every `unsafe_allow_html` path requires deliberate escaping and attribute safety. Verify `html.escape` coverage on titles, summaries, names, links, source names, and query-derived content.
- Article URLs must allow only intended schemes such as `http` and `https`; never permit executable schemes (`javascript:`, `data:`, `vbscript:`). Validate before rendering, ideally at a single choke point.
- Validate and escape values inserted into HTML attributes (`href`, `src`); quote-escaping alone does not block scheme or attribute-breakout attacks.
- Prefer parameterized SQL; no string-built SQL from user or external data. Check LIKE/search behavior for user-controlled wildcards where relevant.
- Treat `.env`, Streamlit secrets, environment variables, git remotes, and logs as secret-bearing surfaces. Never print or reproduce credential values — refer to secrets by location only.
- Inspect subprocess and shell construction, dynamic evaluation (`eval`/`exec`), unsafe imports, filesystem paths (traversal, symlink, destructive operations), and anything that deletes or overwrites data.
- Assess dependency changes for unnecessary packages, suspicious install behavior, and version risk.
- Treat OpenCode permissions and new automation (agents, skills, MCP servers, policies) as part of the security boundary; flag anything that widens access.
- Distinguish confirmed vulnerabilities (reachable path, cited code) from theoretical concerns.
- Never create weaponized payloads or exfiltration instructions; describe flaws with the minimum detail needed to identify and fix them.
