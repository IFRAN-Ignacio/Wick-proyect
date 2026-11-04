-- Esquema inicial (simplificado de 03_ARQUITECTURA §7 para el MVP).
CREATE TABLE strategy (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config_json TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE backtest (
    id TEXT PRIMARY KEY,
    strategy_id TEXT REFERENCES strategy(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    config_snapshot_json TEXT NOT NULL,
    engine_version TEXT NOT NULL,
    data_fingerprint TEXT,
    data_info_json TEXT,
    n_variants INTEGER NOT NULL,
    n_discarded INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    error TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    duration_s REAL
);

CREATE TABLE variant (
    id TEXT PRIMARY KEY,
    backtest_id TEXT NOT NULL REFERENCES backtest(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    params_json TEXT NOT NULL,
    config_json TEXT NOT NULL,
    total_return REAL,
    max_dd REAL,
    sharpe REAL,
    profit_factor REAL,
    win_rate REAL,
    n_trades INTEGER,
    n_ambiguous INTEGER,
    metrics_json TEXT NOT NULL
);
CREATE INDEX variant_backtest ON variant(backtest_id);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
