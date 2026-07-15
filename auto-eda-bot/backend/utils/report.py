import os
import glob
from fpdf import FPDF
import datetime

class EDAReport(FPDF):
    def header(self):
        # Logo veya Başlık
        self.set_font('Arial', 'B', 15)
        self.set_text_color(123, 47, 247) # Mor tonu
        self.cell(0, 10, 'Auto-EDA Bot | Otonom Veri Analizi Raporu', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        # Sayfa Numarası
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(analysis_text: str, charts_dir: str, output_path: str):
    """
    Analiz metni ve klasördeki grafikleri birleştirerek PDF oluşturur.
    """
    pdf = EDAReport()
    pdf.add_page()

    # Tarih bilgisi
    pdf.set_font('Arial', 'I', 10)
    pdf.set_text_color(100)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf.cell(0, 10, f'Rapor Tarihi: {now}', 0, 1, 'R')
    pdf.ln(5)

    # Analiz Metni
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, 'Ajanin Analiz Yorumu:', 0, 1)
    
    pdf.set_font('Arial', '', 11)
    # FPDF temel ascii haricinde tr karakterlerde sorun yapabilir, 
    # şimdilik ascii'ye encode/decode ederek güvenli hale getiriyoruz
    safe_text = analysis_text.encode('ascii', 'replace').decode('ascii')
    pdf.multi_cell(0, 7, safe_text)
    pdf.ln(10)

    # Grafikler
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Uretilen Grafikler:', 0, 1)
    pdf.ln(5)

    png_files = glob.glob(os.path.join(charts_dir, "*.png"))
    for chart in png_files:
        # Sayfaya sığdırma mantığı (Genişlik 180, Yükseklik orantılı)
        pdf.image(chart, x=15, w=180)
        pdf.ln(5)
        pdf.set_font('Arial', 'I', 9)
        pdf.cell(0, 5, os.path.basename(chart), 0, 1, 'C')
        pdf.ln(10)

    pdf.output(output_path)
    return output_path
