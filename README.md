# Intelligent Campus Room Allocation and Event Approval System

## Overview
A production-quality system for managing college room allocations, combining official timetable constraints, real-time bookings, and multi-level approval workflows.

## Technology Stack
- **Frontend**: React + TypeScript + Vite
- **Backend**: Python + FastAPI
- **Database**: PostgreSQL + SQLAlchemy + Alembic
- **Real-time**: Redis + WebSockets
- **Optimization**: Google OR-Tools (CP-SAT)

## Setup Instructions

The maintained UI lives in `frontend/`; the FastAPI application and timetable data live in `backend/`.

1. **Clone and Environment**:
   ```bash
   cp .env.example .env
   docker-compose up --build
   ```

2. **Database Migrations**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

3. **Access**:
   - Backend: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`
   - Frontend: `http://localhost:5173`
   - CampusRoom halls and tickets: `http://localhost:3000`

For frontend-only development:

```bash
cd frontend
npm ci
npm run dev
```

## Architecture Highlights
- **Atomic Bookings**: Uses PostgreSQL pessimistic locking (`FOR UPDATE`) to prevent double-bookings during the 5-minute hold window.
- **Availability Engine**: Merges Timetables, Confirmed Bookings, Active Holds, and Maintenance blocks into a single availability check.
- **Hall Workflow**: Implements a state machine: `PENDING_FACULTY` $\rightarrow$ `PENDING_WELFARE` $\rightarrow$ `PENDING_DIRECTOR` $\rightarrow$ `CONFIRMED`.
- **Auto-Allocation**: Uses Google OR-Tools CP-SAT to solve the room allocation problem based on capacity and equipment constraints.

## Project layout

- `frontend/` — React UI, routing, API client, and frontend build configuration
- `backend/` — FastAPI API, database models, migrations, services, and seed data
- `backend/campusroom/` — Express/PostgreSQL hall approvals and event ticketing service
- `docker-compose.yml` — PostgreSQL, Redis, backend, and frontend services

## Access model

The application has five permission roles across three broad interface experiences:

- Student — classroom, amenity, proposal, and ticket actions
- Faculty — proposal review and event publishing
- Welfare, Director, and Events Office — sequential administrative review stages

The FastAPI service and the Book-It events service currently run as separate authenticated services. A deployment must configure both PostgreSQL connections and start both APIs before all landing-page choices work.
