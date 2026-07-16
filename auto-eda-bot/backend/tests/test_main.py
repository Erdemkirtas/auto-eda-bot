"""
backend/tests/test_main.py — FastAPI API Testleri
==================================================
Backend'in temel uç noktalarını (endpoints) otomatik olarak test eder.
Test edilen senaryolar:
  - Sağlık kontrolü (health check)
  - Dosya yükleme (CSV)
  - Geçersiz dosya yükleme (reddetme)
  - Dosya listeleme
  - Dosya silme
  - Örnek veri seti yükleme
  - Chat endpoint (temel istek/yanıt yapısı)
  - Oturum sıfırlama

Çalıştırma:
    cd backend
    pytest tests/test_main.py -v
"""

import os
import sys
import io
import pytest

# Backend kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app, DATA_DIR
from auth import get_current_user
from models import User

client = TestClient(app)

# Testler için sahte kullanıcı (Mock User)
def override_get_current_user():
    return User(id=999, username="testuser", email="test@test.com", hashed_password="fake")

app.dependency_overrides[get_current_user] = override_get_current_user


# ===================================================================
# TEST 1: Sağlık Kontrolü (Health Check)
# ===================================================================

class TestHealthCheck:
    def test_root_returns_200(self):
        """Ana endpoint 200 dönmeli."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_status(self):
        """Yanıtta 'status' alanı olmalı."""
        response = client.get("/")
        data = response.json()
        assert "status" in data

    def test_root_returns_version(self):
        """Yanıtta version bilgisi olmalı."""
        response = client.get("/")
        data = response.json()
        assert "version" in data
        assert data["version"] == "2.0.0"


# ===================================================================
# TEST 2: Dosya Yükleme
# ===================================================================

class TestFileUpload:
    def test_upload_csv_success(self):
        """Geçerli bir CSV dosyası başarıyla yüklenmeli."""
        csv_content = "ad,yas,sehir\nAli,25,İstanbul\nAyşe,30,Ankara\nMehmet,22,İzmir"
        files = {"file": ("test_upload.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
        
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["file_name"] == "test_upload.csv"
        assert data["row_count"] == 3
        assert len(data["columns"]) == 3
        assert "ad" in data["columns"]
        assert "preview_html" in data
        
        # Temizle
        test_file = os.path.join(DATA_DIR, "test_upload.csv")
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_upload_invalid_extension(self):
        """Desteklenmeyen dosya uzantıları reddedilmeli (400)."""
        files = {"file": ("malware.exe", io.BytesIO(b"fake content"), "application/octet-stream")}
        
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400

    def test_upload_txt_rejected(self):
        """TXT dosyaları da reddedilmeli."""
        files = {"file": ("notes.txt", io.BytesIO(b"some text data"), "text/plain")}
        
        response = client.post("/api/upload", files=files)
        assert response.status_code == 400


# ===================================================================
# TEST 3: Dosya Listeleme ve Silme
# ===================================================================

class TestFileManagement:
    def test_list_files(self):
        """Dosya listeleme endpointi 200 dönmeli ve 'files' alanı içermeli."""
        response = client.get("/api/files")
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert isinstance(data["files"], list)

    def test_delete_nonexistent_file(self):
        """Var olmayan bir dosyayı silmeye çalışmak 404 dönmeli."""
        response = client.delete("/api/files/bu_dosya_yok.csv")
        assert response.status_code == 404

    def test_upload_then_list_then_delete(self):
        """Bir dosya yükle → listele (içinde olsun) → sil → tekrar listele (içinde olmasın)."""
        # Yükle
        csv = "x,y\n1,2\n3,4"
        files = {"file": ("lifecycle_test.csv", io.BytesIO(csv.encode()), "text/csv")}
        upload_res = client.post("/api/upload", files=files)
        assert upload_res.status_code == 200

        # Listele
        list_res = client.get("/api/files")
        file_names = [f["name"] for f in list_res.json()["files"]]
        assert "lifecycle_test.csv" in file_names

        # Sil
        delete_res = client.delete("/api/files/lifecycle_test.csv")
        assert delete_res.status_code == 200
        assert delete_res.json()["success"] is True

        # Tekrar listele — artık olmamalı
        list_res2 = client.get("/api/files")
        file_names2 = [f["name"] for f in list_res2.json()["files"]]
        assert "lifecycle_test.csv" not in file_names2


# ===================================================================
# TEST 4: Örnek Veri Setleri
# ===================================================================

class TestSampleData:
    def test_load_iris(self):
        """Iris örnek veri seti yüklenebilmeli."""
        response = client.post("/api/sample-data", json={"dataset": "iris"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["row_count"] > 100  # Iris 150 satır
        assert "preview_html" in data
        
        # Temizle
        test_file = os.path.join(DATA_DIR, "ornek_iris.csv")
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_load_invalid_dataset(self):
        """Geçersiz veri seti adı 400 dönmeli."""
        response = client.post("/api/sample-data", json={"dataset": "yok_boyle_veri"})
        assert response.status_code == 400


# ===================================================================
# TEST 5: Chat Endpoint (Yapısal Test)
# ===================================================================

class TestChat:
    def test_chat_returns_valid_structure(self):
        """Chat endpoint'i doğru yapıda yanıt dönmeli."""
        response = client.post("/api/chat", json={
            "message": "Merhaba",
            "file_name": None,
            "session_id": "test-session-001"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Yapı kontrolü
        assert "reply" in data
        assert "charts" in data
        assert "html_charts" in data
        assert "steps" in data
        assert "session_id" in data
        assert "success" in data
        assert isinstance(data["charts"], list)
        assert isinstance(data["html_charts"], list)

    def test_chat_preserves_session_id(self):
        """Verilen session_id yanıtta korunmalı."""
        sid = "my-unique-session-123"
        response = client.post("/api/chat", json={
            "message": "Test mesajı",
            "session_id": sid
        })
        data = response.json()
        assert data["session_id"] == sid


# ===================================================================
# TEST 6: Oturum Sıfırlama
# ===================================================================

class TestReset:
    def test_reset_returns_success(self):
        """Oturum sıfırlama başarılı olmalı."""
        response = client.post("/api/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


# ===================================================================
# TEST 7: Dosya İndirme
# ===================================================================

class TestDownload:
    def test_download_nonexistent_file(self):
        """Var olmayan dosya indirme 404 dönmeli."""
        response = client.get("/api/download/bu_dosya_yok.csv")
        assert response.status_code == 404

    def test_download_existing_file(self):
        """Mevcut dosya indirme çalışmalı."""
        # Önce dosya oluştur
        csv = "a,b\n1,2"
        files = {"file": ("download_test.csv", io.BytesIO(csv.encode()), "text/csv")}
        client.post("/api/upload", files=files)
        
        response = client.get("/api/download/download_test.csv")
        assert response.status_code == 200
        
        # Temizle
        test_file = os.path.join(DATA_DIR, "download_test.csv")
        if os.path.exists(test_file):
            os.remove(test_file)
