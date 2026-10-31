from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from uuid import UUID

from app.database import get_db
from app.models import UserModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    role: str = "analyst"

class UserResponse(BaseModel):
    id: UUID  # Natively supports UUID objects from PostgreSQL
    email: EmailStr
    full_name: str | None = None
    role: str

    class Config:
        from_attributes = True

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if email already exists in PostgreSQL
    existing_email = db.query(UserModel).filter(UserModel.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Safely hash the password with a 72-character limit for bcrypt compatibility
    hashed_password = pwd_context.hash(user_data.password[:72])
    
    # Create the new user database model instance matching the 10-table schema
    new_user = UserModel(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role
    )
    
    # Save to PostgreSQL database permanently
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    # Query PostgreSQL for the user by email (OAuth2 form passes email into the 'username' field)
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    
    # Check if user exists and password matches (with safe slice)
    if not user or not pwd_context.verify(form_data.password[:72], user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {"access_token": user.email, "token_type": "bearer"}