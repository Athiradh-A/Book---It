"""Local-development account seeder. Never run with demo credentials in production.

PowerShell:
  $env:BOOKIT_SEED_DEMO_USERS = "1"
  $env:BOOKIT_DEMO_PASSWORD = "Choose-A-Local-Password"
  # Optional: reset existing demo-account passwords to the chosen password
  $env:BOOKIT_RESET_DEMO_PASSWORDS = "1"
  python backend/scripts/seed_demo_users.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.db.session import SessionLocal
from app.models.models import User, Role, UserRole
from app.core.security import get_password_hash

if os.getenv("BOOKIT_SEED_DEMO_USERS") != "1":
    raise SystemExit("Safety check: set BOOKIT_SEED_DEMO_USERS=1 to enable local demo seeding.")
password = os.getenv("BOOKIT_DEMO_PASSWORD")
if not password or len(password) < 12:
    raise SystemExit("Set BOOKIT_DEMO_PASSWORD to a unique password of at least 12 characters.")

ACCOUNTS = [
    ("student", "student@campusroom.edu", "Demo Student", "STUDENT"),
    ("faculty", "faculty@campusroom.edu", "Demo Faculty", "FACULTY"),
    ("welfare", "welfare@campusroom.edu", "Student Welfare", "WELFARE"),
    ("director", "director@campusroom.edu", "Campus Director", "DIRECTOR"),
    ("events", "events@campusroom.edu", "Events Office", "EVENTS"),
    ("admin", "admin@campusroom.edu", "Book-It Administrator", "ADMIN"),
]

db = SessionLocal()
try:
    roles = {}
    for name in {a[3] for a in ACCOUNTS}:
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name); db.add(role); db.flush()
        roles[name] = role
    created = []
    for username, email, full_name, role_name in ACCOUNTS:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(username=username, email=email, full_name=full_name, hashed_password=get_password_hash(password), is_active=True)
            db.add(user); db.flush(); created.append(username)
        elif os.getenv("BOOKIT_RESET_DEMO_PASSWORDS") == "1":
            user.hashed_password = get_password_hash(password)
            user.is_active = True
        link = db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == roles[role_name].id).first()
        if not link:
            db.add(UserRole(user_id=user.id, role_id=roles[role_name].id))
    db.commit()
    print("Demo accounts ready. Newly created users:", ", ".join(created) if created else "none (accounts/roles already existed)")
    print("Login username:", ", ".join(a[0] for a in ACCOUNTS))
    print("All accounts use the password supplied in BOOKIT_DEMO_PASSWORD.")
finally:
    db.close()
