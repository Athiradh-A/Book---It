import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.models import Building, Room, Equipment

BUILDINGS = [
    {"name": f"Academic Block {i}", "code": f"AB{i}"}
    for i in range(1, 5)
]

ROOM_CODES = ["C-101", "W-101", "E-101"]
EQUIPMENT_NAMES = [
    "Projector",
    "Whiteboard",
    "Air Conditioning",
    "Smart Board",
    "Sound System",
]

def seed_resources():
    db = SessionLocal()
    try:
        for data in BUILDINGS:
            if not db.query(Building).filter_by(code=data["code"]).first():
                db.add(Building(**data))
        db.flush()

        buildings = {
            b.code: b
            for b in db.query(Building).filter(
                Building.code.in_(["AB1", "AB2", "AB3", "AB4"])
            ).all()
        }

        for block_code, building in buildings.items():
            for room_code in ROOM_CODES:
                exists = db.query(Room).filter_by(
                    code=room_code,
                    building_id=building.id
                ).first()
                if not exists:
                    db.add(Room(
                        code=room_code,
                        building_id=building.id,
                        academic_block=block_code,
                        room_type="CLASSROOM",
                        capacity=40,
                        is_active=True
                    ))

        for name in EQUIPMENT_NAMES:
            if not db.query(Equipment).filter_by(name=name).first():
                db.add(Equipment(name=name))

        db.commit()
        print("Resource seeding completed.")
        print("Buildings:", db.query(Building).count())
        print("Rooms:", db.query(Room).count())
        print("Equipment:", db.query(Equipment).count())

        for building in db.query(Building).filter(
            Building.code.in_(["AB1", "AB2", "AB3", "AB4"])
        ).order_by(Building.code).all():
            rooms = db.query(Room).filter_by(
                building_id=building.id
            ).order_by(Room.code).all()
            print(f"\n{building.code} - {building.name}")
            print(", ".join(room.code for room in rooms))

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_resources()
