"""
backend/main.py — FastAPI Sunucusu Giriş Noktası
==================================================
Kullanıcı arayüzünden gelen dosya yükleme ve sohbet (EDA)
isteklerini karşılayan API sunucusu.

Özellikler:
  - Dosya yükleme (CSV/Excel)
  - Sohbet (ajan ile EDA) + hafıza desteği
  - SSE streaming
  - Web scraping
  - Çoklu dosya yönetimi
  - Örnek veri setleri
  - Plotly interaktif grafik desteği
  - PDF rapor indirme
  - Yapılandırılmış loglama
"""

import os
import shutil
import glob
import uuid
import json
import asyncio
import pandas as pd
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from agent.agent import create_eda_agent
from agent.callbacks import ThinkingStepsCallback
from utils.logger import get_logger
from config import settings

from database import engine, Base
from models import User
from auth import get_current_user
from routers import auth_router

# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = get_logger("api")

# ---------------------------------------------------------------------------
# Veri Modelleri (Pydantic)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    file_name: Optional[str] = None
    session_id: Optional[str] = None  # Hafıza için oturum kimliği

class ChatResponse(BaseModel):
    reply: str
    charts: List[str] = []
    html_charts: List[str] = []  # Plotly interaktif HTML grafikler
    steps: List[Dict[str, str]] = []
    session_id: str = ""
    success: bool = True

class ScrapeRequest(BaseModel):
    url: str

class SampleDataRequest(BaseModel):
    dataset: str  # "iris", "titanic", "tips", "penguins"

# ---------------------------------------------------------------------------
# FastAPI Uygulaması ve Ayarlar
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Auto-EDA Bot API",
    description="Otonom Veri Bilimcisi Ajanı için Backend API'si",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, settings.data_dir)
CHARTS_DIR = os.path.join(BASE_DIR, settings.charts_dir)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# Grafikleri frontend'e sunmak için statik dosya servisi
app.mount("/output/charts", StaticFiles(directory=CHARTS_DIR), name="charts")

# Ajanımızı başlat
eda_agent = create_eda_agent()

# Auth router'ı ekle
app.include_router(auth_router.router)

logger.info("Auto-EDA Bot API v2.0 (Multi-Tenant) başlatıldı")

# ---------------------------------------------------------------------------
# Yardımcı Dizin Fonksiyonu (Kullanıcıya Özel)
# ---------------------------------------------------------------------------
def get_user_dirs(user_id: int):
    """Kullanıcıya özel veri ve grafik dizinlerini döner, yoksa oluşturur."""
    user_data_dir = os.path.join(DATA_DIR, str(user_id))
    user_charts_dir = os.path.join(CHARTS_DIR, str(user_id))
    os.makedirs(user_data_dir, exist_ok=True)
    os.makedirs(user_charts_dir, exist_ok=True)
    return user_data_dir, user_charts_dir

