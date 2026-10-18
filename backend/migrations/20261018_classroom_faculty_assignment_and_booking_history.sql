-- Adds explicit classroom approver assignment and links hall bookings to their source proposal.
-- Apply once after backing up the database; nullable columns preserve existing records.
BEGIN;
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS assigned_faculty_id INTEGER NULL REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_bookings_assigned_faculty_id ON bookings(assigned_faculty_id);
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_request_id INTEGER NULL REFERENCES event_requests(id);
CREATE INDEX IF NOT EXISTS ix_bookings_event_request_id ON bookings(event_request_id);
COMMIT;
