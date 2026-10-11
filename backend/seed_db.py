import random
import csv
from dotenv import load_dotenv
import os
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal, Base
from app.models.models import Building, Room, Equipment, RoomEquipment, User, Timetable, Booking, BookingHold, EventRequest

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from datetime import datetime, date, timedelta

def import_timetable_csv(db: Session):
    csv_path = Path(__file__).resolve().parent.parent.parent / "room_timetable_monday_friday.csv"
    if not csv_path.exists():
        print(f"CSV file not found at {csv_path}")
        return

    # Define semester dates for the dataset
    semester_start = datetime(2026, 1, 1)
    semester_end = datetime(2026, 12, 31)

    # Exact timings for the 11 slots
    slot_timings = {
        1: ("08:00", "08:50"),
        2: ("08:50", "09:40"),
        3: ("09:40", "10:30"),
        4: ("10:45", "11:35"),
        5: ("11:35", "12:25"),
        6: ("12:25", "13:15"),
        7: ("13:15", "14:05"),
        8: ("14:05", "14:55"),
        9: ("14:55", "15:45"),
        10: ("15:45", "16:35"),
        11: ("16:35", "17:25"),
    }

    print("Importing timetable from CSV (Importing '0' as Official Classes)...")
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            room = db.query(Room).filter(Room.code == row["room_name"]).first()
            if not room:
                continue
            
            day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
            day_of_week = day_map.get(row["day"], 0)
            
            for slot_num in range(1, 12):
                col_name = f"slot_{slot_num}"
                # CRITICAL CHANGE: Only import slots marked "0". 
                # "0" = Official Class = Occuppied.
                # "1" = Bookable = NOT in this table.
                if row.get(col_name) == "0":
                    start_time, end_time = slot_timings[slot_num]
                    db.add(Timetable(
                        room_id=room.id, 
                        day_of_week=day_of_week, 
                        start_time=start_time, 
                        end_time=end_time, 
                        status="ACTIVE",
                        effective_from=semester_start,
                        effective_to=semester_end,
                        semester="Fall 2026"
                    ))
    db.commit()
    print("Timetable CSV imported successfully! '0' slots are now marked as Occupied.")

def seed_data():
    db = SessionLocal()
    try:
        print("Resetting database schema...")
        # Drop all tables to ensure a clean state and updated columns
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("Schema reset successfully.")

        print("Seeding database...")


        # 1. Create Buildings
        buildings = [
            Building(name="Main Academic Block", code="MAB"),
            Building(name="Science Complex", code="SCI"),
            Building(name="Arts & Humanities Hall", code="ART"),
            Building(name="Engineering Wing", code="ENG"),
        ]
        db.add_all(buildings)
        db.commit()

        # 0. Create a Default User (Crucial for bypassing login and booking)
        default_user = User(
            username="admin",
            email="admin@college.edu",
            hashed_password="hashed_password_here",
            full_name="Admin User",
            is_active=True
        )
        db.add(default_user)
        db.commit()
        print(f"Default user created with ID: {default_user.id}")

        # 2. Create Equipment
        equipment_list = [
            Equipment(name="Projector"),
            Equipment(name="Whiteboard"),
            Equipment(name="Air Conditioning"),
            Equipment(name="Smart Board"),
            Equipment(name="Sound System"),
        ]
        db.add_all(equipment_list)
        db.commit()

        # 3. Create Rooms (Matching CSV codes A101, B101, etc.)
        rooms_data = []
        block_codes = ["A", "B", "C", "D", "E"]
        for idx, prefix in enumerate(block_codes):
            b_id = buildings[idx % 4].id
            for floor in range(1, 5):
                for room_num in range(1, 11):
                    code = f"{prefix}{floor}{room_num:02d}"
                    room_type = "HALL" if room_num == 1 and floor == 1 else "CLASSROOM"
                    capacity = 200 if room_type == "HALL" else random.choice([30, 40, 60])
                    rooms_data.append(Room(code=code, building_id=b_id, academic_block=f"AB-{idx+1}", capacity=capacity, room_type=room_type))
        
        db.add_all(rooms_data)
        db.commit()

        # 4. Link Equipment
        all_rooms = db.query(Room).all()
        for room in all_rooms:
            if room.room_type == "HALL":
                for eq in equipment_list:
                    db.add(RoomEquipment(room_id=room.id, equipment_id=eq.id))
            else:
                db.add(RoomEquipment(room_id=room.id, equipment_id=equipment_list[1].id))
                if random.random() > 0.5: db.add(RoomEquipment(room_id=room.id, equipment_id=equipment_list[0].id))
                if random.random() > 0.7: db.add(RoomEquipment(room_id=room.id, equipment_id=equipment_list[2].id))
                if random.random() > 0.9: db.add(RoomEquipment(room_id=room.id, equipment_id=equipment_list[3].id))
        db.commit()

        # 5. Import the official timetable CSV
        import_timetable_csv(db)

        print(f"Successfully seeded the database with {len(all_rooms)} rooms and timetable!")

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
