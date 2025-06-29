import json
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import io

# Ana dizin yolunu belirle
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # Türkçe karakter desteği için font ekleme
        self.add_font('DejaVu', '', 'static/fonts/DejaVuSansCondensed.ttf', uni=True)
        self.add_font('DejaVu', 'B', 'static/fonts/DejaVuSansCondensed-Bold.ttf', uni=True)

class PerformansRaporu:
    def __init__(self):
        self.veri_klasoru = os.path.join(ROOT_DIR, 'veri')
        self.rapor_klasoru = os.path.join(ROOT_DIR, 'static', 'raporlar')
        os.makedirs(self.rapor_klasoru, exist_ok=True)
        # Font klasörünü oluştur
        self.font_klasoru = os.path.join(ROOT_DIR, 'static', 'fonts')
        os.makedirs(self.font_klasoru, exist_ok=True)
    
    def _veri_yukle(self) -> Dict:
        """Gerekli verileri yükle"""
        try:
            # İş listesi verilerini yükle
            with open(os.path.join(self.veri_klasoru, 'is_listesi.json'), 'r', encoding='utf-8') as f:
                is_listesi = json.load(f)
            
            # Monte Carlo sonuçlarını yükle
            with open(os.path.join(self.veri_klasoru, 'monte_carlo_sonuclari.json'), 'r', encoding='utf-8') as f:
                monte_carlo = json.load(f)
            
            return {
                'is_listesi': is_listesi,
                'monte_carlo': monte_carlo
            }
        except Exception as e:
            print(f"Veri yükleme hatası: {str(e)}")
            return {}

    def haftalik_performans_raporu(self) -> str:
        """Haftalık performans raporu oluştur"""
        veriler = self._veri_yukle()
        if not veriler:
            return None
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 16)
        
        # Başlık
        pdf.cell(190, 10, 'Haftalık Performans Raporu', 0, 1, 'C')
        pdf.set_font('DejaVu', '', 12)
        pdf.cell(190, 10, f'Oluşturma Tarihi: {datetime.now().strftime("%d.%m.%Y")}', 0, 1, 'C')
        pdf.ln(10)
        
        # Monte Carlo sonuçlarını analiz et
        if 'monte_carlo' in veriler and 'calisanlar' in veriler['monte_carlo']:
            pdf.set_font('DejaVu', 'B', 14)
            pdf.cell(190, 10, 'Çalışan Performans Özeti', 0, 1, 'L')
            pdf.set_font('DejaVu', '', 12)
            
            for calisan, bilgi in veriler['monte_carlo']['calisanlar'].items():
                pdf.cell(190, 8, f'Çalışan: {calisan}', 0, 1, 'L')
                pdf.cell(190, 6, f'Ortalama Performans: %{bilgi["ortalama_performans"]*100:.1f}', 0, 1, 'L')
                pdf.cell(190, 6, f'Risk Skoru: %{bilgi["risk_skoru"]*100:.1f}', 0, 1, 'L')
                pdf.cell(190, 6, f'Gecikme Olasılığı: %{bilgi["gecikme_olasiligi"]*100:.1f}', 0, 1, 'L')
                pdf.ln(5)
        
        # İş tamamlanma durumları
        if 'is_listesi' in veriler:
            pdf.add_page()
            pdf.set_font('DejaVu', 'B', 14)
            pdf.cell(190, 10, 'İş Tamamlanma Durumları', 0, 1, 'L')
            pdf.set_font('DejaVu', '', 12)
            
            tamamlanan = len([is_ for is_ in veriler['is_listesi'] if is_['durum'] == 'tamamlandi'])
            devam_eden = len([is_ for is_ in veriler['is_listesi'] if is_['durum'] == 'devam_ediyor'])
            bekleyen = len([is_ for is_ in veriler['is_listesi'] if is_['durum'] == 'beklemede'])
            
            pdf.cell(190, 8, f'Tamamlanan İş Sayısı: {tamamlanan}', 0, 1, 'L')
            pdf.cell(190, 8, f'Devam Eden İş Sayısı: {devam_eden}', 0, 1, 'L')
            pdf.cell(190, 8, f'Bekleyen İş Sayısı: {bekleyen}', 0, 1, 'L')
        
        # Raporu kaydet
        rapor_adi = f'haftalik_performans_raporu_{datetime.now().strftime("%Y%m%d")}.pdf'
        rapor_yolu = os.path.join(self.rapor_klasoru, rapor_adi)
        pdf.output(rapor_yolu)
        
        return rapor_adi

    def personel_performans_raporu(self, calisan_adi: str) -> str:
        """Belirli bir çalışan için performans raporu oluştur"""
        veriler = self._veri_yukle()
        if not veriler or 'monte_carlo' not in veriler:
            return None
        
        monte_carlo = veriler['monte_carlo']
        if 'calisanlar' not in monte_carlo or calisan_adi not in monte_carlo['calisanlar']:
            return None
        
        calisan_bilgi = monte_carlo['calisanlar'][calisan_adi]
        
        pdf = PDF()
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 16)
        
        # Başlık
        pdf.cell(190, 10, f'Personel Performans Raporu - {calisan_adi}', 0, 1, 'C')
        pdf.set_font('DejaVu', '', 12)
        pdf.cell(190, 10, f'Oluşturma Tarihi: {datetime.now().strftime("%d.%m.%Y")}', 0, 1, 'C')
        pdf.ln(10)
        
        # Genel performans metrikleri
        pdf.set_font('DejaVu', 'B', 14)
        pdf.cell(190, 10, 'Genel Performans Metrikleri', 0, 1, 'L')
        pdf.set_font('DejaVu', '', 12)
        
        pdf.cell(190, 8, f'Ortalama Performans: %{calisan_bilgi["ortalama_performans"]*100:.1f}', 0, 1, 'L')
        pdf.cell(190, 8, f'Risk Skoru: %{calisan_bilgi["risk_skoru"]*100:.1f}', 0, 1, 'L')
        pdf.cell(190, 8, f'Gecikme Olasılığı: %{calisan_bilgi["gecikme_olasiligi"]*100:.1f}', 0, 1, 'L')
        pdf.cell(190, 8, f'Performans Kararlılığı: %{calisan_bilgi["performans_kararliligi"]*100:.1f}', 0, 1, 'L')
        
        # Tasarım bazlı performans
        if 'tasarim_bazli_sonuclar' in calisan_bilgi:
            pdf.add_page()
            pdf.set_font('DejaVu', 'B', 14)
            pdf.cell(190, 10, 'Tasarım Bazlı Performans', 0, 1, 'L')
            pdf.set_font('DejaVu', '', 12)
            
            for tasarim, sonuc in calisan_bilgi['tasarim_bazli_sonuclar'].items():
                pdf.cell(190, 8, f'Tasarım Kodu: {tasarim}', 0, 1, 'L')
                pdf.cell(190, 6, f'  Ortalama: %{sonuc["ortalama"]*100:.1f}', 0, 1, 'L')
                pdf.cell(190, 6, f'  Risk Skoru: %{sonuc["risk_skoru"]*100:.1f}', 0, 1, 'L')
                pdf.cell(190, 6, f'  Gecikme Olasılığı: %{sonuc["gecikme_olasiligi"]*100:.1f}', 0, 1, 'L')
                pdf.ln(5)
        
        # Raporu kaydet
        rapor_adi = f'personel_raporu_{calisan_adi}_{datetime.now().strftime("%Y%m%d")}.pdf'
        rapor_yolu = os.path.join(self.rapor_klasoru, rapor_adi)
        pdf.output(rapor_yolu)
        
        return rapor_adi

    def excel_raporu_olustur(self) -> str:
        """Tüm verileri içeren Excel raporu oluştur"""
        veriler = self._veri_yukle()
        if not veriler:
            return None
        
        # Excel yazıcı oluştur
        excel_adi = f'performans_raporu_{datetime.now().strftime("%Y%m%d")}.xlsx'
        excel_yolu = os.path.join(self.rapor_klasoru, excel_adi)
        
        with pd.ExcelWriter(excel_yolu, engine='xlsxwriter') as writer:
            # Monte Carlo sonuçları
            if 'monte_carlo' in veriler and 'calisanlar' in veriler['monte_carlo']:
                mc_data = []
                for calisan, bilgi in veriler['monte_carlo']['calisanlar'].items():
                    mc_data.append({
                        'Çalışan': calisan,
                        'Ortalama Performans': f"%{bilgi['ortalama_performans']*100:.1f}",
                        'Risk Skoru': f"%{bilgi['risk_skoru']*100:.1f}",
                        'Gecikme Olasılığı': f"%{bilgi['gecikme_olasiligi']*100:.1f}",
                        'Performans Kararlılığı': f"%{bilgi['performans_kararliligi']*100:.1f}"
                    })
                
                df_monte_carlo = pd.DataFrame(mc_data)
                df_monte_carlo.to_excel(writer, sheet_name='Monte Carlo Sonuçları', index=False)
            
            # İş listesi
            if 'is_listesi' in veriler:
                df_isler = pd.DataFrame(veriler['is_listesi'])
                df_isler.to_excel(writer, sheet_name='İş Listesi', index=False)
        
        return excel_adi 