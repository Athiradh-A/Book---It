import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from backend.app.models import Base

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./portal.db")

# Enable check_same_thread=False for SQLite with FastAPI multi-threading
engine = create_engine(
    DB_PATH,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

# Enable Foreign Keys & WAL mode for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
