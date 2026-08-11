-- @SRHXtra SQLite Multi-Table Schema (V3.7 with Numeric Epoch Timestamp)

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    country TEXT,
    franchise TEXT NOT NULL,
    role TEXT,
    captain INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team1 TEXT NOT NULL,
    team2 TEXT NOT NULL,
    status TEXT DEFAULT 'Scheduled',
    venue TEXT,
    start_time_ist TEXT NOT NULL,
    tournament TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    summary TEXT,
    link TEXT,
    published_at TEXT,
    pub_timestamp REAL DEFAULT 0.0,
    player_name TEXT,
    franchise TEXT,
    importance_score REAL DEFAULT 5.0,
    category TEXT DEFAULT 'General News'
);

CREATE TABLE IF NOT EXISTS tweets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT DEFAULT 'Draft',
    player_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    template_name TEXT NOT NULL,
    filepath TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'INFO',
    is_read INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Performance Indexes ──────────────────────────────────────────────────────
-- Without these, every news query is a full table scan. Critical at scale.
CREATE INDEX IF NOT EXISTS idx_news_pub_timestamp   ON news (pub_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_news_player_ts       ON news (player_name, pub_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_news_franchise        ON news (franchise);
CREATE INDEX IF NOT EXISTS idx_news_source           ON news (source);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications (created_at DESC);

-- Dedupe per tracked target, not globally per URL/title. One article can mention
-- several squad members and should be stored once for each matched player/team.
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_link_target
    ON news (link, player_name, franchise)
    WHERE link IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_title_target
    ON news (title, player_name, franchise);
