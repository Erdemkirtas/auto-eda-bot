# ==============================================================================
# Frontend Dockerfile — React/Vite Multi-Stage Build
# ==============================================================================
# 1) Node.js ile build yap (npm run build)
# 2) Nginx ile statik dosyaları sun
# Kullanım:
#   docker build -t auto-eda-frontend ./frontend
#   docker run -p 80:80 auto-eda-frontend

# ---------- Build Aşaması ----------
FROM node:20-alpine AS builder

WORKDIR /app

# Paket dosyalarını önce kopyala (Docker cache optimizasyonu)
COPY package.json package-lock.json ./
RUN npm ci --silent

# Kaynak kodunu kopyala
COPY . .

# Üretim build'i oluştur
RUN npm run build

# ---------- Çalıştırma Aşaması ----------
FROM nginx:alpine

# Nginx konfigürasyonu — SPA routing desteği
RUN echo 'server { \
    listen 80; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    location /api/ { \
        proxy_pass http://backend:8000; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_buffering off; \
        proxy_cache off; \
    } \
    location /output/ { \
        proxy_pass http://backend:8000; \
    } \
}' > /etc/nginx/conf.d/default.conf

# Build çıktısını nginx'e kopyala
COPY --from=builder /app/dist /usr/share/nginx/html

# Port aç
EXPOSE 80

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
