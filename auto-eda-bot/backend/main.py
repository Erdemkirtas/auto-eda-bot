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
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from agent.agent import create_eda_agent
from agent.callbacks import ThinkingStepsCallback
from utils.logger import get_logger

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
DATA_DIR = os.path.join(BASE_DIR, "data")
CHARTS_DIR = os.path.join(BASE_DIR, "output", "charts")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# Grafikleri frontend'e sunmak için statik dosya servisi
app.mount("/output/charts", StaticFiles(directory=CHARTS_DIR), name="charts")

# Ajanımızı başlat
eda_agent = create_eda_agent()

logger.info("Auto-EDA Bot API v2.0 başlatıldı")

# ---------------------------------------------------------------------------
# Uç Noktalar (Endpoints)
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "Auto-EDA Backend Çalışıyor", "version": "2.0.0"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """CSV veya Excel dosyası yükler."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".csv", ".xls", ".xlsx"]:
        raise HTTPException(status_code=400, detail="Sadece CSV ve Excel dosyaları desteklenir.")

    file_path = os.path.join(DATA_DIR, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Veri önizleme için Pandas ile ilk 5 satırı oku
        df = pd.read_csv(file_path) if ext == ".csv" else pd.read_excel(file_path)
        preview_html = df.head().to_html(classes="data-preview-table", index=False)
        columns = list(df.columns)
        
        logger.info(f"Dosya yüklendi: {file.filename} ({len(df)} satır, {len(columns)} sütun)")
        
        return {
            "success": True, 
            "file_name": file.filename,
            "columns": columns,
            "row_count": len(df),
            "preview_html": preview_html,
            "message": f"{file.filename} başarıyla yüklendi. Şimdi bana 'Bu veriyi analiz et' diyebilirsin."
        }
    except Exception as e:
        logger.error(f"Dosya yükleme hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dosya kaydedilirken hata oluştu: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Kullanıcının sorusunu alır, LangChain ajanına iletir ve sonucu döner.
    Düşünce adımlarını (callback) yakalar.
    Oturum bazlı hafıza desteği sağlar.
    """
    callback_handler = ThinkingStepsCallback()
    
    # Oturum kimliği (yoksa yeni oluştur)
    session_id = request.session_id or str(uuid.uuid4())
    
    logger.info(f"Chat isteği: session={session_id[:8]}... mesaj='{request.message[:50]}...'")
    
    # Eski grafikleri temizle ki yeni sorunun grafikleri ile karışmasın
    for f in glob.glob(os.path.join(CHARTS_DIR, "*.png")):
        try:
            os.remove(f)
        except:
            pass
    for f in glob.glob(os.path.join(CHARTS_DIR, "*.html")):
        try:
            os.remove(f)
        except:
            pass

    try:
        # Ajanı çalıştır (Callback handler + hafıza config)
        response = eda_agent.invoke(
            {"messages": [("user", request.message)]},
            config={
                "callbacks": [callback_handler],
                "configurable": {"thread_id": session_id}
            }
        )
        last_message = response["messages"][-1]
        reply = last_message.content if hasattr(last_message, "content") else "Üzgünüm, cevap üretemedim."
        
        # Üretilen grafikleri bul (PNG ve HTML ayrı)
        charts = []
        html_charts = []
        
        png_files = glob.glob(os.path.join(CHARTS_DIR, "*.png"))
        for p in png_files:
            charts.append(os.path.basename(p))
        
        html_files = glob.glob(os.path.join(CHARTS_DIR, "*.html"))
        for h in html_files:
            html_charts.append(os.path.basename(h))
            
        logger.info(f"Chat yanıtı: {len(charts)} PNG, {len(html_charts)} HTML grafik üretildi")
            
        return ChatResponse(
            reply=reply,
            charts=charts,
            html_charts=html_charts,
            steps=callback_handler.get_steps(),
            session_id=session_id,
            success=True
        )
    except Exception as e:
        logger.error(f"Ajan hatası: {str(e)}")
        return ChatResponse(
            reply=f"Ajan çalışırken hata oluştu: {str(e)}",
            charts=[],
            html_charts=[],
            steps=callback_handler.get_steps(),
            session_id=session_id,
            success=False
        )


