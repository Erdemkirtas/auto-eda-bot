"""
backend/utils/logger.py — Yapılandırılmış Loglama Modülü
=========================================================
Renkli konsol çıktısı + dosyaya yazma desteği.
Her endpoint'in request/response bilgilerini loglar.
"""

import logging
import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# Log Dosyası Dizini
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "output", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"eda_bot_{datetime.now().strftime('%Y%m%d')}.log")

# ---------------------------------------------------------------------------
# Renkli Formatter (Konsol için)
# ---------------------------------------------------------------------------

class ColoredFormatter(logging.Formatter):
    """ANSI renk kodları ile renkli konsol çıktısı."""
    
    COLORS = {
        "DEBUG":    "\033[36m",    # Cyan
        "INFO":     "\033[32m",    # Green
        "WARNING":  "\033[33m",    # Yellow
        "ERROR":    "\033[31m",    # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        record.name = f"{self.BOLD}{record.name}{self.RESET}"
        return super().format(record)


# ---------------------------------------------------------------------------
# Logger Fabrika Fonksiyonu
# ---------------------------------------------------------------------------

def get_logger(name: str = "auto-eda") -> logging.Logger:
    """
    İsimlendirilmiş bir logger döndürür.
    
    Args:
        name: Logger adı (varsayılan: 'auto-eda')
    
    Returns:
        Yapılandırılmış logging.Logger nesnesi
    """
    logger = logging.getLogger(name)
    
    # Logger zaten yapılandırılmışsa tekrar ekleme yapma
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # 1. Konsol Handler (Renkli)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = ColoredFormatter(
        fmt="%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)
    
    # 2. Dosya Handler (Detaylı)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
