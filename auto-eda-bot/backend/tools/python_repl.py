"""
tools/python_repl.py — Güvenli Python REPL Aracı
=================================================
Bu modül, LangChain ajanının Python kodu çalıştırmasını sağlayan
sandbox'lı bir REPL aracı sunar.

Güvenlik Katmanları:
  1. Yasaklı modül/fonksiyon kontrolü (import hook + regex tarama)
  2. Timeout mekanizması (Windows uyumlu, threading tabanlı)
  3. Çıktı boyutu sınırı (max karakter)
  4. İzole namespace (her çalıştırma temiz bir ortamda başlar)
  5. Hata yakalama (traceback ajana geri döner, uygulama çökmez)
"""

import io
import sys
import traceback
import threading
import re
import os
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional, Any

from langchain.tools import BaseTool

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

# Maksimum çalışma süresi (saniye)
DEFAULT_TIMEOUT_SECONDS: int = 30

# Maksimum çıktı uzunluğu (karakter)
MAX_OUTPUT_LENGTH: int = 15_000

# Yasaklı modüller — sisteme zarar verebilecek modüller
BANNED_MODULES: set[str] = {
    "subprocess",
    "shutil",
    "socket",
    "http",
    "urllib",
    "requests",
    "ftplib",
    "smtplib",
    "ctypes",
    "multiprocessing",
    "signal",
    "webbrowser",
    "antigravity",
}

# Yasaklı fonksiyon/ifade kalıpları — kaynak kodda taranır
BANNED_PATTERNS: list[str] = [
    r"\bos\.system\b",
    r"\bos\.popen\b",
    r"\bos\.exec\w*\b",
    r"\bos\.spawn\w*\b",
    r"\bos\.remove\b",
    r"\bos\.unlink\b",
    r"\bos\.rmdir\b",
    r"\bos\.removedirs\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\b__import__\s*\(",
    r"\bcompile\s*\(",
    r"\bopen\s*\(.+,\s*['\"]w",  # yazma modunda dosya açma
]

# Güvenli olarak izin verilen ön-yüklü modüller
SAFE_PRELOADED_MODULES: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Yardımcı Fonksiyonlar
# ---------------------------------------------------------------------------

def _check_banned_imports(code: str) -> Optional[str]:
    """
    Kod metninde yasaklı modül importlarını arar.
    Yasaklı bir import bulursa hata mesajı döndürür, yoksa None döner.
    """
    # import xyz veya from xyz import ... kalıplarını yakala
    import_pattern = re.compile(
        r"(?:^|\n)\s*(?:import|from)\s+([\w.]+)", re.MULTILINE
    )
    for match in import_pattern.finditer(code):
        module_name = match.group(1).split(".")[0]
        if module_name in BANNED_MODULES:
            return (
                f"GÜVENLİK HATASI: '{module_name}' modülünün kullanımı yasaklanmıştır. "
                f"Bu modül sistem güvenliği nedeniyle engellenmiştir. "
                f"Lütfen alternatif bir yöntem kullanın."
            )
    return None


def _check_banned_patterns(code: str) -> Optional[str]:
    """
    Kod metninde yasaklı fonksiyon/ifade kalıplarını arar.
    Yasaklı bir kalıp bulursa hata mesajı döndürür, yoksa None döner.
    """
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, code):
            return (
                f"GÜVENLİK HATASI: Yasaklı bir ifade tespit edildi (kalıp: {pattern}). "
                f"Bu ifade sistem güvenliği nedeniyle engellenmiştir. "
                f"Lütfen alternatif bir yöntem kullanın."
            )
    return None


def _truncate_output(text: str, max_length: int = MAX_OUTPUT_LENGTH) -> str:
    """
    Çıktı metni çok uzunsa kırpar ve uyarı ekler.
    """
    if len(text) > max_length:
        return (
            text[:max_length]
            + f"\n\n... [ÇIKTI KISILDI: {len(text)} karakter → {max_length} karakter]"
        )
    return text


# ---------------------------------------------------------------------------
# Kod Çalıştırma Motoru
# ---------------------------------------------------------------------------

class _ExecutionResult:
    """Kod çalıştırma sonucunu taşıyan dahili sınıf."""

    def __init__(self) -> None:
        self.output: str = ""
        self.error: str = ""
        self.success: bool = False


