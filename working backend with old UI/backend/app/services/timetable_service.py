import pandas as pd
from sqlalchemy.orm import Session
from app.models.models import Timetable
from app.schemas.resources import TimetableCreate
from fastapi import HTTPException

class TimetableService:
    @staticmethod
    def import_from_file(db: Session, file_path: str):
        # Use pandas to read CSV or Excel
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith((".xls", ".xlsx")):
            df = pd.read_excel(file_path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        imported_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Map CSV columns to Timetable model
                # Expected CSV columns: course_id, faculty_id, room_id, day_of_week, start_time, end_time, semester
                timetable_data = Timetable(
                    course_id=int(row["course_id"]),
                    faculty_id=int(row["faculty_id"]),
                    room_id=int(row["room_id"]),
                    day_of_week=int(row["day_of_week"]),
                    start_time=str(row["start_time"]),
                    end_time=str(row["end_time"]),
                    semester=str(row["semester"]),
                    status="ACTIVE"
                )
                db.add(timetable_data)
                imported_count += 1
            except Exception as e:
                errors.append(f"Row {index}: {str(e)}")

        db.commit()
        return imported_count, errors

    @staticmethod
    def get_all_timetables(db: Session):
        return db.query(Timetable).all()

    @staticmethod
    def delete_timetable(db: Session, timetable_id: int):
        db_tt = db.query(Timetable).filter(Timetable.id == timetable_id).first()
        if not db_tt:
            return None
        db.delete(db_tt)
        db.commit()
        return True
