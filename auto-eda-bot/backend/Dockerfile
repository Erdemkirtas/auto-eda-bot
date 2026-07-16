# ==============================================================================
# Backend Dockerfile — FastAPI + LangChain Agent
# ==============================================================================
# Python 3.11 slim tabanlı, hafif üretim imajı.
# Kullanım:
#   docker build -t auto-eda-backend ./backend
#   docker run -p 8000:8000 auto-eda-backend

FROM python:3.11-slim

# Çalışma dizini
WORKDIR /app

# Sistem bağımlılıkları (matplotlib, fontlar vs.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Gereksinimleri önce kopyala (Docker cache optimizasyonu)
COPY ../requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Uygulama kodunu kopyala
COPY . .

# data ve output dizinlerini oluştur
RUN mkdir -p /app/../data /app/../output/charts /app/../output/logs

# Port aç
EXPOSE 8000

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Sunucuyu başlat
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
