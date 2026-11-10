ALTER TABLE tax_roll ADD COLUMN IF NOT EXISTS owner_language TEXT;

CREATE TABLE IF NOT EXISTS sync_conflicts (
    id              BIGSERIAL PRIMARY KEY,
    building_id     INT REFERENCES detected_buildings(id),
    local_payload   JSONB,
    server_response JSONB,
    resolved        BOOLEAN DEFAULT FALSE,
    logged_at       TIMESTAMPTZ DEFAULT NOW()
);
