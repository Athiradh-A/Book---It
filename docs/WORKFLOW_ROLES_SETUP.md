# Book-It workflow roles: safe setup and verification

## What changed

- Added an idempotent role seed for `STUDENT`, `FACULTY`, `WELFARE`, `DIRECTOR`, `EVENTS`, and `ADMIN`.
- Added an opt-in assignment command for an existing account. It preserves the user ID, password hash, and event/approval history. For a director account it adds `DIRECTOR` and removes only that account's redundant `STUDENT` role link.
- Added a requester-only resubmission endpoint for `RETURNED_FOR_CHANGES`. The existing approval rows remain intact; a `RESUBMITTED` history row is appended and the proposal returns to Faculty stage.
- Added tests for stage transitions, unauthorized stage-role checks, returned proposals, meeting requests that do not advance the workflow, and final confirmation.
- Tightened meeting resolution so `ADMIN` alone is not treated as an approval-stage role.
- Frontend feature visibility now treats higher workflow roles as inheriting student features while keeping approval decisions stage-specific.

## Before running a database command

**Confirm the app's `DATABASE_URL` targets your intended `book_it_db` database.** The default in `backend/app/db/session.py` is `campus_room_db`, which is not the database inspected for this workflow. Do not run the seed command until the connection target is verified.

PowerShell example for the local PostgreSQL instance (replace `YOUR_PASSWORD`):

```powershell
$env:DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/book_it_db"
python backend/scripts/seed_workflow_roles.py
```

This first command only ensures that role rows exist. It does not modify role assignments.

After verifying that `campus_director` is the exact account you intend to promote, run:

```powershell
python backend/scripts/seed_workflow_roles.py --assign-director-username campus_director
```

This only changes that account's role links. It does not create accounts, reset passwords, delete users, or modify event requests or approval history. Other role assignments (Faculty, Welfare, Events) should be mapped only after confirming their exact existing usernames.

## SQL migration alternative

Run `backend/migrations/20261017_workflow_roles.sql` against the intended database. It inserts missing role names only and is safe to rerun. It does not assign roles to users.

## Tests

From the project root:

```powershell
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -q
```

The tests exercise pure transition/permission rules, not a live database or full HTTP integration. A frontend production build should also be run in the project environment after installing dependencies.
