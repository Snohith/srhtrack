---
name: Tracker Streamlit
description: Streamlit UI architecture, rendering safety, caching, refresh behavior, and user-input rules for Tracker.
---

`app.py` is the Streamlit orchestration/UI layer. Avoid turning it into a second business-logic layer: matching, retention, and dedupe decisions belong in their owning modules.

## Rules

- Review startup side effects and cold-start ingest carefully (`init_db`, purge, empty-table ingest, background thread spawn).
- Treat background refresh, manual refresh, caching (`st.cache_data` TTLs), and session state as interacting state machines; reason about their combined behavior, not each in isolation.
- Review cache invalidation whenever underlying database state changes (ingest, purge, manual refresh must clear or bypass stale caches).
- Ensure user search inputs are handled safely and deterministically; never interpolate raw query text into HTML.
- Audit every use of `unsafe_allow_html=True`. Preserve escaping for titles, summaries, names, links, source names, and query-derived content.
- Verify URL handling (scheme allowlist, attribute escaping) before HTML rendering.
- Avoid blocking or long-running work on the UI thread where possible; prefer background threads or explicit user-triggered actions.
- Preserve tab behavior and existing user-facing semantics when refactoring.
- Consider concurrent database access from Streamlit refresh paths (background thread vs manual refresh vs purge).
- Avoid adding hidden global state merely to work around Streamlit reruns.
- Any UI change that affects data or refresh behavior should include regression tests where feasible.
