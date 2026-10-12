CREATE EXTENSION IF NOT EXISTS pgcrypto;
DO $$ BEGIN CREATE TYPE user_role AS ENUM ('student','faculty','welfare','director','events'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE proposal_status AS ENUM ('draft','faculty_review','welfare_review','director_review','events_review','meeting_requested','approved','rejected','cancelled'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN CREATE TYPE decision_type AS ENUM ('approved','rejected','meeting_requested','meeting_resolved'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS users (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
 role user_role NOT NULL, department TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS halls (
 id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL, capacity INTEGER NOT NULL CHECK(capacity > 0), location TEXT, active BOOLEAN NOT NULL DEFAULT true
);
CREATE TABLE IF NOT EXISTS proposals (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), request_token TEXT UNIQUE NOT NULL, student_id UUID NOT NULL REFERENCES users(id), faculty_id UUID REFERENCES users(id),
 event_name TEXT NOT NULL, department TEXT NOT NULL, description TEXT, starts_at TIMESTAMPTZ NOT NULL, ends_at TIMESTAMPTZ NOT NULL CHECK(ends_at > starts_at),
 participant_count INTEGER NOT NULL CHECK(participant_count > 0), national_count INTEGER DEFAULT 0, international_count INTEGER DEFAULT 0, male_count INTEGER DEFAULT 0, female_count INTEGER DEFAULT 0,
 hall_id INTEGER REFERENCES halls(id), infrastructure JSONB NOT NULL DEFAULT '[]', catering JSONB NOT NULL DEFAULT '[]', vehicles JSONB NOT NULL DEFAULT '[]', accommodation JSONB NOT NULL DEFAULT '[]',
 arrangements JSONB NOT NULL DEFAULT '{}', funding_source TEXT, additional_requirements TEXT, discipline_faculty TEXT, organizer_details JSONB NOT NULL DEFAULT '{}',
 status proposal_status NOT NULL DEFAULT 'draft', current_stage user_role, submitted_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS proposal_documents (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), proposal_id UUID NOT NULL REFERENCES proposals(id) ON DELETE CASCADE, uploaded_by UUID NOT NULL REFERENCES users(id),
 kind TEXT NOT NULL, original_name TEXT NOT NULL, stored_name TEXT NOT NULL, mime_type TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS approval_history (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), proposal_id UUID NOT NULL REFERENCES proposals(id) ON DELETE CASCADE, actor_id UUID REFERENCES users(id), stage user_role NOT NULL,
 decision decision_type NOT NULL, note TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS meetings (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), proposal_id UUID NOT NULL REFERENCES proposals(id) ON DELETE CASCADE, requested_by UUID NOT NULL REFERENCES users(id), stage user_role NOT NULL,
 note TEXT NOT NULL, scheduled_at TIMESTAMPTZ, outcome TEXT, resolved_at TIMESTAMPTZ
 ,created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hall_bookings (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), proposal_id UUID UNIQUE NOT NULL REFERENCES proposals(id), hall_id INTEGER NOT NULL REFERENCES halls(id), starts_at TIMESTAMPTZ NOT NULL, ends_at TIMESTAMPTZ NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('confirmed','cancelled')) DEFAULT 'confirmed', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hall_holds (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), proposal_id UUID UNIQUE NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
 hall_id INTEGER NOT NULL REFERENCES halls(id), starts_at TIMESTAMPTZ NOT NULL, ends_at TIMESTAMPTZ NOT NULL,
 expires_at TIMESTAMPTZ NOT NULL, released_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS holds_window ON hall_holds(hall_id, starts_at, ends_at) WHERE released_at IS NULL;
CREATE TABLE IF NOT EXISTS registrations (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), proposal_id UUID NOT NULL REFERENCES proposals(id), student_id UUID NOT NULL REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(proposal_id,student_id)
);
CREATE TABLE IF NOT EXISTS registration_events (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), faculty_id UUID NOT NULL REFERENCES users(id), hall_id INTEGER REFERENCES halls(id),
 name TEXT NOT NULL, description TEXT, starts_at TIMESTAMPTZ NOT NULL, registration_deadline TIMESTAMPTZ,
 capacity INTEGER NOT NULL CHECK(capacity > 0), poster_stored_name TEXT, poster_original_name TEXT, published BOOLEAN NOT NULL DEFAULT true, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS registration_queue (
 ticket_id BIGSERIAL PRIMARY KEY, booking_id UUID NOT NULL UNIQUE, event_id UUID NOT NULL REFERENCES registration_events(id) ON DELETE CASCADE,
 student_id UUID NOT NULL REFERENCES users(id), roll_number TEXT NOT NULL, participant_name TEXT NOT NULL, department TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting','processing','granted','failed')), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS event_ticket_allocations (
 event_id UUID NOT NULL REFERENCES registration_events(id) ON DELETE CASCADE, student_id UUID NOT NULL REFERENCES users(id),
 roll_number TEXT NOT NULL, participant_name TEXT NOT NULL, department TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'held' CHECK(status IN ('held','confirmed')),
 booking_id UUID NOT NULL UNIQUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ, PRIMARY KEY(event_id, student_id), UNIQUE(event_id, roll_number)
);
CREATE TABLE IF NOT EXISTS classrooms (
 id SERIAL PRIMARY KEY, room_name TEXT UNIQUE NOT NULL, sub_block TEXT NOT NULL, floor INTEGER NOT NULL, room_number_on_floor INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS classroom_timetable (
 day_of_week TEXT NOT NULL CHECK(day_of_week IN ('Monday','Tuesday','Wednesday','Thursday','Friday')), classroom_id INTEGER NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
 slot_index INTEGER NOT NULL CHECK(slot_index BETWEEN 1 AND 11), baseline_occupied BOOLEAN NOT NULL, PRIMARY KEY(day_of_week,classroom_id,slot_index)
);
CREATE TABLE IF NOT EXISTS classroom_requests (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), student_id UUID NOT NULL REFERENCES users(id), faculty_id UUID NOT NULL REFERENCES users(id), classroom_id INTEGER NOT NULL REFERENCES classrooms(id),
 booking_date DATE NOT NULL, slot_indices INTEGER[] NOT NULL, purpose TEXT NOT NULL, contact TEXT, status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','cancelled')),
 faculty_note TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), decided_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS classroom_booking_slots (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), request_id UUID NOT NULL REFERENCES classroom_requests(id) ON DELETE CASCADE, classroom_id INTEGER NOT NULL REFERENCES classrooms(id),
 booking_date DATE NOT NULL, slot_index INTEGER NOT NULL CHECK(slot_index BETWEEN 1 AND 11), status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed','cancelled')), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS confirmed_classroom_slot ON classroom_booking_slots(classroom_id,booking_date,slot_index) WHERE status='confirmed';
CREATE INDEX IF NOT EXISTS bookings_window ON hall_bookings(hall_id, starts_at, ends_at) WHERE status='confirmed';
