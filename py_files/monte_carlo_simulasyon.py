import json
import os
import numpy as np
from typing import Dict, List
import matplotlib.pyplot as plt
from datetime import datetime

# Ana dizin yolunu belirle
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def performans_verilerini_oku() -> Dict:
    """Geçmiş performans verilerini JSON dosyasından okur."""
    try:
        with open(os.path.join(ROOT_DIR, 'veri', 'gecmis_proje_performans_verileri.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Performans verileri okunamadı: {str(e)}")
        return None

def calisan_performans_dagilimi(veriler: Dict, calisan: str) -> Dict[str, Dict]:
    """Her tasarım kodu için çalışanın performans dağılımını ve trendini hesaplar."""
    dagilimlar = {}
    for tasarim_kodu in veriler:
        performanslar = [proje[calisan] for proje in veriler[tasarim_kodu] if calisan in proje]
        if not performanslar:
            continue
            
        # Son 10 proje ve önceki projeleri ayır
        son_10_proje = performanslar[-10:] if len(performanslar) > 10 else performanslar
        onceki_projeler = performanslar[:-10] if len(performanslar) > 10 else []
        
        # Ağırlıklı ortalama hesapla
        son_10_ortalama = np.mean(son_10_proje) if son_10_proje else 0
        onceki_ortalama = np.mean(onceki_projeler) if onceki_projeler else son_10_ortalama
        
        # Son 10 projeye %60, önceki projelere %40 ağırlık ver
        agirlikli_performans = (son_10_ortalama * 0.6) + (onceki_ortalama * 0.4)
        
        # Trend analizi (son projelerdeki değişim)
        trend = 0
        if len(performanslar) > 1:
            trend = np.polyfit(range(len(performanslar)), performanslar, 1)[0]
        
        dagilimlar[tasarim_kodu] = {
            'performanslar': performanslar,
            'agirlikli_performans': float(agirlikli_performans),
            'trend': float(trend),
            'varyans': float(np.var(performanslar))
        }
    return dagilimlar

def monte_carlo_simulasyonu(veriler: Dict, calisan_listesi: List[str], iterasyon_sayisi: int = 100000) -> Dict:
    """Monte Carlo simülasyonu yaparak gelecek performans tahminlerini üretir."""
    sonuclar = {
        'calisanlar': {},
        'simulasyon_zamani': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    for calisan in calisan_listesi:
        performans_dagilimi = calisan_performans_dagilimi(veriler, calisan)
        
        # Her tasarım kodu için ayrı simülasyon yap
        tasarim_sonuclari = {}
        tum_performanslar = []
        
        for tasarim_kodu, dagilim in performans_dagilimi.items():
            # Performans dağılımını ve trendi kullanarak simülasyon
            temel_performans = dagilim['agirlikli_performans']
            trend = dagilim['trend']
            varyans = max(0.01, dagilim['varyans'])  # Minimum varyans garantisi
            
            # Trend ve varyansı kullanarak simülasyon
            simulasyon = np.random.normal(
                loc=temel_performans + trend,
                scale=np.sqrt(varyans),
                size=iterasyon_sayisi
            )
            
            # Değerleri 0-1 aralığına sınırla
            simulasyon = np.clip(simulasyon, 0, 1)
            
            tasarim_sonuclari[tasarim_kodu] = {
                'ortalama': float(np.mean(simulasyon)),
                'risk_skoru': float(len(simulasyon[simulasyon < 0.5]) / len(simulasyon)),
                'gecikme_olasiligi': float(len(simulasyon[simulasyon < 0.3]) / len(simulasyon))
            }
            
            tum_performanslar.extend(simulasyon)
        
        # Genel performans metrikleri
        ortalama_performans = np.mean(tum_performanslar)
        risk_skoru = len([p for p in tum_performanslar if p < 0.5]) / len(tum_performanslar)
        gecikme_olasiligi = len([p for p in tum_performanslar if p < 0.3]) / len(tum_performanslar)
        
        # Performans kararlılığı (düşük varyans = yüksek kararlılık)
        performans_kararliligi = 1 - min(1, np.var(tum_performanslar) * 2)
        
        sonuclar['calisanlar'][calisan] = {
            'ortalama_performans': float(ortalama_performans),
            'risk_skoru': float(risk_skoru),
            'gecikme_olasiligi': float(gecikme_olasiligi),
            'performans_kararliligi': float(performans_kararliligi),
            'tasarim_bazli_sonuclar': tasarim_sonuclari,
            'performans_dagilimi': {
                'min': float(np.min(tum_performanslar)),
                'max': float(np.max(tum_performanslar)),
                'std': float(np.std(tum_performanslar)),
                'q25': float(np.percentile(tum_performanslar, 25)),
                'q75': float(np.percentile(tum_performanslar, 75))
            }
        }
    
    return sonuclar

def simulasyon_calistir():
    """Ana simülasyon fonksiyonu."""
    try:
        # Verileri oku
        veriler = performans_verilerini_oku()
        if not veriler:
            return "Performans verileri okunamadı!"
        
        # Tüm çalışanların listesini al
        calisan_listesi = list(veriler[list(veriler.keys())[0]][0].keys())
        
        # Simülasyonu çalıştır
        sonuclar = monte_carlo_simulasyonu(veriler, calisan_listesi)
        
        # Sonuçları JSON olarak kaydet
        with open(os.path.join(ROOT_DIR, 'veri', 'monte_carlo_sonuclari.json'), 'w', encoding='utf-8') as f:
            json.dump(sonuclar, f, indent=4, ensure_ascii=False)
        
        # Rapor oluştur
        rapor = "PERFORMANS SİMÜLASYON RAPORU\n"
        rapor += "=" * 50 + "\n\n"
        rapor += f"Simülasyon Zamanı: {sonuclar['simulasyon_zamani']}\n\n"
        rapor += "ÇALIŞAN PERFORMANS TAHMİNLERİ:\n"
        rapor += "-" * 30 + "\n\n"
        
        # Çalışanları ortalama performansa göre sırala
        sirali_calisanlar = sorted(
            sonuclar['calisanlar'].items(),
            key=lambda x: (
                x[1]['ortalama_performans'] * 0.4 +  # Ortalama performans
                (1 - x[1]['risk_skoru']) * 0.3 +     # Risk skoru (tersine çevrilmiş)
                x[1]['performans_kararliligi'] * 0.3  # Performans kararlılığı
            ),
            reverse=True
        )
        
        for calisan, bilgi in sirali_calisanlar:
            rapor += f"Çalışan: {calisan}\n"
            rapor += f"Ortalama Performans: {bilgi['ortalama_performans']:.2f}\n"
            rapor += f"Risk Skoru: {bilgi['risk_skoru']:.2f}\n"
            rapor += f"Gecikme Olasılığı: {bilgi['gecikme_olasiligi']:.2f}\n"
            rapor += f"Performans Kararlılığı: {bilgi['performans_kararliligi']:.2f}\n"
            rapor += f"Performans Aralığı: {bilgi['performans_dagilimi']['q25']:.2f} - {bilgi['performans_dagilimi']['q75']:.2f}\n\n"
        
        # Raporu dosyaya kaydet
        with open(os.path.join(ROOT_DIR, 'simulasyon_raporu.txt'), 'w', encoding='utf-8') as f:
            f.write(rapor)
        
        return "Simülasyon başarıyla tamamlandı. Sonuçlar kaydedildi."
        
    except Exception as e:
        return f"Hata oluştu: {str(e)}"

if __name__ == "__main__":
    print(simulasyon_calistir()) 