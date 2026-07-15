"""
tools/file_io.py — Veri Dosyası Okuma ve Yazma Aracı
======================================================
Ajanın yerel dosya sistemindeki verileri güvenle okuyabilmesi 
ve analiz edebilmesi için kullanılan araçtır.
"""

import os
import pandas as pd
from typing import Optional, Dict, Any
from langchain.tools import BaseTool

def analyze_dataframe(df: pd.DataFrame) -> str:
    """Bir DataFrame'in kısa yapısal özetini çıkarır."""
    import io
    buffer = io.StringIO()
    df.info(buf=buffer)
    info_str = buffer.getvalue()
    
    # Boyutlar
    rows, cols = df.shape
    
    # Temel istatistikler (sayısal sütunlar için)
    numeric_summary = ""
    numeric_cols = df.select_dtypes(include='number').columns
    if len(numeric_cols) > 0:
        numeric_summary = "\n--- Sayısal Sütun İstatistikleri ---\n"
        numeric_summary += df[numeric_cols].describe().to_string()
        
    # Eksik veri özeti
    missing_data = df.isnull().sum()
    missing_data = missing_data[missing_data > 0]
    missing_summary = "\n--- Eksik Veri Özeti ---\n"
    if len(missing_data) > 0:
        missing_summary += missing_data.to_string()
    else:
        missing_summary += "Eksik veri bulunmuyor."

    return (
        f"Veri Seti Yüklendi! Toplam Satır: {rows}, Sütun: {cols}\n"
        f"\n--- Veri Yapısı (df.info) ---\n{info_str}"
        f"{missing_summary}"
        f"{numeric_summary}"
        f"\n\n--- İlk 3 Satır ---\n{df.head(3).to_string()}"
    )

def read_data_file(file_path: str) -> str:
    """
    Belirtilen yoldaki CSV veya Excel dosyasını okur ve özetini döndürür.
    """
    if not os.path.exists(file_path):
        return f"HATA: '{file_path}' bulunamadı. Lütfen dosya yolunu kontrol edin."
    
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == '.csv':
            df = pd.read_csv(file_path)
        elif ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path)
        else:
            return f"HATA: Desteklenmeyen dosya formatı '{ext}'. Sadece CSV ve Excel desteklenir."
        
        return analyze_dataframe(df)
    except Exception as e:
        return f"HATA: Dosya okunurken bir sorun oluştu: {str(e)}"

# ---------------------------------------------------------------------------
# LangChain Araç Tanımları
# ---------------------------------------------------------------------------

class DataLoadTool(BaseTool):
    """
    Veri yüklemek ve ilk keşif analizini (EDA) yapmak için kullanılan araç.
    """
    name: str = "load_data"
    description: str = (
        "Bir CSV veya Excel dosyasının yolunu alır. "
        "Dosyayı okur ve verinin yapısı (sütun tipleri, eksik veriler, özet istatistikler) "
        "hakkında kapsamlı bir rapor döndürür. Veriyi tanımak için her zaman ilk bunu kullan."
    )

    def _run(self, file_path: str) -> str:
        return read_data_file(file_path)

    async def _arun(self, file_path: str) -> str:
        return self._run(file_path)
