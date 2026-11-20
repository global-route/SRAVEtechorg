ALTER TABLE tax_assessments
  ADD COLUMN IF NOT EXISTS amount_paid  NUMERIC(15,2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS payment_date TIMESTAMPTZ;

-- Drop and recreate wa_status constraint to include partially_paid and escalated
ALTER TABLE tax_assessments DROP CONSTRAINT IF EXISTS tax_assessments_wa_status_check;
ALTER TABLE tax_assessments ADD CONSTRAINT tax_assessments_wa_status_check
  CHECK (wa_status IN ('pending','delivered','reminder_sent','partially_paid','paid','escalated'));

-- Index for payment reminder scheduler and reconciliation queries (fixes gap D-04)
CREATE INDEX IF NOT EXISTS idx_assessments_wa_status
  ON tax_assessments (wa_status, assessed_at);
