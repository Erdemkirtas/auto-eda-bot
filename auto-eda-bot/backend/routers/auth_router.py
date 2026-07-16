"""
backend/routers/auth_router.py — Kayıt ve Giriş Uç Noktaları
=============================================================
/api/auth/register ve /api/auth/login endpoint'lerini sağlar.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import User
from auth import get_password_hash, verify_password, create_access_token
from config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

# İstek modelleri
class UserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None

class TokenInfo(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str


@router.post("/register", response_model=dict)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Yeni kullanıcı kaydeder."""
    # Kullanıcı var mı kontrol et
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Bu kullanıcı adı zaten alınmış."
        )
    
    # Şifreyi hashle ve kaydet
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"success": True, "message": "Kullanıcı başarıyla oluşturuldu."}


@router.post("/login", response_model=TokenInfo)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Kullanıcı adı ve parola ile giriş yapar, JWT Token döndürür."""
    # Kullanıcıyı bul
    user = db.query(User).filter(User.username == form_data.username).first()
    
    # Doğrula
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hatalı kullanıcı adı veya parola.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Token üret
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username
    }
