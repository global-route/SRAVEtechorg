ALTER TABLE detected_buildings
    DROP COLUMN IF EXISTS property_type,
    DROP COLUMN IF EXISTS scan_date;