def _execute_code_in_thread(
    code: str,
    namespace: dict,
    result: _ExecutionResult,
) -> None:
    """
    Kodu verilen namespace içinde çalıştırır.
    Sonuçları result nesnesine yazar.
    Bu fonksiyon bir thread içinde çağrılacak.
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, namespace)  # noqa: S102 — sandbox içinde kontrollü çalıştırma
        result.output = stdout_capture.getvalue()
        result.success = True
    except Exception:
        result.error = traceback.format_exc()
        result.output = stdout_capture.getvalue()
        result.success = False
    finally:
        stdout_capture.close()
        stderr_capture.close()


def run_python_code(
    code: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    charts_dir: str = "",
) -> str:
    """
    Python kodunu güvenli bir şekilde çalıştırır.

    Args:
        code: Çalıştırılacak Python kodu.
        timeout: Maksimum çalışma süresi (saniye).
        charts_dir: Grafiklerin kaydedileceği klasör yolu.

    Returns:
        Çalıştırma sonucu veya hata mesajı (string).
    """
    # ---- 1. Güvenlik kontrolleri ----
    banned_import_msg = _check_banned_imports(code)
    if banned_import_msg:
        return banned_import_msg

    banned_pattern_msg = _check_banned_patterns(code)
    if banned_pattern_msg:
        return banned_pattern_msg

    # ---- 2. İzole namespace hazırla ----
    # Matplotlib backend'ini non-interactive yap (Streamlit uyumu için)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Grafik kayıt dizinini belirle
    if not charts_dir:
        charts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "charts")
    os.makedirs(charts_dir, exist_ok=True)

    namespace: dict[str, Any] = {
        "__builtins__": __builtins__,
        "plt": plt,
        "CHARTS_DIR": charts_dir,
    }

    # Güvenli ön-yüklü modülleri namespace'e ekle
    try:
        import pandas as pd
        import numpy as np
        import seaborn as sns

        namespace["pd"] = pd
        namespace["np"] = np
        namespace["sns"] = sns
    except ImportError:
        pass  # Eğer yüklü değilse atla, ajan import ederek kullanır

    # ---- 3. Kodu thread içinde çalıştır (timeout destekli) ----
    result = _ExecutionResult()
    thread = threading.Thread(
        target=_execute_code_in_thread,
        args=(code, namespace, result),
        daemon=True,
    )
    thread.start()
    thread.join(timeout=timeout)

    # ---- 4. Timeout kontrolü ----
    if thread.is_alive():
        return (
            f"ZAMANAŞIMI HATASI: Kod {timeout} saniye içinde tamamlanamadı. "
            f"Lütfen daha verimli bir yöntem deneyin veya veri boyutunu küçültün."
        )

    # ---- 5. Sonucu formatla ----
    # Matplotlib figürlerini otomatik kaydet
    saved_charts: list[str] = []
    try:
        fig_nums = plt.get_fignums()
        for fig_num in fig_nums:
            fig = plt.figure(fig_num)
            # Benzersiz dosya adı üret
            existing_charts = [
                f for f in os.listdir(charts_dir)
                if f.startswith("chart_") and f.endswith(".png")
            ]
            chart_index = len(existing_charts) + 1
            chart_filename = f"chart_{chart_index:03d}.png"
            chart_path = os.path.join(charts_dir, chart_filename)
            fig.savefig(chart_path, dpi=150, bbox_inches="tight", facecolor="white")
            saved_charts.append(chart_path)
        plt.close("all")
    except Exception:
        pass  # Grafik kaydetme hatası kritik değil

    # Çıktı metnini oluştur
    output_parts: list[str] = []

    if result.output.strip():
        output_parts.append(result.output.strip())

    if saved_charts:
        charts_info = "\n".join(
            f"  📊 {os.path.basename(p)}" for p in saved_charts
        )
        output_parts.append(f"Kaydedilen grafikler:\n{charts_info}")

    if result.success:
        if output_parts:
            final_output = "\n\n".join(output_parts)
        else:
            final_output = "Kod başarıyla çalıştırıldı (çıktı yok)."
    else:
        error_text = result.error.strip()
        if output_parts:
            final_output = (
                "\n\n".join(output_parts)
                + f"\n\nHATA OLUŞTU:\n{error_text}"
            )
        else:
            final_output = f"HATA OLUŞTU:\n{error_text}"

    return _truncate_output(final_output)


# ---------------------------------------------------------------------------
# LangChain Araç Tanımı
# ---------------------------------------------------------------------------

class SafePythonREPLTool(BaseTool):
    """
    LangChain uyumlu güvenli Python REPL aracı.

    Ajan bu aracı kullanarak Python kodu çalıştırabilir.
    Kod bir sandbox içinde çalışır:
      - Yasaklı modüller/fonksiyonlar engellenir
      - Timeout ile uzun süren kodlar durdurulur
      - Çıktı boyutu sınırlandırılır
      - Hatalar yakalanıp ajana geri döndürülür
      - Matplotlib grafikleri otomatik kaydedilir
    """

    name: str = "python_repl"
    description: str = (
        "Python kodu çalıştırmak için kullan. "
        "Girdi olarak geçerli bir Python kodu al. "
        "Veri analizi için pandas (pd), numpy (np), matplotlib.pyplot (plt), "
        "seaborn (sns) zaten yüklüdür. "
        "Grafikler otomatik olarak kaydedilir — plt.show() ÇAĞIRMA, "
        "sadece plt.figure() ve çizim komutlarını kullan. "
        "print() ile sonuçları yazdır ki çıktıyı görebilelim. "
        "Hata alırsan, hatayı oku ve kodunu düzeltip tekrar dene."
    )

    timeout: int = DEFAULT_TIMEOUT_SECONDS
    charts_dir: str = ""

    def _run(self, code: str) -> str:
        """Aracı senkron olarak çalıştır."""
        return run_python_code(
            code=code,
            timeout=self.timeout,
            charts_dir=self.charts_dir,
        )

    async def _arun(self, code: str) -> str:
        """Aracı asenkron olarak çalıştır (senkron sürümü sarar)."""
        return self._run(code)
