"""
backend/config.py — Merkezi Konfigürasyon Yönetimi
====================================================
Pydantic Settings ile tüm .env ayarlarını tip kontrollü,
doğrulanmış ve tek merkezden yönetir.

Kullanım:
    from config import settings
    print(settings.llm_api_base)
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """
    Uygulama genelindeki tüm ayarlar.
    Değerler önce ortam değişkenlerinden, bulunamazsa .env dosyasından,
    o da yoksa varsayılan değerden alınır.
    """

    # ---- LLM Ayarları ----
    local_llm_api_base: str = Field(
        default="http://localhost:11434/v1",
        description="Yerel LLM API adresi (Ollama, Foundry Local vb.)"
    )
    local_llm_model: str = Field(
        default="llama3",
        description="Kullanılacak model adı"
    )
    local_llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="LLM sıcaklığı (0=tutarlı, 2=yaratıcı)"
    )

    # ---- Uygulama Ayarları ----
    backend_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Backend sunucu portu"
    )
    max_repl_timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Python REPL zaman aşımı (saniye)"
    )
    max_output_length: int = Field(
        default=15000,
        ge=1000,
        description="REPL çıktı karakter limiti"
    )

    # ---- Veritabanı ----
    memory_db_path: str = Field(
        default="data/memory.db",
        description="SQLite Langgraph hafıza veritabanı dosya yolu"
    )
    app_db_path: str = Field(
        default="sqlite:///./data/app.db",
        description="SQLAlchemy Ana uygulama veritabanı (Kullanıcılar vb.)"
    )

    # ---- Güvenlik (JWT Auth) ----
    secret_key: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7", # Dev için sabit
        description="JWT şifreleme anahtarı (Prod'da mutlaka değiştirilmeli!)"
    )
    algorithm: str = Field(default="HS256", description="JWT şifreleme algoritması")
    access_token_expire_minutes: int = Field(default=60 * 24 * 7, description="Token geçerlilik süresi (dakika)")

    # ---- Dizinler (göreli yollar, BASE_DIR'e göre hesaplanır) ----
    data_dir: str = Field(default="data", description="Veri dosyaları dizini")
    charts_dir: str = Field(default="output/charts", description="Grafik çıktı dizini")
    logs_dir: str = Field(default="output/logs", description="Log dosyaları dizini")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",           # .env'de fazladan değişken olursa hata verme
    }


# Tek bir global settings nesnesi — her yerde `from config import settings` ile kullanılır
settings = Settings()
