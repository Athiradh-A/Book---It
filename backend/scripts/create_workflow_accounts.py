
import os
import sys
from getpass import getpass
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath("backend"))

from app.db.session import SessionLocal
from app.models.models import User, Role, UserRole
from app.core.security import get_password_hash

ACCOUNTS = [
    {
        "username": "faculty_test",
        "email": "faculty_test@example.com",
        "full_name": "Faculty Test",
        "role": "FACULTY",
    },
    {
        "username": "welfare_test",
        "email": "welfare_test@example.com",
        "full_name": "Student Welfare Test",
        "role": "WELFARE",
    },
    {
        "username": "events_test",
        "email": "events_test@example.com",
        "full_name": "Events Office Test",
        "role": "EVENTS",
    },
]

def main():
    db: Session = SessionLocal()
    created = []
    try:
        for account in ACCOUNTS:
            existing = (
                db.query(User)
                .filter(
                    (User.username == account["username"])
                    | (User.email == account["email"])
                )
                .first()
            )
            if existing:
                print(
                    f"SKIPPED {account['username']}: "
                    f"username or email already exists"
                )
                continue

            password = getpass(
                f"Set password for {account['username']}: "
            )
            confirm = getpass("Confirm password: ")
            if not password or password != confirm:
                raise ValueError(
                    f"Password empty or confirmation mismatch for "
                    f"{account['username']}. No changes committed."
                )

            role = (
                db.query(Role)
                .filter(Role.name == account["role"])
                .first()
            )
            if not role:
                raise ValueError(
                    f"Role {account['role']} is missing. "
                    "Run the role seeder first."
                )

            user = User(
                username=account["username"],
                email=account["email"],
                full_name=account["full_name"],
                hashed_password=get_password_hash(password),
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id))
            created.append(account["username"])
            print(f"Prepared {account['username']} with role {account['role']}")

        db.commit()
        print("\nAccount creation complete.")
        print("Created:", ", ".join(created) if created else "None")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
