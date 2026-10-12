from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.allocation_service import AllocationService
from datetime import datetime

router = APIRouter(prefix="/allocation", tags=["Allocation"])

@router.post("/auto-allocate")
def auto_allocate(requests: list, db: Session = Depends(get_db)):
    # requests: list of [user_id, start_time, end_time, capacity, eq_ids]
    # Simplified parsing for demonstration
    parsed_reqs = []
    for r in requests:
        parsed_reqs.append([
            r["user_id"],
            datetime.fromisoformat(r["start"]),
            datetime.fromisoformat(r["end"]),
            r["capacity"],
            r.get("eq_ids", [])
        ])
    
    result = AllocationService.auto_allocate_bookings(db, parsed_reqs)
    if not result:
        return {"status": "Infeasible", "message": "Could not allocate all requests."}
    return {"status": "Success", "assignments": result}

@router.get("/simulate")
def simulate(room_id: int, date_str: str, start_str: str, end_str: str, db: Session = Depends(get_db)):
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M")
    end = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M")
    return AllocationService.simulate_what_if(db, room_id, date, start, end)

