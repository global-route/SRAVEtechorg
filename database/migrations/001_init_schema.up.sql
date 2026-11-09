CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE lg_boundaries (
    id    SERIAL PRIMARY KEY,
    name  TEXT NOT NULL,
    state TEXT NOT NULL,
    geom  GEOMETRY(MULTIPOLYGON, 4326)
);

CREATE INDEX idx_lg_boundaries_geom ON lg_boundaries USING GIST (geom);

CREATE TABLE detected_buildings (
    id               SERIAL PRIMARY KEY,
    lga_id           TEXT NOT NULL,
    footprint        GEOMETRY(POLYGON, 4326),
    confidence_score FLOAT,
    verified         BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_detected_buildings_lga ON detected_buildings (lga_id);
CREATE INDEX idx_detected_buildings_geom ON detected_buildings USING GIST (footprint);
