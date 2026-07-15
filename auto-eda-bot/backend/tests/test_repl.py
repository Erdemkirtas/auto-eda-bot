import os
import sys

# Windows terminali için UTF-8 ayarı
sys.stdout.reconfigure(encoding='utf-8')

# tools klasörünü bulabilmek için yolu ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.python_repl import run_python_code

def test_repl():
    print("=== TEST 1: Basit Matematik ===")
    code = "print(2 + 2)"
    result = run_python_code(code)
    print("Sonuç:", result)
    assert result.strip() == "4", "Basit matematik testi başarısız!"
    print("✅ Başarılı\n")

    print("=== TEST 2: Yasaklı Modül (os.system) ===")
    code = "import os\nos.system('echo hacklanıyor')"
    result = run_python_code(code)
    print("Sonuç:", result)
    assert "GÜVENLİK HATASI" in result, "Yasaklı kalıp yakalanamadı!"
    print("✅ Başarılı\n")

    print("=== TEST 3: Yasaklı Import (subprocess) ===")
    code = "import subprocess\nsubprocess.run(['ls'])"
    result = run_python_code(code)
    print("Sonuç:", result)
    assert "GÜVENLİK HATASI" in result, "Yasaklı import yakalanamadı!"
    print("✅ Başarılı\n")

    print("=== TEST 4: Grafikler (Matplotlib) ===")
    code = '''
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
plt.figure()
plt.plot(x, np.sin(x))
plt.title("Test Grafiği")
print("Grafik çizildi.")
'''
    result = run_python_code(code)
    print("Sonuç:", result)
    assert "Grafik çizildi." in result, "Matplotlib kodu çalışmadı!"
    assert "Kaydedilen grafikler:" in result, "Grafik kaydedilemedi!"
    print("✅ Başarılı\n")
    
    print("=== TEST 5: Hata Yakalama (Traceback) ===")
    code = "print(1 / 0)"
    result = run_python_code(code)
    print("Sonuç:\n", result)
    assert "HATA OLUŞTU" in result and "ZeroDivisionError" in result, "Hata düzgün yakalanamadı!"
    print("✅ Başarılı\n")

if __name__ == "__main__":
    test_repl()
    print("🚀 TÜM TESTLER BAŞARIYLA GEÇTİ!")
