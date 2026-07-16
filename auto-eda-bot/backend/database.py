"""
backend/database.py — SQLAlchemy Veritabanı Yöneticisi
======================================================
Kullanıcılar ve diğer kalıcı veriler için SQLAlchemy
motorunu ve oturum (session) yapısını kurar.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from config import settings

# Veritabanı yolundaki klasörlerin var olduğundan emin ol
db_path = settings.app_db_path.replace("sqlite:///", "")
if db_path.startswith("./"):
    db_path = db_path[2:]
    
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
full_db_path = os.path.join(BASE_DIR, db_path)

os.makedirs(os.path.dirname(full_db_path), exist_ok=True)

# SQLite kullanıldığı için check_same_thread=False gerekir (FastAPI için)
engine = create_engine(
    f"sqlite:///{full_db_path}", connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI uç noktaları için Dependency olarak kullanılacak
    veritabanı oturum üreticisi.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
