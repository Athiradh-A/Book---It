"""Idempotently create Book-It workflow roles. Does not modify account assignments by default.

Run from project root:
  python backend/scripts/seed_workflow_roles.py
Optional: assign DIRECTOR to an existing account by exact username (keeps password/history):
  python backend/scripts/seed_workflow_roles.py --assign-director-username campus_director
"""
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.db.session import SessionLocal
from app.models.models import Role, User, UserRole

parser = argparse.ArgumentParser()
parser.add_argument('--assign-director-username', help='Exact existing username to assign DIRECTOR; no password changes')
args = parser.parse_args()
db = SessionLocal()
try:
    names = ('STUDENT', 'FACULTY', 'WELFARE', 'DIRECTOR', 'EVENTS', 'ADMIN')
    for name in names:
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name)); db.flush()
    if args.assign_director_username:
        user = db.query(User).filter(User.username == args.assign_director_username).with_for_update().first()
        if not user:
            raise SystemExit(f'No user found with exact username {args.assign_director_username!r}; no changes committed.')
        role = db.query(Role).filter(Role.name == 'DIRECTOR').one()
        if not db.query(UserRole).filter_by(user_id=user.id, role_id=role.id).first():
            db.add(UserRole(user_id=user.id, role_id=role.id))
        student_role = db.query(Role).filter(Role.name == 'STUDENT').first()
        if student_role:
            db.query(UserRole).filter_by(user_id=user.id, role_id=student_role.id).delete(synchronize_session=False)
    db.commit()
    print('Workflow roles ensured:', ', '.join(names))
    if args.assign_director_username: print('DIRECTOR assigned to existing account:', args.assign_director_username)
    print('No passwords or event/approval records were changed.')
except Exception:
    db.rollback(); raise
finally:
    db.close()
