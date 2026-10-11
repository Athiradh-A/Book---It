import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db, SessionLocal
from app.seed import seed_database
from app.routes import events, registrations, calendar, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    init_db()
    # Seed initial test data if DB is empty
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="Student Limited-Seats Event Booking & Calendar Module",
    description="Modular student-facing event discovery, eligibility-based FCFS seat booking, and Academic Calendar sync.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for standalone or embedded frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(events.router, prefix="/api", tags=["Event Discovery & Eligibility"])
app.include_router(registrations.router, prefix="/api", tags=["Seat Booking & Registrations"])
app.include_router(calendar.router, prefix="/api", tags=["Academic Calendar Sync"])
app.include_router(admin.router, prefix="/api", tags=["Admin & Event Management"])

# Serve frontend static assets if directory exists
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
