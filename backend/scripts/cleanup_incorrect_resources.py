import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import SessionLocal
from app.models.models import Building, Room

WRONG_CODES = {"MAB", "SCI", "ENG"}
EXPECTED_CODES = {"AB1", "AB2", "AB3", "AB4"}
EXPECTED_ROOMS = {"C-101", "W-101", "E-101"}

def main():
    db = SessionLocal()
    try:
        wrong_buildings = db.query(Building).filter(
            Building.code.in_(WRONG_CODES)
        ).all()
        correct_buildings = db.query(Building).filter(
            Building.code.in_(EXPECTED_CODES)
        ).all()

        if {b.code for b in correct_buildings} != EXPECTED_CODES:
            raise RuntimeError("Expected AB1–AB4 to exist. No changes made.")

        if {b.code for b in wrong_buildings} != WRONG_CODES:
            raise RuntimeError("Unexpected incorrect-building inventory. No changes made.")

        wrong_ids = {b.id for b in wrong_buildings}
        wrong_rooms = db.query(Room).filter(
            Room.building_id.in_(wrong_ids)
        ).all()

        print("Buildings to remove:", [(b.id, b.code, b.name) for b in wrong_buildings])
        print("Rooms to remove:", [(r.id, r.code, r.building_id) for r in wrong_rooms])
        print("Correct buildings to retain:", sorted(b.code for b in correct_buildings))

        confirmation = input(
            "\nType DELETE-INCORRECT-RESOURCES to continue: "
        )
        if confirmation != "DELETE-INCORRECT-RESOURCES":
            print("Cancelled. No changes made.")
            return

        for room in wrong_rooms:
            db.delete(room)
        db.flush()

        for building in wrong_buildings:
            db.delete(building)

        db.commit()
        print("\nCleanup committed.")

        print("Buildings remaining:",
              [(b.code, b.name) for b in db.query(Building).order_by(Building.code).all()])
        print("Rooms remaining:",
              [(r.code, r.academic_block, r.capacity)
               for r in db.query(Room).order_by(Room.building_id, Room.code).all()])
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
