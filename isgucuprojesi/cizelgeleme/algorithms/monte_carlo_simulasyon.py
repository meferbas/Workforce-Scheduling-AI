import json
import os
import numpy as np
from typing import Dict, List
import matplotlib.pyplot as plt
from datetime import datetime
from ..models import Calisan, TasarimKodu, GecmisPerformansVerisi, MonteCarloSonuc, MonteCarloTasarimSonuc
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Ana dizin yolunu belirle
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def performans_verilerini_oku() -> Dict:
    """Geçmiş performans verilerini Django modellerinden okur."""
    try:
        veriler = {}
        for tasarim in TasarimKodu.objects.all():
            veriler[tasarim.kod] = []
            performans_verileri = GecmisPerformansVerisi.objects.filter(tasarim=tasarim)
            
            # Proje indekslerine göre grupla
            for proje_index in set(pv.proje_index for pv in performans_verileri):
                proje = {}
                for pv in performans_verileri.filter(proje_index=proje_index):
                    proje[pv.calisan.ad_soyad] = pv.verimlilik_puani
                veriler[tasarim.kod].append(proje)
                
        return veriler
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

        # Son 25 iş ve önceki işleri ayır
        if len(performanslar) > 25:
            son_25_is = performanslar[-25:]
            onceki_isler = performanslar[:-25]
        else:
            son_25_is = performanslar
            onceki_isler = []

        # Ağırlıklı ortalama hesapla: %40 son 25 iş, %60 önceki işler
        if onceki_isler:
            son_25_ortalama = np.mean(son_25_is) if son_25_is else 0
            onceki_ortalama = np.mean(onceki_isler) if onceki_isler else 0
            agirlikli_performans = (son_25_ortalama * 0.4) + (onceki_ortalama * 0.6)
        else:
            agirlikli_performans = np.mean(son_25_is) if son_25_is else 0

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

def monte_carlo_simulasyonu(veriler: Dict, calisan_listesi: List[str], iterasyon_sayisi: int = 10000) -> Dict:
    """Monte Carlo simülasyonu yaparak gelecek performans tahminlerini üretir."""
    sonuclar = {
        'calisanlar': {},
        'simulasyon_zamani': datetime.now()
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
        calisan_listesi = [c.ad_soyad for c in Calisan.objects.all()]
        
        # Simülasyonu çalıştır
        sonuclar = monte_carlo_simulasyonu(veriler, calisan_listesi)
        
        # Önceki sonuçları temizle
        MonteCarloSonuc.objects.all().delete()
        MonteCarloTasarimSonuc.objects.all().delete()
        
        # Sonuçları veritabanına kaydet
        for calisan_adi, bilgi in sonuclar['calisanlar'].items():
            calisan = Calisan.objects.get(ad_soyad=calisan_adi)
            
            # Genel sonuçları kaydet
            mc_sonuc = MonteCarloSonuc.objects.create(
                calisan=calisan,
                ortalama_performans=bilgi['ortalama_performans'],
                risk_skoru=bilgi['risk_skoru'],
                gecikme_olasiligi=bilgi['gecikme_olasiligi'],
                performans_kararliligi=bilgi['performans_kararliligi'],
                simulasyon_zamani=sonuclar['simulasyon_zamani']
            )
            
            # Tasarım bazlı sonuçları kaydet
            for tasarim_kodu, tasarim_sonuc in bilgi['tasarim_bazli_sonuclar'].items():
                tasarim = TasarimKodu.objects.get(kod=tasarim_kodu)
                MonteCarloTasarimSonuc.objects.create(
                    calisan=calisan,
                    tasarim=tasarim,
                    ortalama=tasarim_sonuc['ortalama'],
                    risk_skoru=tasarim_sonuc['risk_skoru'],
                    gecikme_olasiligi=tasarim_sonuc['gecikme_olasiligi']
                )
        
        # WebSocket mesajı gönder
        send_channel_message("monte_carlo_simulasyon", "simulasyon_sonuclari", sonuclar)
        
        return "Simülasyon başarıyla tamamlandı. Sonuçlar veritabanına kaydedildi."
        
    except Exception as e:
        return f"Hata oluştu: {str(e)}"

def send_channel_message(group_name, message_type, message_content):
    """WebSocket grubuna mesaj gönderir."""
    try:
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": message_type,
                    "message": message_content,
                },
            )
            print(f"'{group_name}' grubuna mesaj gönderildi.")
        else:
            print("Channel layer bulunamadı.")
    except Exception as e:
        print(f"WebSocket mesajı gönderilirken hata oluştu: {str(e)}")

if __name__ == "__main__":
    print(simulasyon_calistir()) 