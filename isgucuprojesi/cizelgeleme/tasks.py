from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .algorithms.monte_carlo_simulasyon import simulasyon_calistir
from .algorithms.taguchi import main as taguchi_main
from .algorithms.geneticalgorithm import main as genetic_main
from .models import MonteCarloSonuc, TaguchiSonucu, GenetikSonuc
from django.db.models import Avg

@shared_task
def run_all_optimizations():
    """Tüm optimizasyonları çalıştır ve sonuçları WebSocket üzerinden gönder"""
    print("Optimizasyonlar başlatılıyor...")
    channel_layer = get_channel_layer()
    
    try:
        # Monte Carlo Simülasyonu
        print("Monte Carlo simülasyonu başlatılıyor...")
        monte_carlo_result = simulasyon_calistir()
        
        # Veritabanından en son kaydedilen sonuçları al
        latest_mc_results_qs = MonteCarloSonuc.objects.select_related('calisan').order_by('-simulasyon_zamani')
        
        # Genel istatistikleri hesapla
        ortalama_performans_genel = latest_mc_results_qs.aggregate(Avg('ortalama_performans'))['ortalama_performans__avg'] or 0
        ortalama_risk_genel = latest_mc_results_qs.aggregate(Avg('risk_skoru'))['risk_skoru__avg'] or 0

        monte_carlo_data = {
            'genel_istatistikler': {
                'ortalama_performans': ortalama_performans_genel,
                'ortalama_risk': ortalama_risk_genel
            },
            'latest_results': list(latest_mc_results_qs.values(
                'calisan__ad_soyad', 'ortalama_performans', 
                'risk_skoru', 'gecikme_olasiligi', 'performans_kararliligi'
            )[:5]) # İlk 5 sonucu alalım (isteğe bağlı)
        }
        print(f"Monte Carlo sonuçları (WebSocket için): {monte_carlo_data}")
        
        # Taguchi Optimizasyonu
        print("Taguchi optimizasyonu başlatılıyor...")
        taguchi_result = taguchi_main()
        taguchi_data = {
            'latest_results': list(TaguchiSonucu.objects.order_by('-guncellenme_tarihi')
                                .values('tasarim_kodu', 'optimum_sure', 
                                      'iyilestirme_orani')[:5])
        }
        print(f"Taguchi sonuçları: {taguchi_data}")
        
        # Genetik Algoritma
        print("Genetik algoritma başlatılıyor...")
        genetic_result = genetic_main()
        genetic_data = {
            'latest_results': list(GenetikSonuc.objects.select_related('tasarim')
                                .order_by('-id')
                                .values('tasarim__kod', 'senaryo')[:5])
        }
        print(f"Genetik algoritma sonuçları: {genetic_data}")
        
        # Sonuçları WebSocket üzerinden gönder
        async_to_sync(channel_layer.group_send)(
            'optimization_updates',
            {
                'type': 'optimization_update',
                'monte_carlo': monte_carlo_data,
                'taguchi': taguchi_data,
                'genetic': genetic_data
            }
        )
        print("Sonuçlar WebSocket üzerinden gönderildi")
        
    except Exception as e:
        print(f"Hata oluştu: {str(e)}")
        raise
    
    return "Optimizasyonlar tamamlandı" 