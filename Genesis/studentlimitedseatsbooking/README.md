# Student Limited-Seat Event Booking, Eligibility & Academic Calendar Module
### Amrita Vishwa Vidyapeetham, Coimbatore — Campus Portal Component

A modular, highly testable component for student event discovery, multi-condition eligibility verification, server-side First-Come-First-Served (FCFS) atomic seat registration, student dashboard isolation, and Academic Calendar synchronization.

---

## 1. Directory Structure

```text
studentlimitedseatsbooking/
├── README.md
├── .env.example
├── docs/
│   └── integration.md
├── frontend/
│   └── index.html             # Responsive SPA UI with Lucide Icons & Tailwind CSS
└── backend/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py            # FastAPI main entry point with static mounting
    │   ├── database.py        # SQLite WAL mode DB session & transaction locks
    │   ├── seed.py            # Initial test events and student personas
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── models.py      # SQLAlchemy models for Events, Rules, Bookings, Calendar
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   └── schemas.py     # Pydantic validation schemas
    │   ├── services/
    │   │   ├── __init__.py
    │   │   ├── eligibility.py # Multi-condition eligibility rule evaluator
    │   │   ├── booking.py     # FCFS atomic seat allocator & cancellation service
    │   │   └── calendar_sync.py # Idempotent Academic Calendar sync engine
    │   └── routes/
    │       ├── __init__.py
    │       ├── events.py      # Student discovery & search endpoints
    │       ├── registrations.py # FCFS booking & My Registrations endpoints
    │       ├── calendar.py    # Synced Academic Calendar endpoints
    │       └── admin.py       # Event manager & eligibility config endpoints
    └── tests/
        ├── __init__.py
        └── test_booking_module.py # Test suite covering all 20 specified requirements
```

---

## 2. Key Features

1. **Student Discovery**:
   - Lists officially published campus events (`PUBLISHED`). Draft or unapproved events are excluded.
   - Independent event visibility: Every student can discover published events regardless of registration eligibility.
   - Search by keyword and filter by department, category, or registration status (`Registration Open`, `Registration Full`, `Upcoming`, `Cancelled`).

2. **Configurable Eligibility Rules**:
   - Supports combinations of Degree/Programme, Department, Academic Year, and Graduating Batch.
   - Rule logic: **OR** within the same criterion list (e.g. `B.Tech` OR `M.Tech`), **AND** across criteria.
   - Clear, plain-language rejection explanations detailing exact missing or unmatched student attributes.

3. **Server-Side FCFS Atomic Seat Allocation**:
   - Atomic database locking (`BEGIN IMMEDIATE` & atomic SQL update) preventing seat overbooking beyond `total_capacity`.
   - Generates unique registration references (`REG-2025-XXXXXX`).
   - Restricts duplicate active bookings for the same student.
   - Immediate seat release on cancellation, instantly freeing seats for waiting students.

4. **My Registrations Dashboard**:
   - Strict student isolation: Students can only query and view their own seat bookings.

5. **Academic Calendar Sync**:
   - Automatic idempotent synchronization from source events to `AcademicCalendarEntry`.
   - Keyed on `source_event_id` to update existing entries on event modification without creating duplicate records.

---

## 3. Running the Application

### Prerequisites
- Python 3.10+
- Dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `pytest`, `httpx`

### Installation & Launch
```bash
# Navigate to the component directory
cd studentlimitedseatsbooking

# Install dependencies (if not already installed)
pip install -r backend/requirements.txt

# Run the FastAPI Uvicorn Server
$env:PYTHONPATH="backend"
py -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Open your browser and navigate to:
- **Interactive Portal SPA**: [http://127.0.0.1:8001](http://127.0.0.1:8001)
- **API Documentation**: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

---

## 4. Running the Test Suite

Execute the test suite covering all 20 required test scenarios:

```bash
cd studentlimitedseatsbooking
$env:PYTHONPATH="backend"
py -m pytest backend/tests/test_booking_module.py -v
```

### Test Coverage (16 Test Functions / 20 Scenarios)
- `test_1_published_event_discovery`: Drafts hidden, published visible.
- `test_2_event_visibility_independent_of_eligibility`: Ineligible student can discover restricted event.
- `test_3_open_vs_restricted_eligibility`: Open vs restricted event evaluation.
- `test_4_multicondition_eligibility`: OR within criterion, AND across criteria.
- `test_5_clear_explanation_for_ineligible_student`: Plain language rejection reasoning.
- `test_6_missing_profile_attributes`: Unverified/missing profile denial.
- `test_7_8_fcfs_seat_allocation_and_overbooking_prevention`: Seat allocation up to limit and overbooking rejection.
- `test_9_concurrent_fcfs_seat_allocation`: Parallel thread booking safety under capacity limit.
- `test_10_duplicate_registration_prevention`: Rejection of duplicate bookings.
- `test_11_registration_reference_generation`: Format `REG-{YYYY}-{HEX}` validation.
- `test_12_13_seat_release_and_rebooking`: Seat release on cancellation and immediate re-claim.
- `test_14_registration_window_enforcement`: Rejection outside registration start/end windows.
- `test_15_my_registrations_dashboard_isolation`: Strict user isolation in My Registrations dashboard.
- `test_16_17_18_academic_calendar_sync`: Idempotent Academic Calendar synchronization and status updates.
- `test_19_non_registration_announcement_types`: Informational events rejection of seat booking.
- `test_20_admin_event_management`: Admin creation, eligibility configuration, and publish state toggling.
