from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import os
import psutil

from database import get_db
from models import User, AnalysisLog
from auth import get_current_admin
from pydantic import BaseModel
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])

class UserOut(BaseModel):
    id: int
    username: str
    email: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime | None

    class Config:
        orm_mode = True

@router.get("/users", response_model=List[UserOut])
def get_all_users(db: Session = Depends(get_db), admin_user: User = Depends(get_current_admin)):
    """Sistemdeki tüm kullanıcıları listeler."""
    users = db.query(User).all()
    return users

@router.delete("/users/{user_id}", response_model=dict)
def delete_user(user_id: int, db: Session = Depends(get_db), admin_user: User = Depends(get_current_admin)):
    """Kullanıcıyı siler (Admin hariç tutularak)."""
    if admin_user.id == user_id:
        raise HTTPException(status_code=400, detail="Kendinizi silemezsiniz!")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
        
    db.delete(user)
    db.commit()
    return {"success": True, "message": f"{user.username} silindi."}

@router.patch("/users/{user_id}/role", response_model=dict)
def update_user_role(user_id: int, is_admin: bool, db: Session = Depends(get_db), admin_user: User = Depends(get_current_admin)):
    """Kullanıcının admin yetkisini değiştirir."""
    if admin_user.id == user_id:
        raise HTTPException(status_code=400, detail="Kendi yetkinizi değiştiremezsiniz!")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
        
    user.is_admin = is_admin
    db.commit()
    return {"success": True, "message": f"{user.username} yetkisi güncellendi."}

@router.get("/stats", response_model=dict)
def get_system_stats(db: Session = Depends(get_db), admin_user: User = Depends(get_current_admin)):
    """Sistem genel özet istatistiklerini getirir."""
    total_users = db.query(User).count()
    total_analyses = db.query(AnalysisLog).count()
    
    # Disk kullanımı
    try:
        data_dir = "data"
        total_size = 0
        if os.path.exists(data_dir):
            for dirpath, _, filenames in os.walk(data_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        disk_usage_mb = round(total_size / (1024 * 1024), 2)
    except:
        disk_usage_mb = 0.0

    return {
        "total_users": total_users,
        "total_analyses": total_analyses,
        "disk_usage_mb": disk_usage_mb,
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": psutil.virtual_memory().percent
    }
