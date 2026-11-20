CREATE TABLE IF NOT EXISTS lga_settings (
    lga_id              TEXT PRIMARY KEY REFERENCES lg_boundaries(name),
    confidence_threshold FLOAT NOT NULL DEFAULT 0.5,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
