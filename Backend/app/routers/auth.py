<<<<<<< Updated upstream
from fastapi import APIRouter, HTTPException, status
from app.schemas.auth import UserLogin, Token
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    if credentials.username == "investigator" and credentials.password == "password123":
        token = create_access_token(data={"sub": credentials.username})
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
=======
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.config import settings
from app.database import get_db
from app.models import UserModel
from app.core.security import get_password_hash, verify_password, create_access_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=160)

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=72)

def create_password_reset_token(email: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode({"sub": email, "exp": expires, "type": "reset"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_password_reset_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub") if payload.get("type") == "reset" else None
    except JWTError:
        return None

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    if db.query(UserModel).filter(UserModel.email == email).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    user = UserModel(email=email, hashed_password=get_password_hash(data.password), full_name=data.full_name, role="analyst")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    email = form_data.username.strip().lower()
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(str(user.id)), "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_me(user: UserModel = Depends(get_current_user)):
    return user

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == str(payload.email).lower()).first()
    if not user:
        return {"message": "If the email exists, a password reset token has been generated."}
    # Demo workflow: token is returned to the caller. Production deployments should email it instead.
    return {"message": "Password reset token generated successfully.", "reset_token": create_password_reset_token(user.email)}

@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    email = verify_password_reset_token(payload.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password has been successfully reset. You can now log in."}
>>>>>>> Stashed changes
