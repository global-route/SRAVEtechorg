CREATE TABLE IF NOT EXISTS failed_jobs (
    id          BIGSERIAL PRIMARY KEY,
    task_name   TEXT NOT NULL,
    job_id      TEXT NOT NULL,
    lga_id      TEXT,
    error       TEXT,
    payload     JSONB,
    retries     INT NOT NULL DEFAULT 0,
    replayed    BOOLEAN NOT NULL DEFAULT FALSE,
    failed_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_failed_jobs_lga      ON failed_jobs (lga_id);
CREATE INDEX IF NOT EXISTS idx_failed_jobs_replayed ON failed_jobs (replayed) WHERE replayed = FALSE;
