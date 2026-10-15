# Classroom timetable import

Upload a CSV using **Admin → Timetable import** (API: `POST /api/resources/timetables/import-dataset`).

Required columns:
- `classroom_id`: room code such as `C-101`, `W-101`, or `E-101`
- `building`: building code such as `AB1`, `AB2`, `AB3`, or `AB4`
- `day_of_week`: `MON`–`SUN` or integer `0`–`6` (Monday is 0)
- `start_time`, `end_time`: 24-hour `HH:MM`
- `semester`: timetable semester label

Optional columns: `course_code`, `course_name`, `faculty_email`, `effective_from`, `effective_to`. Dates use `YYYY-MM-DD`. If dates are omitted, entries are active from the import date through 2099-12-31. A supplied faculty email must already be linked to a record in the `faculty` table.

**Important:** the CSV rows represent occupied class periods; Book-It derives free periods by checking the absence of timetable classes, bookings, active holds, and maintenance. The included CSV contains illustrative demo rows, not an official Amrita timetable. Replace them with the official schedule before using the availability results for real bookings. Room inventory must already exist in PostgreSQL, and classroom codes are scoped by building.
