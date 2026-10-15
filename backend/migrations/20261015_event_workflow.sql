-- Run once against the same PostgreSQL database used by the FastAPI backend.
-- PostgreSQL commits a newly added enum value separately from statements that use it.
ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'PENDING_EVENTS_APPROVAL';

ALTER TABLE bookings ADD COLUMN IF NOT EXISTS decision_comment TEXT;
