CREATE TABLE tax_roll (
    id            SERIAL PRIMARY KEY,
    lga_id        TEXT NOT NULL,
    owner_name    TEXT,
    owner_phone   TEXT,
    owner_language TEXT,
    address       TEXT,
    geom          GEOMETRY(POINT, 4326),
    registered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_roll_lga   ON tax_roll (lga_id);
CREATE INDEX idx_tax_roll_geom  ON tax_roll USING GIST (geom);
CREATE INDEX idx_tax_roll_phone ON tax_roll (owner_phone);

CREATE TABLE tax_rates (
    lga_id          TEXT NOT NULL,
    property_type   TEXT NOT NULL,
    annual_rate_ngn NUMERIC(15, 2) NOT NULL DEFAULT 30000,
    PRIMARY KEY (lga_id, property_type)
);

-- Default rates applied to all LGAs via trigger on new LGA insert
INSERT INTO tax_rates (lga_id, property_type, annual_rate_ngn)
SELECT name, pt.property_type, pt.rate
FROM lg_boundaries,
     (VALUES
         ('residential_low',  30000),
         ('residential_high', 80000),
         ('commercial',      200000),
         ('industrial',      500000)
     ) AS pt(property_type, rate)
ON CONFLICT DO NOTHING;