# ---------------------------------------------------------------------------
# SSE Streaming Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Ajanın düşünce adımlarını Server-Sent Events (SSE) ile gerçek zamanlı stream eder.
    """
    session_id = request.session_id or str(uuid.uuid4())
    
    logger.info(f"Stream isteği: session={session_id[:8]}... mesaj='{request.message[:50]}...'")
    
    # Eski grafikleri temizle
    for f in glob.glob(os.path.join(CHARTS_DIR, "*.png")):
        try:
            os.remove(f)
        except:
            pass
    for f in glob.glob(os.path.join(CHARTS_DIR, "*.html")):
        try:
            os.remove(f)
        except:
            pass

    async def event_generator():
        try:
            # Başlangıç event'i
            yield f"data: {json.dumps({'type': 'start', 'session_id': session_id})}\n\n"
            
            final_reply = ""
            
            async for event in eda_agent.astream_events(
                {"messages": [("user", request.message)]},
                config={"configurable": {"thread_id": session_id}},
                version="v2"
            ):
                kind = event.get("event", "")
                
                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    tool_input = str(event.get("data", {}).get("input", ""))[:200]
                    step_data = {
                        "type": "step",
                        "step_type": "tool_start",
                        "tool": tool_name,
                        "detail": tool_input
                    }
                    yield f"data: {json.dumps(step_data)}\n\n"
                    
                elif kind == "on_tool_end":
                    output = str(event.get("data", {}).get("output", ""))[:300]
                    step_data = {
                        "type": "step",
                        "step_type": "tool_end",
                        "detail": output
                    }
                    yield f"data: {json.dumps(step_data)}\n\n"
                    
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        final_reply += token
                        yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            # Grafikleri bul
            charts = [os.path.basename(p) for p in glob.glob(os.path.join(CHARTS_DIR, "*.png"))]
            html_charts = [os.path.basename(h) for h in glob.glob(os.path.join(CHARTS_DIR, "*.html"))]
            
            # Son event
            yield f"data: {json.dumps({'type': 'done', 'reply': final_reply, 'charts': charts, 'html_charts': html_charts, 'session_id': session_id})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream hatası: {str(e)}")
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
async def download_report(text: str = "Analiz Raporu"):
    """Üretilen son grafikleri ve verilen metni PDF olarak indirir."""
    pdf_path = os.path.join(BASE_DIR, "output", "EDA_Raporu.pdf")
    try:
        generate_pdf_report(text, CHARTS_DIR, pdf_path)
        logger.info("PDF rapor oluşturuldu")
        return FileResponse(pdf_path, media_type='application/pdf', filename='EDA_Raporu.pdf')
    except Exception as e:
        logger.error(f"Rapor hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Rapor oluşturulamadı: {str(e)}")


# ---------------------------------------------------------------------------
# Web Scraping - URL'den Tablo Çekme
# ---------------------------------------------------------------------------

@app.post("/api/scrape")
async def scrape_url(request: ScrapeRequest):
    """Verilen URL'deki HTML tablolarını pandas ile çeker ve CSV olarak kaydeder."""
    try:
        tables = pd.read_html(request.url)
        if not tables:
            raise HTTPException(status_code=404, detail="Bu URL'de herhangi bir tablo bulunamadı.")
        
        # En büyük tabloyu seç (en çok satıra sahip olan)
        df = max(tables, key=len)
        
        # Dosya adı oluştur
        from urllib.parse import urlparse
        domain = urlparse(request.url).netloc.replace(".", "_")
        file_name = f"web_{domain}.csv"
        file_path = os.path.join(DATA_DIR, file_name)
        df.to_csv(file_path, index=False)
        
        preview_html = df.head().to_html(classes="data-preview-table", index=False)
        columns = list(df.columns)
        
        logger.info(f"Web scraping: {request.url} → {file_name} ({len(df)} satır)")
        
        return {
            "success": True,
            "file_name": file_name,
            "columns": columns,
            "row_count": len(df),
            "preview_html": preview_html,
            "message": f"URL'den {len(df)} satırlık tablo çekildi ve '{file_name}' olarak kaydedildi."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scraping hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Web scraping hatası: {str(e)}")


# ---------------------------------------------------------------------------
# Çoklu Dosya Yönetimi
# ---------------------------------------------------------------------------

@app.get("/api/files")
async def list_files():
    """data/ klasöründeki tüm veri dosyalarını listeler."""
    files = []
    for fname in os.listdir(DATA_DIR):
        fpath = os.path.join(DATA_DIR, fname)
        if os.path.isfile(fpath) and not fname.startswith("."):
            ext = os.path.splitext(fname)[1].lower()
            if ext in [".csv", ".xls", ".xlsx"]:
                size_bytes = os.path.getsize(fpath)
                # Satır sayısını da al
                try:
                    if ext == ".csv":
                        row_count = sum(1 for _ in open(fpath, encoding="utf-8")) - 1
                    else:
                        row_count = len(pd.read_excel(fpath))
                except:
                    row_count = -1
                
                files.append({
                    "name": fname,
                    "size_bytes": size_bytes,
                    "size_display": _format_size(size_bytes),
                    "row_count": row_count,
                    "extension": ext
                })
    
    return {"files": files}


@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """data/ klasöründen dosya siler."""
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    
    try:
        os.remove(file_path)
        logger.info(f"Dosya silindi: {filename}")
        return {"success": True, "message": f"'{filename}' silindi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya silinirken hata: {str(e)}")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """data/ klasöründeki bir dosyayı indirir."""
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    return FileResponse(file_path, media_type='application/octet-stream', filename=filename)


# ---------------------------------------------------------------------------
# Örnek Veri Setleri
# ---------------------------------------------------------------------------

@app.post("/api/sample-data")
async def load_sample_data(request: SampleDataRequest):
    """Hazır örnek veri setlerini yükler."""
    dataset = request.dataset.lower()
    
    DATASETS = {
        "iris": ("Iris Çiçek Verisi", _generate_iris),
        "tips": ("Restoran Bahşiş Verisi", _generate_tips),
        "titanic": ("Titanic Yolcu Verisi", _generate_titanic),
    }
    
    if dataset not in DATASETS:
        raise HTTPException(
            status_code=400, 
            detail=f"Geçersiz veri seti. Desteklenenler: {', '.join(DATASETS.keys())}"
        )
    
    display_name, generator_fn = DATASETS[dataset]
    
    try:
        df = generator_fn()
        file_name = f"ornek_{dataset}.csv"
        file_path = os.path.join(DATA_DIR, file_name)
        df.to_csv(file_path, index=False)
        
        preview_html = df.head().to_html(classes="data-preview-table", index=False)
        columns = list(df.columns)
        
        logger.info(f"Örnek veri yüklendi: {display_name} ({len(df)} satır)")
        
        return {
            "success": True,
            "file_name": file_name,
            "columns": columns,
            "row_count": len(df),
            "preview_html": preview_html,
            "message": f"'{display_name}' ({len(df)} satır) yüklendi. Şimdi analiz edebilirsin!"
        }
    except Exception as e:
        logger.error(f"Örnek veri hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Veri seti oluşturulamadı: {str(e)}")


# Oturum sıfırlama
@app.post("/api/reset")
async def reset_session():
    """Sohbet geçmişini ve grafikleri sıfırlar."""
    # Grafikleri temizle
    for f in glob.glob(os.path.join(CHARTS_DIR, "*")):
        if not f.endswith(".gitkeep"):
            try:
                os.remove(f)
            except:
                pass
    logger.info("Oturum sıfırlandı")
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
