ALTER TABLE tax_assessments
  DROP COLUMN IF EXISTS amount_paid,
  DROP COLUMN IF EXISTS payment_date;

DROP INDEX IF EXISTS idx_assessments_wa_status;

ALTER TABLE tax_assessments DROP CONSTRAINT IF EXISTS tax_assessments_wa_status_check;
ALTER TABLE tax_assessments ADD CONSTRAINT tax_assessments_wa_status_check
  CHECK (wa_status IN ('pending','delivered','reminder_sent','paid','escalated'));
