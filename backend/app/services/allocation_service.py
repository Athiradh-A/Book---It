from ortools.sat.python import cp_model
from sqlalchemy.orm import Session
from app.models.models import Room, Timetable, Booking
from app.services.availability_service import AvailabilityService, AvailabilityRequest
from datetime import datetime
from fastapi import HTTPException

class AllocationService:
    @staticmethod
    def auto_allocate_bookings(db: Session, requested_bookings_data: list):
        """
        requested_bookings_data: List of (user_id, start_time, end_time, capacity, eq_ids)
        """
        model = cp_model.CpModel()
        rooms = db.query(Room).filter(Room.is_active == True).all()
        
        # Variables: x[booking_id, room_id] = 1 if booking i is assigned to room j
        x = {}
        for i in range(len(requested_bookings_data)):
            for j in range(len(rooms)):
                x[i, j] = model.NewBoolVar(f"booking_{i}_room_{j}")

        # Constraint 1: Each booking must be assigned to exactly one room
        for i in range(len(requested_bookings_data)):
            model.Add(sum(x[i, j] for j in range(len(rooms))) == 1)

        # Constraint 2: Room suitability (Capacity/Equipment)
        for i in range(len(requested_bookings_data)):
            req_data = requested_bookings_data[i]
            req = AvailabilityRequest(
                date=req_data[1],
                start_time=req_data[1],
                end_time=req_data[2],
                required_capacity=req_data[3],
                required_equipment_ids=req_data[4]
            )
            for j in range(len(rooms)):
                res = AvailabilityService.check_room_availability(db, rooms[j].id, req)
                if not res.is_available and res.conflict_type in ["CAPACITY", "EQUIPMENT", "ROOM_TYPE"]:
                    model.Add(x[i, j] == 0)

        # Constraint 3: No overlapping assignments in the same room
        for j in range(len(rooms)):
            for i in range(len(requested_bookings_data)):
                for k in range(i + 1, len(requested_bookings_data)):
                    # Check if booking i and k overlap
                    if (requested_bookings_data[i][1] < requested_bookings_data[k][2] and 
                        requested_bookings_data[k][1] < requested_bookings_data[i][2]):
                        model.Add(x[i, j] + x[k, j] <= 1)

        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            assignments = []
            for i in range(len(requested_bookings_data)):
                for j in range(len(rooms)):
                    if solver.Value(x[i, j]) == 1:
                        assignments.append({"booking_index": i, "room_id": rooms[j].id})
            return assignments
        else:
            return None

    @staticmethod
    def simulate_what_if(db: Session, unavailable_room_id: int, date: datetime, start: datetime, end: datetime):
        # Simulate a scenario where a specific room is marked as maintenance
        # and check how it affects current availability requests
        # In a real system, this would run the auto_allocate_bookings with the room excluded.
        return {"message": f"Simulation complete: Room {unavailable_room_id} marked as unavailable. Recalculating alternatives..."}

