# Book-It workflow patch notes

## Changes in this patch

- Classroom requests now store `assigned_faculty_id` and can only be listed/decided by the assigned account with a direct `FACULTY` role.
- Students select an active faculty account from `/api/bookings/faculty-directory`; the confirm endpoint independently validates the submitted email against an active account with a direct `FACULTY` role. A requester cannot assign the request to their own account.
- Classroom hold/confirm and faculty-directory endpoints require a direct `STUDENT` role. The classroom decision endpoint does not grant Admin, Student Welfare, Campus Director, or Events Office a bypass.
- Approval navigation uses explicitly assigned roles rather than allowing Admin through a generic bypass. The approval page loads the classroom queue only for accounts with a direct `FACULTY` role.
- Hall approvals lock the shared room row before creating/renewing the 48-hour hold and during final conversion. Hall bookings retain the source `event_request_id`.
- A booking-specific history endpoint returns classroom audit decisions or the approval steps belonging to that hall booking's source event proposal. My Bookings now has a timeline view.
- Added small styles for the faculty selector and timeline panel.

## Database migration

Back up the database, then apply:

```sh
psql "$DATABASE_URL" -f backend/migrations/20261018_classroom_faculty_assignment_and_booking_history.sql
```

The migration adds nullable columns to preserve existing bookings. Existing pending classroom requests have no assigned faculty yet; assign them deliberately before expecting them to appear in any faculty queue. This patch does not guess their intended approver.

## Microsoft sign-in boundary

The current project uses its existing username/password authentication. This patch uses the email stored on an existing Book-It user record to route classroom requests; it does **not** add Microsoft Entra ID single sign-on. To make the campus Microsoft account the login identity, the university's Entra tenant/app registration details and redirect URI must be configured, and the backend must validate Entra-issued tokens before mapping the verified tenant/object identity to a Book-It user. Do not trust a client-supplied email as proof of login identity.

## Validation performed

- Backend Python syntax/AST parse: passed.
- Existing backend tests: 13 passed.
- SQLAlchemy model metadata/create-all check using SQLite: passed for model declarations.
- Frontend production build: not run successfully because frontend dependencies are absent and package installation could not reach the package registry in this environment.
- PostgreSQL migration execution, authenticated API integration tests, concurrent reservation tests, Microsoft SSO, and visual viewport checks remain unverified.
