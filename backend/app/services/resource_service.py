from sqlalchemy.orm import Session
from app.models.models import Building, Room, Equipment, RoomEquipment
from app.schemas.resources import BuildingCreate, RoomCreate, EquipmentCreate

class ResourceService:
    @staticmethod
    def create_building(db: Session, building_in: BuildingCreate):
        db_building = Building(**building_in.model_dump())
        db.add(db_building)
        db.commit()
        db.refresh(db_building)
        return db_building

    @staticmethod
    def get_buildings(db: Session):
        return db.query(Building).all()

    @staticmethod
    def create_equipment(db: Session, equipment_in: EquipmentCreate):
        db_eq = Equipment(**equipment_in.model_dump())
        db.add(db_eq)
        db.commit()
        db.refresh(db_eq)
        return db_eq

    @staticmethod
    def get_equipment(db: Session):
        return db.query(Equipment).all()

    @staticmethod
    def create_room(db: Session, room_in: RoomCreate):
        # Separate equipment ids from the basic room data
        data = room_in.model_dump()
        eq_ids = data.pop("equipment_ids", [])
        
        db_room = Room(**data)
        db.add(db_room)
        db.commit()
        db.refresh(db_room)
        
        for eq_id in eq_ids:
            db_re = RoomEquipment(room_id=db_room.id, equipment_id=eq_id)
            db.add(db_re)
        
        db.commit()
        return db_room

    @staticmethod
    def get_rooms(db: Session, building_id: int = None):
        query = db.query(Room)
        if building_id:
            query = query.filter(Room.building_id == building_id)
        return query.all()
