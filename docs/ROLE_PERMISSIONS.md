# Book-It role permissions

## Role hierarchy

`STUDENT < FACULTY < WELFARE < DIRECTOR < EVENTS`

Higher workflow roles inherit lower-level feature permissions. This inheritance is for general features; it does **not** grant approval authority for another stage.

| Role | Feature access | Event approval authority |
|---|---|---|
| Student | Room search and booking, event proposals, published event registration, amenities, own bookings and notifications | None |
| Faculty | Student features plus faculty-level review tools and relevant faculty event management | Faculty stage only |
| Student Welfare (`WELFARE`) | Faculty features plus welfare review | Student Welfare stage only |
| Campus Director (`DIRECTOR`) | Lower-level features plus director review | Director stage only |
| Events Office (`EVENTS`) | Lower-level features plus final review and published-event operations | Events Office/final stage only |
| System Administrator (`ADMIN`) | System administration tools such as timetable import and resource configuration | No implicit event-stage approval bypass |

## Enforcement notes

- Public registration always assigns `STUDENT`; users cannot choose a privileged role through the registration payload.
- The backend enforces roles. Hiding a navigation link is only a usability measure, not the security boundary.
- Event approval queues are stage-specific. Approval decisions and meeting resolutions check the user's directly assigned role against the event's current stage.
- Proposal history and documents are visible to the requester, system administrators, and the reviewer for the current stage. Uploading proposal documents is restricted to the requester or a system administrator.
- Timetable import and resource configuration remain system-administrator capabilities; the Events Office role does not imply system administration.
- Role assignments for Faculty, Student Welfare, Campus Director, and Events Office must be made by a trusted administrator through the application's authorized provisioning process/database. Do not add privileged role selection to public registration.

## Manual verification checklist

1. Register a new account and confirm `/auth/me` returns only `STUDENT`.
2. Assign `FACULTY`, `WELFARE`, `DIRECTOR`, and `EVENTS` to separate test accounts using the trusted administrative process.
3. Confirm each role sees the shared booking features and only its own event approval queue.
4. Attempt to approve a proposal at a different role's stage directly through the API; expect HTTP 403.
5. Attempt to open `/admin/timetable` as a non-admin; expect redirection to the dashboard and HTTP 403 from the API.
6. Confirm a user cannot read another user's proposal history unless they are the reviewer for its current stage or a system administrator.
7. Confirm final Events Office approval creates a confirmed hall booking and published registration event.
