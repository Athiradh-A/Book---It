from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env file from the parent directory
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

from app.db.session import engine, Base
from app.models import models

print(f"Using DATABASE_URL: {os.getenv('DATABASE_URL')}")
print("Connecting to database and creating tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Successfully created all tables in the database!")
except Exception as e:
    print(f"An error occurred: {e}")

