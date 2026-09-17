CREATE TABLE IF NOT EXISTS steam_games (
    steam_id            INTEGER PRIMARY KEY,
    name                TEXT    NOT NULL,
    copies_sold         INTEGER,
    price               REAL,
    review_score        INTEGER,
    publisher_class     TEXT,
    unreleased          INTEGER,  -- boolean stored as 0/1
    early_access        INTEGER,  -- boolean stored as 0/1
    release_date        INTEGER,  -- unix timestamp (ms)
    first_release_date  INTEGER,  -- unix timestamp (ms)
    ea_release_date     INTEGER,  -- unix timestamp (ms), earlyAccessExitDate
    -- Array fields stored as JSON-encoded text, e.g. '["Action","RPG"]'
    -- Filter with: WHERE genres LIKE '%Action%'
    genres              TEXT,
    developers          TEXT,
    publishers          TEXT,
    -- Ingestion metadata
    ingested_at         INTEGER NOT NULL DEFAULT (strftime('%s', 'now') * 1000)
);

-- Index to speed up common query patterns
CREATE INDEX IF NOT EXISTS idx_steam_games_copies_sold   ON steam_games (copies_sold DESC);
CREATE INDEX IF NOT EXISTS idx_steam_games_review_score  ON steam_games (review_score DESC);
CREATE INDEX IF NOT EXISTS idx_steam_games_price         ON steam_games (price);
CREATE INDEX IF NOT EXISTS idx_steam_games_publisher_cls ON steam_games (publisher_class);
CREATE INDEX IF NOT EXISTS idx_steam_games_release_date  ON steam_games (release_date DESC);
