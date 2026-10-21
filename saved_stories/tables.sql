-- SRHXtra Telegram delivery ledger.
-- articles: one row per unique relevant story.
-- deliveries: one row per article; the only source of truth for what was sent.

CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key   TEXT NOT NULL UNIQUE,
    title_key    TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL,
    source       TEXT NOT NULL,
    summary      TEXT,
    link         TEXT NOT NULL,
    published_at TEXT,
    published_ts REAL NOT NULL DEFAULT 0.0,
    people       TEXT NOT NULL DEFAULT '[]',
    franchises   TEXT NOT NULL DEFAULT '[]',
    topics       TEXT NOT NULL DEFAULT '[]',
    first_seen_ts REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_articles_published
    ON articles (published_ts DESC, id DESC);

CREATE TABLE IF NOT EXISTS deliveries (
    article_id      INTEGER PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sending', 'sent', 'failed')),
    attempts        INTEGER NOT NULL DEFAULT 0,
    next_attempt_ts REAL NOT NULL DEFAULT 0.0,
    claimed_at      REAL,
    sent_at         REAL,
    last_error      TEXT,
    updated_at      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deliveries_due
    ON deliveries (status, next_attempt_ts);

-- Per-feed failure backoff, so a dead source is not hit every five minutes.
CREATE TABLE IF NOT EXISTS feed_health (
    feed_url       TEXT PRIMARY KEY,
    feed_name      TEXT NOT NULL,
    failures       INTEGER NOT NULL DEFAULT 0,
    next_attempt_ts REAL NOT NULL DEFAULT 0.0,
    last_error     TEXT,
    updated_at     REAL NOT NULL
);

-- One-time migration from the old dashboard's alerted_stories table.  It keeps
-- recently sent titles quiet while the old table is dropped.
CREATE TABLE IF NOT EXISTS suppressed_titles (
    title_key  TEXT PRIMARY KEY,
    expires_ts REAL NOT NULL
);

-- Persistent activation time.  The first collection skips older stories so a
-- fresh deployment does not replay the last 24 hours as a burst of alerts.
CREATE TABLE IF NOT EXISTS service_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

PRAGMA user_version = 2;
