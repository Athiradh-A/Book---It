# Book-It 2.0 architecture audit

## What exists

- The core FastAPI service contains JWT issuance, users and roles, resource CRUD, timetable import, room availability, classroom holds and confirmation, event requests, notifications, analytics, and OR-Tools allocation endpoints.
- PostgreSQL is the core data store. Redis and a WebSocket manager are configured, but Redis is not currently used to coordinate booking transactions or publish notifications.
- The React/Vite frontend had login, room search, eleven-slot selection, and event request screens. Most calls were made directly with Axios rather than through a shared authenticated client.
- `Genesis/campusdirector` and `Genesis/studentlimitedseatsbooking` are independent SQLite applications. Their models and identity systems are not integrated with the core database. The Director module contains useful workflow concepts; the limited-seat module contains a useful atomic seat-decrement pattern. Neither should be mounted unchanged into the core service.
- Root `main.py` is a separate PostgreSQL CLI prototype. It has useful unique-key/transaction and FIFO ideas, but uses a different schema and a machine-specific CSV path.

## Material gaps found

- Authentication was bypassed in both the React router and FastAPI dependencies. Classroom writes impersonated a hard-coded administrator.
- Holds and confirmation did not atomically recheck all overlapping reservations, confirm ownership, or handle idempotent confirmation.
- Event approval lists were not filtered by approval stage and the approval action was not role-gated per stage. The existing state machine also omits the final Events Department stage requested by the product brief.
- The frontend had no centralized authenticated API client, booking history, amenities, real approval UI, or admin UI. Dashboard data was static.
- Equipment represented room features only; it was not an independently reservable amenity inventory.
- The README advertises Alembic, but no Alembic environment or prior revision chain exists. A first amenities revision is included as a migration artifact, but an Alembic environment must be initialized before `alembic upgrade` can run.
- Allocation simulation remains a placeholder and CP-SAT suggestions are not persisted safely through the booking service.
- CORS permits every origin while credentials are enabled. The JWT default secret is unsafe for production.
- Existing automated coverage is limited to the standalone Genesis apps; there are no core backend or frontend tests.

## Integration direction

The core FastAPI/PostgreSQL application remains the system of record. Genesis code stays isolated until its relevant policies are ported behind the shared user/role model. All user-facing calls go through one typed/authenticated client. Classroom, hall, and amenity workflows use database transactions and shared overlap semantics. Approval transitions should be consolidated into one stage-aware service with an audit entry for every decision. Redis can then broadcast committed notifications, but must not replace PostgreSQL constraints as the booking authority.

## Implemented milestone

- Restored real JWT validation and database-backed roles.
- Removed hard-coded classroom users; added hold ownership, row locking, overlap revalidation, expiry handling, idempotent confirmation, history, and cancellation endpoints.
- Added amenity inventory and booking models, schemas, APIs, quantity-aware overlap checks, approval decisions, notifications, history, cancellation, and a migration artifact.
- Added a centralized frontend API client, protected application shell, cinematic responsive landing page, amenities experience, and unified booking history.
- Added responsive/reduced-motion behavior without another animation dependency.

## Next milestone

Stage-authorize and complete the hall approval workflow, build its role queue and timeline UI, add the admin management screens, route dashboard cards to real aggregate endpoints, strengthen allocation constraints, create the Alembic baseline, and add concurrency/authorization tests.
