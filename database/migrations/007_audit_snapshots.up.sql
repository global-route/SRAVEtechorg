CREATE TABLE IF NOT EXISTS audit_snapshots (
    id                BIGSERIAL PRIMARY KEY,
    lga_id            TEXT NOT NULL,
    snapshot_date     DATE NOT NULL,
    ledger_entry_hash TEXT NOT NULL,
    previous_hash     TEXT NOT NULL,
    payload_json      JSONB NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (lga_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_audit_snapshots_lga
    ON audit_snapshots (lga_id, snapshot_date DESC);
