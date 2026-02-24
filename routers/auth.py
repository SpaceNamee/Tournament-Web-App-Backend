from datetime import timedelta
from fastapi import Depends, HTTPException, status, APIRouter, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from auth.auth_handler import (
    authenticate_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_user,
    get_password_hash,
)
from database import get_db
from schemas import Token, UserCreate, UserResponse
from models import User
import random
from pydantic import BaseModel

auth_router = APIRouter(prefix="", tags=["auth"])
verification_codes = {}  

@auth_router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    if get_user(db, user.nickname):
        raise HTTPException(status_code=400, detail="Nickname already registered.")
    if get_user(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    hashed_password = get_password_hash(user.password)
    db_user = User(
        name=user.name,
        nickname=user.nickname,
        email=user.email,
        hashed_password=hashed_password,
        phone_number=user.phone_number,
        date_of_birth=user.date_of_birth,
        tournament_notif=user.tournament_notif,
        match_notif=user.match_notif,
        general_notif=user.general_notif,
        is_admin=False,
        is_verified=False,  
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@auth_router.post("/send-verification-code")
def send_verification_code(email: str = Query(...), db: Session = Depends(get_db)):
    user = get_user(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    code = f"{random.randint(100000, 999999)}"
    verification_codes[email] = code
    print(f"Verification code for {email}: {code}")

    return {"message": "Verification code sent successfully."}

# ---------------------- LOGIN ----------------------
from pydantic import BaseModel
class TokenWithUserId(BaseModel):
    access_token: str
    token_type: str
    user_id: int

@auth_router.post("/token", response_model=TokenWithUserId)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,  
    }

class VerificationCode(BaseModel):
    email: str
    code: str
@auth_router.post("/verify-code")
def verify_code(data: VerificationCode, db: Session = Depends(get_db)):
    user = get_user(db, data.email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.email_verified = True
    db.commit()

    return {"message": "Email verified successfully."}

