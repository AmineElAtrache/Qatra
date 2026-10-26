from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.models import Farmer

router = APIRouter()


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""
    role: str = "farmer"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post("/register", response_model=TokenOut)
def register(body: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    if db.query(Farmer).filter(Farmer.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if body.role not in {"farmer", "advisor"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    farmer = Farmer(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(farmer)
    db.commit()
    db.refresh(farmer)
    token = create_access_token(str(farmer.id), {"role": farmer.role, "email": farmer.email})
    return TokenOut(access_token=token, role=farmer.role)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    farmer = db.query(Farmer).filter(Farmer.email == body.email).first()
    if not farmer or not verify_password(body.password, farmer.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad credentials")
    token = create_access_token(str(farmer.id), {"role": farmer.role, "email": farmer.email})
    return TokenOut(access_token=token, role=farmer.role)
