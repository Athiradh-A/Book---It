from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, UserRole, Role
from app.core.security import decode_token
from jose.exceptions import JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(db: Session = Depends(get_db)):
    # BYPASS LOGIN: Return a mock student user
    return User(id=1, username="mock_student", email="student@college.edu", full_name="Mock Student")

def get_current_user_roles(user: User = Depends(get_current_user)):
    # BYPASS LOGIN: Return student role
    return ["STUDENT"]

def require_role(allowed_roles: list):
    def role_checker(user: User = Depends(get_current_user), roles = Depends(get_current_user_roles)):
        if not any(role in allowed_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to perform this action"
            )
        return user
    return role_checker
