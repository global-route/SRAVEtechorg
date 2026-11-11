CREATE TABLE IF NOT EXISTS clients (
    id           TEXT PRIMARY KEY,
    secret_hash  TEXT NOT NULL,
    scope        TEXT NOT NULL CHECK (scope IN ('municipal', 'field_agent', 'multilateral', 'admin')),
    lga_id       TEXT,
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clients_active ON clients (id) WHERE active = TRUE;
