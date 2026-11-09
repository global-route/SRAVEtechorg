CREATE TABLE tax_assessments (
    id           SERIAL PRIMARY KEY,
    building_id  INT NOT NULL REFERENCES detected_buildings (id),
    owner_phone  TEXT,
    amount_due   NUMERIC(15, 2),
    wa_status    TEXT DEFAULT 'pending', -- pending | delivered | paid
    payment_ref  TEXT,
    assessed_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_id   TEXT,
    payload     JSONB,
    logged_at   TIMESTAMPTZ DEFAULT NOW()
);
