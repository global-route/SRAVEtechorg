ALTER TABLE tax_assessments
    DROP CONSTRAINT IF EXISTS tax_assessments_wa_status_check;

ALTER TABLE tax_assessments
    ADD CONSTRAINT tax_assessments_wa_status_check
    CHECK (wa_status IN ('pending', 'delivered', 'reminder_sent', 'read', 'paid'));
