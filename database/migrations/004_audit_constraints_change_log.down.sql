DROP TRIGGER IF EXISTS audit_snapshots_immutable ON audit_snapshots;
DROP FUNCTION IF EXISTS prevent_audit_modification;
DROP TABLE IF EXISTS change_detection_log;
