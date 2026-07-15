"""
backend/main.py — FastAPI Sunucusu Giriş Noktası
==================================================
Kullanıcı arayüzünden gelen dosya yükleme ve sohbet (EDA)
isteklerini karşılayan API sunucusu.
"""

import os
import shutil
import glob
import pandas as pd
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.agent import create_eda_agent
from agent.callbacks import ThinkingStepsCallback

# ---------------------------------------------------------------------------
# Veri Modelleri (Pydantic)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    file_name: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    charts: List[str] = []
    steps: List[Dict[str, str]] = []
    success: bool = True

# ---------------------------------------------------------------------------
# FastAPI Uygulaması ve Ayarlar
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Auto-EDA Bot API",
    description="Otonom Veri Bilimcisi Ajanı için Backend API'si",
    version="1.0.0"
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

# ---------------------------------------------------------------------------
# Uç Noktalar (Endpoints)
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "Auto-EDA Backend Çalışıyor", "version": "1.0.0"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
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
        
        return {
            "success": True, 
            "file_name": file.filename,
            "columns": columns,
            "row_count": len(df),
            "preview_html": preview_html,
            "message": f"{file.filename} başarıyla yüklendi. Şimdi bana 'Bu veriyi analiz et' diyebilirsin."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dosya kaydedilirken hata oluştu: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Kullanıcının sorusunu alır, LangChain ajanına iletir ve sonucu döner.
    Düşünce adımlarını (callback) yakalar.
    """
    callback_handler = ThinkingStepsCallback()
    
    # Eski grafikleri temizle ki yeni sorunun grafikleri ile karışmasın
    for f in glob.glob(os.path.join(CHARTS_DIR, "*.png")):
        try:
            os.remove(f)
        except:
            pass

    try:
        # Ajanı çalıştır (Callback handler ile birlikte)
        response = eda_agent.invoke(
            {"messages": [("user", request.message)]},
            config={"callbacks": [callback_handler]}
        )
        last_message = response["messages"][-1]
        reply = last_message.content if hasattr(last_message, "content") else "Üzgünüm, cevap üretemedim."
        
        # Üretilen grafikleri bul
        charts = []
        png_files = glob.glob(os.path.join(CHARTS_DIR, "*.png"))
        for p in png_files:
            charts.append(os.path.basename(p))
            
        return ChatResponse(
            reply=reply,
            charts=charts,
            steps=callback_handler.get_steps(),
            success=True
        )
    except Exception as e:
        return ChatResponse(
            reply=f"Ajan çalışırken hata oluştu: {str(e)}",
            charts=[],
            steps=callback_handler.get_steps(),
            success=False
        )

from fastapi.responses import FileResponse
from utils.report import generate_pdf_report

@app.get("/api/report")
async def download_report(text: str = "Analiz Raporu"):
    """
    Üretilen son grafikleri ve verilen metni PDF olarak indirir.
    """
    pdf_path = os.path.join(BASE_DIR, "output", "EDA_Raporu.pdf")
    try:
        generate_pdf_report(text, CHARTS_DIR, pdf_path)
        return FileResponse(pdf_path, media_type='application/pdf', filename='EDA_Raporu.pdf')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rapor oluşturulamadı: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
