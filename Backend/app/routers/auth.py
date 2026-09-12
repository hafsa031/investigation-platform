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