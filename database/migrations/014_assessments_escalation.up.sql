ALTER TABLE tax_assessments
  ADD COLUMN IF NOT EXISTS escalated    BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_assessments_escalated
  ON tax_assessments (escalated, assessed_at) WHERE escalated = TRUE;
