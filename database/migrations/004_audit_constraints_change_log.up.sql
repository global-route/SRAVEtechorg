-- Immutability trigger on audit_snapshots
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_snapshots is immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_snapshots_immutable
BEFORE UPDATE OR DELETE ON audit_snapshots
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

REVOKE UPDATE, DELETE ON audit_snapshots FROM srave_user;

-- Change detection log
CREATE TABLE change_detection_log (
    id               SERIAL PRIMARY KEY,
    building_id      INT REFERENCES detected_buildings(id),
    change_type      TEXT NOT NULL CHECK (change_type IN ('new', 'modified', 'demolished')),
    from_scan_date   DATE,
    to_scan_date     DATE,
    flagged_for_review BOOLEAN DEFAULT TRUE,
    detected_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_change_log_lga ON change_detection_log (building_id);

-- scan_date index on detected_buildings
CREATE INDEX IF NOT EXISTS idx_detected_buildings_scan_date
    ON detected_buildings (lga_id, scan_date);

-- owner_language column on tax_roll (idempotent)
ALTER TABLE tax_roll ADD COLUMN IF NOT EXISTS owner_language TEXT;