# ---------------------------------------------------------------------------
# Uç Noktalar (Endpoints)
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "Auto-EDA Backend Çalışıyor", "version": "2.0.0"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """Kullanıcının kendi dizinine CSV veya Excel dosyası yükler."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".csv", ".xls", ".xlsx"]:
        raise HTTPException(status_code=400, detail="Sadece CSV ve Excel dosyaları desteklenir.")

    user_data_dir, _ = get_user_dirs(user.id)
    file_path = os.path.join(user_data_dir, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Veri önizleme için Pandas ile ilk 5 satırı oku
        df = pd.read_csv(file_path) if ext == ".csv" else pd.read_excel(file_path)
        preview_html = df.head().to_html(classes="data-preview-table", index=False)
        columns = list(df.columns)
        
        logger.info(f"User {user.username} dosya yükledi: {file.filename}")
        
        return {
            "success": True, 
            "file_name": file.filename,
            "columns": columns,
            "row_count": len(df),
            "preview_html": preview_html,
            "message": f"{file.filename} başarıyla yüklendi."
        }
    except Exception as e:
        logger.error(f"Dosya yükleme hatası ({user.username}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dosya kaydedilirken hata oluştu: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest, user: User = Depends(get_current_user)):
    """
    Kullanıcının sorusunu alır, LangChain ajanına iletir ve sonucu döner.
    Düşünce adımlarını (callback) yakalar.
    Oturum bazlı hafıza desteği sağlar.
    """
    callback_handler = ThinkingStepsCallback()
    
    # Oturum kimliği izolasyonu (Kullanıcı başkasının IDsini tahmin etse bile kendi alanı)
    base_session = request.session_id or str(uuid.uuid4())
    secure_session_id = f"user_{user.id}_session_{base_session}"
    
    logger.info(f"Chat ({user.username}): session={base_session[:8]}... mesaj='{request.message[:50]}...'")
    
    user_data_dir, user_charts_dir = get_user_dirs(user.id)
    
    # Eski grafikleri temizle (sadece bu kullanıcının grafiklerini)
    for f in glob.glob(os.path.join(user_charts_dir, "*.png")):
        try: os.remove(f)
        except: pass
    for f in glob.glob(os.path.join(user_charts_dir, "*.html")):
        try: os.remove(f)
        except: pass

    try:
        # Ajanı çalıştırırken kullanıcının kendi dizininde çalışmasını sağlamak için
        # Python REPL'da os.chdir yapmıyoruz (çünkü asyncio), ama Tool'ları izole edeceğiz.
        # Şimdilik REPL, absolute path ile user_data_dir'i kullansın diye mesaja path ekleyebiliriz.
        # Daha temizi: LangChain config'e user_id geçmek ama karmaşık olmasın diye
        # mesajın sonuna gizli context ekleyebiliriz.
        context_msg = f"{request.message}\n[SİSTEM NOTU: Çalışma dizinin: '{user_data_dir}', Grafikleri kaydetme dizinin: '{user_charts_dir}']"
        
        response = eda_agent.invoke(
            {"messages": [("user", context_msg)]},
            config={
                "callbacks": [callback_handler],
                "configurable": {"thread_id": secure_session_id}
            }
        )
        last_message = response["messages"][-1]
        reply = last_message.content if hasattr(last_message, "content") else "Üzgünüm, cevap üretemedim."
        
        # Üretilen grafikleri bul (Kullanıcının klasöründen)
        charts = [f"{user.id}/{os.path.basename(p)}" for p in glob.glob(os.path.join(user_charts_dir, "*.png"))]
        html_charts = [f"{user.id}/{os.path.basename(h)}" for h in glob.glob(os.path.join(user_charts_dir, "*.html"))]
            
        logger.info(f"Chat yanıtı ({user.username}): {len(charts)} PNG, {len(html_charts)} HTML")
            
        return ChatResponse(
            reply=reply,
            charts=charts,
            html_charts=html_charts,
            steps=callback_handler.get_steps(),
            session_id=base_session,
            success=True
        )
    except Exception as e:
        logger.error(f"Ajan hatası: {str(e)}")
        return ChatResponse(
            reply=f"Ajan çalışırken hata oluştu: {str(e)}",
            charts=[],
            html_charts=[],
            steps=callback_handler.get_steps(),
            session_id=base_session,
            success=False
        )


# ---------------------------------------------------------------------------
# SSE Streaming Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, user: User = Depends(get_current_user)):
    """Ajanın düşünce adımlarını SSE ile gerçek zamanlı stream eder."""
    base_session = request.session_id or str(uuid.uuid4())
    secure_session_id = f"user_{user.id}_session_{base_session}"
    
    logger.info(f"Stream ({user.username}): session={base_session[:8]}... mesaj='{request.message[:50]}...'")
    
    user_data_dir, user_charts_dir = get_user_dirs(user.id)
    
    for f in glob.glob(os.path.join(user_charts_dir, "*.png")):
        try: os.remove(f)
        except: pass
    for f in glob.glob(os.path.join(user_charts_dir, "*.html")):
        try: os.remove(f)
        except: pass

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'start', 'session_id': base_session})}\n\n"
            final_reply = ""
            
            context_msg = f"{request.message}\n[SİSTEM NOTU: Çalışma dizinin: '{user_data_dir}', Grafikleri kaydetme dizinin: '{user_charts_dir}']"
            
            async for event in eda_agent.astream_events(
                {"messages": [("user", context_msg)]},
                config={"configurable": {"thread_id": secure_session_id}},
                version="v2"
            ):
                kind = event.get("event", "")
                
                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = str(event.get("data", {}).get("input", ""))[:200]
                    yield f"data: {json.dumps({'type': 'step', 'step_type': 'tool_start', 'tool': tool_name, 'detail': tool_input})}\n\n"
                    
                elif kind == "on_tool_end":
                    output = str(event.get("data", {}).get("output", ""))[:300]
                    yield f"data: {json.dumps({'type': 'step', 'step_type': 'tool_end', 'detail': output})}\n\n"
                    
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        final_reply += token
                        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            # Grafikleri kullanıcı klasörüne göre formatla
            charts = [f"{user.id}/{os.path.basename(p)}" for p in glob.glob(os.path.join(user_charts_dir, "*.png"))]
            html_charts = [f"{user.id}/{os.path.basename(h)}" for h in glob.glob(os.path.join(user_charts_dir, "*.html"))]
            
            yield f"data: {json.dumps({'type': 'done', 'reply': final_reply, 'charts': charts, 'html_charts': html_charts, 'session_id': base_session})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream hatası ({user.username}): {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ---------------------------------------------------------------------------
# PDF Rapor İndirme
# ---------------------------------------------------------------------------

from utils.report import generate_pdf_report

@app.get("/api/report")
async def download_report(text: str = "Analiz Raporu", user: User = Depends(get_current_user)):
    """Kullanıcının ürettiği grafikleri PDF yapar."""
    _, user_charts_dir = get_user_dirs(user.id)
    pdf_path = os.path.join(BASE_DIR, "output", f"EDA_Raporu_{user.id}.pdf")
    try:
        generate_pdf_report(text, user_charts_dir, pdf_path)
        return FileResponse(pdf_path, media_type='application/pdf', filename='EDA_Raporu.pdf')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rapor oluşturulamadı: {str(e)}")


# ---------------------------------------------------------------------------
# Web Scraping - URL'den Tablo Çekme
# ---------------------------------------------------------------------------

@app.post("/api/scrape")
async def scrape_url(request: ScrapeRequest, user: User = Depends(get_current_user)):
    try:
        tables = pd.read_html(request.url)
        if not tables:
            raise HTTPException(status_code=404, detail="Tablo bulunamadı.")
        
        df = max(tables, key=len)
        from urllib.parse import urlparse
        domain = urlparse(request.url).netloc.replace(".", "_")
        file_name = f"web_{domain}.csv"
        
        user_data_dir, _ = get_user_dirs(user.id)
        file_path = os.path.join(user_data_dir, file_name)
        df.to_csv(file_path, index=False)
        
        preview_html = df.head().to_html(classes="data-preview-table", index=False)
        return {
            "success": True, "file_name": file_name, "columns": list(df.columns),
            "row_count": len(df), "preview_html": preview_html
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Çoklu Dosya Yönetimi (Kullanıcıya İzole)
# ---------------------------------------------------------------------------

@app.get("/api/files")
async def list_files(user: User = Depends(get_current_user)):
    user_data_dir, _ = get_user_dirs(user.id)
    files = []
    for fname in os.listdir(user_data_dir):
        fpath = os.path.join(user_data_dir, fname)
        if os.path.isfile(fpath) and not fname.startswith("."):
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".csv", ".xls", ".xlsx"]:
                size_bytes = os.path.getsize(fpath)
                try:
                    if ext == ".csv": row_count = sum(1 for _ in open(fpath, encoding="utf-8")) - 1
                    else: row_count = len(pd.read_excel(fpath))
                except: row_count = -1
                
                files.append({
                    "name": fname, "size_bytes": size_bytes,
                    "size_display": _format_size(size_bytes), "row_count": row_count, "extension": ext
                })
    return {"files": files}


@app.delete("/api/files/{filename}")
async def delete_file(filename: str, user: User = Depends(get_current_user)):
    user_data_dir, _ = get_user_dirs(user.id)
    file_path = os.path.join(user_data_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    os.remove(file_path)
    return {"success": True, "message": f"'{filename}' silindi."}


@app.get("/api/download/{filename}")
async def download_file(filename: str, user: User = Depends(get_current_user)):
    user_data_dir, _ = get_user_dirs(user.id)
    file_path = os.path.join(user_data_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    return FileResponse(file_path, media_type='application/octet-stream', filename=filename)


# ---------------------------------------------------------------------------
# Örnek Veri Setleri
# ---------------------------------------------------------------------------

@app.post("/api/sample-data")
async def load_sample_data(request: SampleDataRequest, user: User = Depends(get_current_user)):
    dataset = request.dataset.lower()
    DATASETS = {
        "iris": ("Iris Çiçek Verisi", _generate_iris),
        "tips": ("Restoran Bahşiş Verisi", _generate_tips),
        "titanic": ("Titanic Yolcu Verisi", _generate_titanic),
    }
    if dataset not in DATASETS:
        raise HTTPException(status_code=400, detail="Geçersiz veri seti.")
    
    display_name, generator_fn = DATASETS[dataset]
    try:
        df = generator_fn()
        file_name = f"ornek_{dataset}.csv"
        user_data_dir, _ = get_user_dirs(user.id)
        file_path = os.path.join(user_data_dir, file_name)
        df.to_csv(file_path, index=False)
        
        preview_html = df.head().to_html(classes="data-preview-table", index=False)
        return {
            "success": True, "file_name": file_name, "columns": list(df.columns),
            "row_count": len(df), "preview_html": preview_html
        }
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset")
async def reset_session(user: User = Depends(get_current_user)):
    """Kullanıcının grafiklerini temizler."""
    _, user_charts_dir = get_user_dirs(user.id)
    for f in glob.glob(os.path.join(user_charts_dir, "*")):
        try: os.remove(f)
        except: pass
    return {"success": True, "message": "Oturum sıfırlandı."}


# ---------------------------------------------------------------------------
# Yardımcı Fonksiyonlar
# ---------------------------------------------------------------------------

def _format_size(size_bytes: int) -> str:
    """Byte'ı okunabilir formata çevirir."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _generate_iris() -> pd.DataFrame:
    """Iris veri setini oluşturur."""
    try:
        from sklearn.datasets import load_iris
        data = load_iris()
        df = pd.DataFrame(data.data, columns=data.feature_names)
        df["species"] = [data.target_names[t] for t in data.target]
        return df
    except ImportError:
        import seaborn as sns
        return sns.load_dataset("iris")


def _generate_tips() -> pd.DataFrame:
    """Tips veri setini oluşturur."""
    import seaborn as sns
    return sns.load_dataset("tips")


def _generate_titanic() -> pd.DataFrame:
    """Titanic veri setini oluşturur."""
    import seaborn as sns
    return sns.load_dataset("titanic")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.backend_port, reload=True)
