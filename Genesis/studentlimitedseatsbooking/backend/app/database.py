import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.models.models import Base

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///./student_booking.db")

engine = create_engine(
    DB_PATH,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(target_engine=None):
    use_engine = target_engine if target_engine else engine
    Base.metadata.create_all(bind=use_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
