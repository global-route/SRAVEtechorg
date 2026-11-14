ALTER TABLE detected_buildings
    ADD COLUMN IF NOT EXISTS property_type TEXT NOT NULL DEFAULT 'residential_low',
    ADD COLUMN IF NOT EXISTS scan_date     DATE;

CREATE INDEX IF NOT EXISTS idx_detected_buildings_property
    ON detected_buildings (lga_id, property_type);

CREATE INDEX IF NOT EXISTS idx_detected_buildings_scan_date
    ON detected_buildings (lga_id, scan_date);
