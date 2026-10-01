from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import User
from ..schemas.auth import RegisterIn, LoginIn, UserOut, ProfileUpdate
from ..security import hash_password, verify_password, create_access_token, current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first(): raise HTTPException(409, "Email already registered")
    u = User(full_name=data.full_name,email=data.email,password_hash=hash_password(data.password),role=data.role,phone=data.phone)
    db.add(u); db.commit(); db.refresh(u)
    return {"access_token":create_access_token(u.id),"token_type":"bearer","user":UserOut.model_validate(u)}

@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == data.email).first()
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
    return {"access_token":create_access_token(u.id),"token_type":"bearer","user":UserOut.model_validate(u)}

@router.get("/me", response_model=UserOut)
def me(user=Depends(current_user)): return user

@router.patch("/me", response_model=UserOut)
def update_me(data: ProfileUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    for field, value in data.model_dump().items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
