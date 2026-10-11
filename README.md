# Intelligent Campus Room Allocation and Event Approval System

## ?? Overview
A production-quality system for managing college room allocations, combining official timetable constraints, real-time bookings, and multi-level approval workflows.

## ??? Technology Stack
- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: Python + FastAPI
- **Database**: PostgreSQL + SQLAlchemy + Alembic
- **Real-time**: Redis + WebSockets
- **Optimization**: Google OR-Tools (CP-SAT)

## ?? Setup Instructions

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

## ??? Architecture Highlights
- **Atomic Bookings**: Uses PostgreSQL pessimistic locking (`FOR UPDATE`) to prevent double-bookings during the 5-minute hold window.
- **Availability Engine**: Merges Timetables, Confirmed Bookings, Active Holds, and Maintenance blocks into a single availability check.
- **Hall Workflow**: Implements a state machine: `PENDING_FACULTY` $\rightarrow$ `PENDING_WELFARE` $\rightarrow$ `PENDING_DIRECTOR` $\rightarrow$ `CONFIRMED`.
- **Auto-Allocation**: Uses Google OR-Tools CP-SAT to solve the room allocation problem based on capacity and equipment constraints.

## ?? Testing
- Backend tests: `pytest`
- Frontend tests: `vitest`
