from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.models import User, UserRole, Role
from app.core.security import decode_token
from jose.exceptions import JWTError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access" or not payload.get("sub"):
            raise credentials_error
    except JWTError:
        raise credentials_error
    user = db.query(User).filter(User.username == payload["sub"], User.is_active.is_(True)).first()
    if not user:
        raise credentials_error
    return user

def get_current_user_roles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [name for (name,) in db.query(Role.name).join(UserRole, UserRole.role_id == Role.id).filter(UserRole.user_id == user.id).all()]

def require_role(allowed_roles: list):
    def role_checker(user: User = Depends(get_current_user), roles = Depends(get_current_user_roles)):
        if not any(role in allowed_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="You do not have permission to perform this action"
            )
        return user
    return role_checker
