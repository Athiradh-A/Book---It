-- Book-It workflow roles. Safe to rerun; does not modify users, passwords, or event history.
BEGIN;
INSERT INTO roles (name) VALUES ('STUDENT'), ('FACULTY'), ('WELFARE'), ('DIRECTOR'), ('EVENTS'), ('ADMIN')
ON CONFLICT (name) DO NOTHING;
COMMIT;
