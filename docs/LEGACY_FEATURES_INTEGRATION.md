# Book-It legacy workflow integration

This branch integrates legacy workflow concepts into the React + FastAPI application. It does not run the legacy Express app as a second source of truth.

## Roles and local demo accounts

The role seeder creates or links these local-development users and roles:

| Username | Email | Role |
|---|---|---|
| student | student@campusroom.edu | STUDENT |
| faculty | faculty@campusroom.edu | FACULTY |
| welfare | welfare@campusroom.edu | WELFARE |
| director | director@campusroom.edu | DIRECTOR |
| events | events@campusroom.edu | EVENTS |
| admin | admin@campusroom.edu | ADMIN |

All six accounts use the password you set in BOOKIT_DEMO_PASSWORD. These are **local demo accounts only**; use unique passwords and do not run the seeder in production.

From the repository root in PowerShell:

    .\.venv\Scripts\Activate.ps1
    $env:BOOKIT_SEED_DEMO_USERS = "1"
    $env:BOOKIT_DEMO_PASSWORD = "Choose-A-Unique-Password-At-Least-12-Chars"
    $env:BOOKIT_RESET_DEMO_PASSWORDS = "1"
    python backend\scripts\seed_demo_users.py

Unset the environment variables when finished if desired. BOOKIT_RESET_DEMO_PASSWORDS=1 intentionally replaces passwords for matching demo users.

## Database migration

Run the existing table initializer, then apply the migration to the same database used by FastAPI. The migration adds the Events Office approval enum value and the classroom decision-comment column.

    python backend\init_db.py
    & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d book_it_db -f backend\migrations\20261015_event_workflow.sql

Enter your PostgreSQL password when prompted. If your FastAPI database is not named book_it_db, replace that database name with the value configured in your root .env DATABASE_URL. Do not commit .env.

## Room inventory and timetable

1. Sign in as admin.
2. Open **Timetable import** in the navigation.
3. Upload the room inventory CSV first, then upload the occupied timetable CSV.
4. Check the row-level errors returned by each import.

Inventory CSV columns: classroom_id, building, capacity, with optional room_type and active. Building values are AB1, AB2, AB3, AB4. Classroom IDs use codes such as C-101, W-101, E-101. Duplicate classroom codes are allowed across buildings; the building scopes the identity.

Timetable CSV columns: classroom_id, building, day_of_week, start_time, end_time, semester; optional columns are course_code, course_name, faculty_email, effective_from, effective_to. Days can be MON–SUN or 0–6 (Monday is 0). Times use 24-hour HH:MM. Each row is an occupied teaching period. Availability is calculated as periods not occupied by timetable entries, confirmed/pending classroom bookings, active holds, or maintenance.

The sample CSV rows in backend/data are **illustrative only**. No official room list or class schedule was supplied with this change, so these samples must be replaced with the complete campus inventory and authoritative timetable before real-world use. The code cannot infer which classes are actually scheduled.

## Event approval workflow

Event proposals progress through four roles:

1. Faculty
2. Student Welfare
3. Campus Director
4. Events Office

Approvers can approve, reject, return for changes, or request a meeting. The proposal history records decisions and comments. Student requests store the extended proposal fields and allow up to 10 supporting files, each limited to 10 MB. Files are stored under backend/uploads/event_documents by default; configure BOOKIT_UPLOAD_DIR to change this. For deployment, use persistent or object storage because local disks may be ephemeral.

After Student Welfare approval, the app creates a 48-hour hall hold. If that hold expires before director approval, the director-stage transition rechecks conflicts and creates a fresh 48-hour hold only if the hall remains available. Events Office approval performs another conflict check before creating the confirmed hall booking.

## Ticket registration

Ticket reservation locks the registration-event row in PostgreSQL, expires stale holds, checks the active held/confirmed count, and creates a 10-minute hold. The student must confirm before expiry. Unique constraints prevent duplicate registrations by student and roll number.

## Classroom requests

Students select one or more consecutive timetable periods. The selected span is held for five minutes while the request is submitted; it then becomes a PENDING_FACULTY_APPROVAL booking. Pending requests count as occupied for other availability searches. Faculty can approve, reject, or return the request with a required comment; the decision is recorded in audit logs and the student's booking history.

## Important verification

These are source changes on a feature branch and have not been run against your local PostgreSQL instance or browser in this session. Apply the migration, run the seed script, import your real datasets, then start FastAPI and Vite and test each role. Before production, configure persistent file storage, restrict CORS to the deployed frontend origin, and use unique passwords/secrets.
