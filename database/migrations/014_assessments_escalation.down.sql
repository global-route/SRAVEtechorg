DROP INDEX IF EXISTS idx_assessments_escalated;
ALTER TABLE tax_assessments
  DROP COLUMN IF EXISTS escalated,
  DROP COLUMN IF EXISTS escalated_at;
