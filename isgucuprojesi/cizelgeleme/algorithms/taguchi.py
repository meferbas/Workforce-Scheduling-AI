import json
import numpy as np
from itertools import product
import os
from scipy import stats
import matplotlib.pyplot as plt
from datetime import datetime
import random
from ..models import TasarimKodu, GecmisSureVerisi, TaguchiSonucu

# Ana dizin yolunu belirle
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def load_data():
    """Django modellerinden verileri yükle"""
    try:
        tasarim_kodlari = {t.kod: {
            "urun_adi": t.urun_adi,
            "tahmini_montaj_suresi": t.tahmini_montaj_suresi,
            "minimum_yetkinlik_seviyesi": t.minimum_yetkinlik_seviyesi,
            "optimum_yetkinlik_seviyesi": t.optimum_yetkinlik_seviyesi,
            "departman": t.departman
        } for t in TasarimKodu.objects.all()}
        
        # Geçmiş süre verilerini departmanlara göre grupla
        gecmis_veriler_ham = {}
        for veri in GecmisSureVerisi.objects.all():
            if veri.departman not in gecmis_veriler_ham:
                gecmis_veriler_ham[veri.departman] = {}
            
            if veri.tasarim.kod not in gecmis_veriler_ham[veri.departman]:
                gecmis_veriler_ham[veri.departman][veri.tasarim.kod] = {
                    "urun_adi": veri.urun_adi,
                    "gecmis_sureler": []
                }
            
            gecmis_veriler_ham[veri.departman][veri.tasarim.kod]["gecmis_sureler"].append(veri.sure)
            
        # Tüm departmanlardan verileri birleştir
            gecmis_veriler = {}
            for departman, veriler in gecmis_veriler_ham.items():
                gecmis_veriler.update(veriler)
            
        return tasarim_kodlari, gecmis_veriler, gecmis_veriler_ham
    except Exception as e:
        print(f"Veri yükleme hatası: {str(e)}")
        return None, None, None

def analyze_historical_data(gecmis_veriler, kod):
    """Geçmiş verileri analiz et ve optimum süreyi hesapla"""
    if kod not in gecmis_veriler:
        return None
        
    sureler = gecmis_veriler[kod]["gecmis_sureler"]
    
    # Temel istatistikler
    ortalama = np.mean(sureler)
    std = np.std(sureler)
    
    # Aykırı değerleri tespit et
    q1 = np.percentile(sureler, 25)
    q3 = np.percentile(sureler, 75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    # Aykırı değerleri filtrele
    filtered_sureler = [s for s in sureler if lower_bound <= s <= upper_bound]
    
    # Filtrelenmiş verilerle istatistikleri güncelle
    if filtered_sureler:
        ortalama = np.mean(filtered_sureler)
        std = np.std(filtered_sureler)
        minimum = np.min(filtered_sureler)
    else:
        minimum = np.min(sureler)
    
    # Normal dağılım varsayımı altında güven aralığı
    guven_araligi = stats.norm.interval(0.95, loc=ortalama, scale=std)
    
    # Optimum süre: Alt güven aralığı, ortalama ve minimum değerin ağırlıklı ortalaması
    optimum_sure = (
        guven_araligi[0] * 0.4 +  # Alt güven aralığı %40 ağırlık
        ortalama * 0.4 +          # Ortalama %40 ağırlık
        minimum * 0.2             # Minimum %20 ağırlık
    )
    
    return {
        "optimum_sure": optimum_sure,
        "ortalama": ortalama,
        "std": std,
        "minimum": minimum,
        "guven_araligi": guven_araligi,
        "filtered_count": len(filtered_sureler),
        "original_count": len(sureler),
        "q1": q1,
        "q3": q3
    }

def create_parameter_levels(tasarim_kodlari, gecmis_veriler, level_count=3):
    """Tasarım kodları için parametre seviyelerini oluştur"""
    parameter_levels = {}
    for kod, bilgi in tasarim_kodlari.items():
        # Geçmiş veriler varsa onları kullan
        historical_analysis = None
        if gecmis_veriler and kod in gecmis_veriler:
            historical_analysis = analyze_historical_data(gecmis_veriler, kod)
        
        if historical_analysis:
            base_time = historical_analysis["optimum_sure"]
            # Geçmiş verilere dayalı seviyeleri belirle
            if level_count == 3:
                parameter_levels[kod] = [
                    max(base_time * 0.9, historical_analysis["minimum"]),  # En az minimum kadar
                    base_time,
                    base_time * 1.1  # %10 tolerans
                ]
            elif level_count == 5:
                parameter_levels[kod] = [
                    max(base_time * 0.85, historical_analysis["minimum"]),  # En az minimum kadar
                    max(base_time * 0.925, historical_analysis["minimum"]),
                    base_time,
                    base_time * 1.075,
                    base_time * 1.15  # %15 tolerans
                ]
        else:
            # Geçmiş veri yoksa mevcut tahmini süreyi kullan
            base_time = bilgi["tahmini_montaj_suresi"]
            if level_count == 3:
                parameter_levels[kod] = [
                    base_time * 0.8,
                    base_time,
                    base_time * 1.2
                ]
            elif level_count == 5:
                parameter_levels[kod] = [
                    base_time * 0.75,
                    base_time * 0.875,
                    base_time,
                    base_time * 1.125,
                    base_time * 1.25
                ]
    return parameter_levels

def calculate_snr(values, snr_type="smaller"):
    """
    Sinyal/Gürültü oranını hesapla
    
    Parametreler:
    - values: Değerler listesi
    - snr_type: SNR tipi ("smaller", "larger", "nominal")
    """
    values = np.array(values)
    
    if snr_type == "smaller":  # Smaller is better
        return -10 * np.log10(np.mean(values ** 2))
    elif snr_type == "larger":  # Larger is better
        return -10 * np.log10(np.mean(1 / (values ** 2)))
    elif snr_type == "nominal":  # Nominal is best
        mean = np.mean(values)
        var = np.var(values)
        if var == 0:
            return 0
        return 10 * np.log10((mean ** 2) / var)
    else:
        raise ValueError(f"Geçersiz SNR tipi: {snr_type}")

def create_orthogonal_array(parameter_count, level_count):
    """
    Ortogonal dizi oluştur
    
    Parametreler:
    - parameter_count: Parametre sayısı
    - level_count: Seviye sayısı
    """
    # Basit bir L9 ortogonal dizi (3 seviye, 4 faktör)
    if level_count == 3 and parameter_count <= 4:
        return np.array([
            [0, 0, 0, 0],
            [0, 1, 1, 1],
            [0, 2, 2, 2],
            [1, 0, 1, 2],
            [1, 1, 2, 0],
            [1, 2, 0, 1],
            [2, 0, 2, 1],
            [2, 1, 0, 2],
            [2, 2, 1, 0]
        ])[:, :parameter_count]
    
    # L27 ortogonal dizi (3 seviye, 13 faktör)
    elif level_count == 3 and parameter_count <= 13:
        # L27 ortogonal dizi temel matrisi
        L27_base = np.zeros((27, 13), dtype=int)
        
        # İlk 3 sütun temel faktörler
        for i in range(27):
            L27_base[i, 0] = (i // 9) % 3
            L27_base[i, 1] = (i // 3) % 3
            L27_base[i, 2] = i % 3
        
        # Diğer sütunlar etkileşimler
        for i in range(27):
            L27_base[i, 3] = (L27_base[i, 0] + L27_base[i, 1]) % 3
            L27_base[i, 4] = (L27_base[i, 0] + L27_base[i, 2]) % 3
            L27_base[i, 5] = (L27_base[i, 1] + L27_base[i, 2]) % 3
            L27_base[i, 6] = (L27_base[i, 0] + L27_base[i, 1] + L27_base[i, 2]) % 3
            L27_base[i, 7] = (2*L27_base[i, 0] + L27_base[i, 1]) % 3
            L27_base[i, 8] = (2*L27_base[i, 0] + L27_base[i, 2]) % 3
            L27_base[i, 9] = (2*L27_base[i, 1] + L27_base[i, 0]) % 3
            L27_base[i, 10] = (2*L27_base[i, 1] + L27_base[i, 2]) % 3
            L27_base[i, 11] = (2*L27_base[i, 2] + L27_base[i, 0]) % 3
            L27_base[i, 12] = (2*L27_base[i, 2] + L27_base[i, 1]) % 3
            
        return L27_base[:, :parameter_count]
    
    # Basit bir L25 ortogonal dizi (5 seviye, 6 faktör)
    elif level_count == 5 and parameter_count <= 6:
        # L25 ortogonal dizi oluştur
        L25 = np.zeros((25, 6), dtype=int)
        for i in range(25):
            for j in range(6):
                L25[i, j] = (i + j*5) % 5
        return L25[:, :parameter_count]
    
    # L50 ortogonal dizi (5 seviye, 12 faktör)
    elif level_count == 5 and parameter_count <= 12:
        # L50 ortogonal dizi oluştur (5^12 için yaklaşık bir dizi)
        L50 = np.zeros((50, 12), dtype=int)
        
        # İlk 2 sütun temel faktörler
        for i in range(50):
            L50[i, 0] = (i // 10) % 5
            L50[i, 1] = i % 5
        
        # Diğer sütunlar için Latin kare tasarımı kullan
        for j in range(2, 12):
            for i in range(50):
                L50[i, j] = (L50[i, 0] + j*L50[i, 1]) % 5
                
        return L50[:, :parameter_count]
    
    # Parametre sayısı çok fazla ise uyarı ver ve None döndür
    elif parameter_count > 15 or (level_count ** parameter_count) > 1000000:
        print(f"UYARI: Parametre sayısı ({parameter_count}) veya kombinasyon sayısı ({level_count ** parameter_count}) çok fazla!")
        print("Tam faktöriyel tasarım çok fazla bellek kullanacak ve sistem yavaşlayabilir.")
        print("Daha az parametre ile tekrar deneyin veya farklı bir optimizasyon yöntemi kullanın.")
        return None
    
    # Ortogonal dizi yoksa tam faktöriyel tasarım kullan
    else:
        print(f"Uygun ortogonal dizi bulunamadı. Tam faktöriyel tasarım kullanılıyor.")
        print(f"Toplam {level_count ** parameter_count} kombinasyon oluşturulacak.")
        return None

def taguchi_optimization(parameter_levels, gecmis_veriler, level_count=3, snr_type="smaller"):
    """
    Taguchi optimizasyonu gerçekleştir ve birden fazla çalıştırmanın ortalamasını al
    
    Parametreler:
    - parameter_levels: Parametre seviyeleri
    - gecmis_veriler: Geçmiş veriler
    - level_count: Seviye sayısı
    - snr_type: SNR tipi
    """
    CALISTIRMA_SAYISI = 5  # Optimizasyonun kaç kez tekrarlanacağı
    
    keys = list(parameter_levels.keys())
    parameter_count = len(keys)
    
    print(f"Toplam parametre sayısı: {parameter_count}, Seviye sayısı: {level_count}")
    print(f"Optimizasyon {CALISTIRMA_SAYISI} kez tekrarlanacak ve ortalama sonuç alınacak")
    
    # Her tasarım kodu için optimize edilmiş süreleri tutacak sözlük
    tum_optimum_sureler = {}
    tum_improvement_data = {}
    tum_snr_values = []
    
    for calistirma in range(CALISTIRMA_SAYISI):
        print(f"\nOptimizasyon çalıştırması {calistirma + 1}/{CALISTIRMA_SAYISI}")
        
        # Ortogonal dizi oluştur
        orthogonal_array = create_orthogonal_array(parameter_count, level_count)
        
        if orthogonal_array is not None:
            print(f"Ortogonal dizi kullanılıyor. Toplam {len(orthogonal_array)} deney yapılacak.")
            # Ortogonal dizi kullanarak deneyleri oluştur
            experiments = []
            for row in orthogonal_array:
                experiment = []
                for i, level_idx in enumerate(row):
                    key = keys[i]
                    experiment.append(parameter_levels[key][level_idx])
                experiments.append(experiment)
            
            # Deneyleri değerlendir
            experiment_results = []
            snr_values = []
            for experiment in experiments:
                total_time = sum(experiment)
                experiment_results.append(total_time)
                snr_values.append(calculate_snr([total_time], snr_type))
            
            # En iyi kombinasyonu bul
            best_idx = np.argmax(snr_values)
            best_combination = experiments[best_idx]
            best_parameters = dict(zip(keys, best_combination))
            
        else:
            # Rastgele örnekleme için
            print("Rastgele örnekleme yöntemi kullanılıyor...")
            max_combinations = 10000
            
            # Parametre seviyelerini liste olarak hazırla
            level_lists = [parameter_levels[key] for key in keys]
            
            # En iyi kombinasyonu bulmak için değişkenler
            best_combination = None
            best_snr = float('-inf')
            best_total_time = float('inf')
            
            # Rastgele kombinasyonları değerlendir
            experiment_results = []
            snr_values = []
            for _ in range(max_combinations):
                combination = [random.choice(levels) for levels in level_lists]
                total_time = sum(combination)
                snr_value = calculate_snr([total_time], snr_type)
                
                experiment_results.append(total_time)
                snr_values.append(snr_value)
                
                if snr_value > best_snr:
                    best_snr = snr_value
                    best_combination = combination
                    best_total_time = total_time
            
            best_parameters = dict(zip(keys, best_combination))
        
        # İyileştirme oranlarını hesapla
        improvement_data = {}
        for kod, optimum_sure in best_parameters.items():
            if kod in gecmis_veriler:
                historical = analyze_historical_data(gecmis_veriler, kod)
                if historical:
                    original = historical["ortalama"]
                    improvement = ((original - optimum_sure) / original) * 100
                    improvement_data[kod] = {
                        "original": original,
                        "optimized": optimum_sure,
                        "improvement": improvement
                    }
        
        # Her tasarım kodu için optimize edilmiş süreleri ve iyileştirme verilerini sakla
        for kod, optimum_sure in best_parameters.items():
            if kod not in tum_optimum_sureler:
                tum_optimum_sureler[kod] = []
            tum_optimum_sureler[kod].append(optimum_sure)
            
            if kod in improvement_data:
                if kod not in tum_improvement_data:
                    tum_improvement_data[kod] = []
                tum_improvement_data[kod].append(improvement_data[kod])
        
        tum_snr_values.extend(snr_values)
    
    # Ortalama sonuçları hesapla
    final_best_parameters = {}
    final_improvement_data = {}
    
    for kod in tum_optimum_sureler:
        # Optimize edilmiş sürelerin ortalamasını al
        ortalama_sure = np.mean(tum_optimum_sureler[kod])
        final_best_parameters[kod] = ortalama_sure
        
        # İyileştirme verilerinin ortalamasını al
        if kod in tum_improvement_data:
            ortalama_improvement = np.mean([data["improvement"] for data in tum_improvement_data[kod]])
            final_improvement_data[kod] = {
                "original": tum_improvement_data[kod][0]["original"],  # İlk değeri kullan
                "optimized": ortalama_sure,
                "improvement": ortalama_improvement
            }
    
    print("\nTüm çalıştırmaların ortalaması alındı.")
    
    return final_best_parameters, experiment_results, tum_snr_values, final_improvement_data

def analyze_parameter_effects(parameter_levels, experiments, snr_values, is_random_sampling=False):
    """
    Her parametrenin etkisini analiz et
    
    Parametreler:
    - parameter_levels: Parametre seviyeleri
    - experiments: Deneyler
    - snr_values: SNR değerleri
    - is_random_sampling: Rastgele örnekleme kullanıldı mı?
    """
    parameter_effects = {}
    keys = list(parameter_levels.keys())
    
    # Rastgele örnekleme kullanıldıysa, parametre etkilerini hesaplamak için
    # her seviyenin ortalama SNR değerini kullan
    if is_random_sampling:
        print("Rastgele örnekleme için parametre etkileri hesaplanıyor...")
        
        # Her parametre için
        for i, key in enumerate(keys):
            parameter_effects[key] = {}
            levels = parameter_levels[key]
            
            # Her seviye için
            for level_idx, level_value in enumerate(levels):
                # Bu seviyeyi içeren tüm deneyleri bul
                level_snr_values = []
                
                # Tüm deneyleri kontrol et
                for j, experiment in enumerate(experiments):
                    if abs(experiment[i] - level_value) < 0.001:  # Yaklaşık eşitlik kontrolü
                        level_snr_values.append(snr_values[j])
                
                # Bu seviye için ortalama SNR değerini hesapla
                if level_snr_values:
                    parameter_effects[key][level_value] = np.mean(level_snr_values)
                else:
                    parameter_effects[key][level_value] = 0
        
        return parameter_effects
    
    # Normal Taguchi analizi için
    for i, key in enumerate(keys):
        parameter_effects[key] = {}
        levels = parameter_levels[key]
        
        for level_idx, level_value in enumerate(levels):
            # Bu seviyeyi içeren tüm deneyleri bul
            level_experiments = []
            level_snr_values = []
            
            for j, experiment in enumerate(experiments):
                if isinstance(experiment, list) and i < len(experiment):
                    if abs(experiment[i] - level_value) < 0.001:  # Yaklaşık eşitlik kontrolü
                        level_experiments.append(experiment)
                        level_snr_values.append(snr_values[j])
            
            # Bu seviye için ortalama SNR değerini hesapla
            if level_snr_values:
                parameter_effects[key][level_value] = np.mean(level_snr_values)
            else:
                parameter_effects[key][level_value] = 0
    
    return parameter_effects

def create_taguchi_visualizations(parameter_effects, improvement_data):
    """
    Taguchi optimizasyonu sonuçlarını görselleştir
    
    Parametreler:
    - parameter_effects: Parametre etkileri
    - improvement_data: İyileştirme verileri
    """
    # Grafikleri kaydetmek için klasör oluştur
    output_dir = os.path.join(ROOT_DIR, 'static', 'img', 'taguchi')
    os.makedirs(output_dir, exist_ok=True)
    
    # Parametre etkileri grafiği
    plt.figure(figsize=(12, 8))
    
    for i, (param, effects) in enumerate(parameter_effects.items()):
        plt.subplot(2, 3, i+1)
        plt.plot(range(1, len(effects)+1), effects, 'o-', linewidth=2)
        plt.title(f'Parametre: {param}')
        plt.xlabel('Seviye')
        plt.ylabel('Ortalama SNR')
        plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'parameter_effects.png'), dpi=100, bbox_inches='tight')
    
    # İyileştirme oranları grafiği
    if improvement_data:
        plt.figure(figsize=(12, 6))
        
        # En yüksek iyileştirme oranına göre sırala
        sorted_improvements = sorted(improvement_data.items(), key=lambda x: x[1]['improvement'], reverse=True)
        codes = [item[0] for item in sorted_improvements]
        improvements = [item[1]['improvement'] for item in sorted_improvements]
        
        # En fazla 15 tasarım kodunu göster
        if len(codes) > 15:
            codes = codes[:15]
            improvements = improvements[:15]
        
        bars = plt.bar(codes, improvements, alpha=0.7)
        plt.title('Tasarım Kodlarına Göre İyileştirme Oranları')
        plt.xlabel('Tasarım Kodu')
        plt.ylabel('İyileştirme Oranı (%)')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        
        # Değerleri çubukların üzerine ekle
        for bar, value in zip(bars, improvements):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f'{value:.1f}%', 
                    ha='center', va='bottom')
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'improvement_rates.png'), dpi=100, bbox_inches='tight')
    
    # Orijinal vs Optimize edilmiş süreler karşılaştırması
    if improvement_data:
        plt.figure(figsize=(12, 6))
        
        codes = list(improvement_data.keys())
        original_times = [improvement_data[code]['original'] for code in codes]
        optimized_times = [improvement_data[code]['optimized'] for code in codes]
        
        # En fazla 10 tasarım kodunu göster
        if len(codes) > 10:
            codes = codes[:10]
            original_times = original_times[:10]
            optimized_times = optimized_times[:10]
        
        x = np.arange(len(codes))
        width = 0.35
        
        plt.bar(x - width/2, original_times, width, label='Orijinal Süre', color='orange', alpha=0.7)
        plt.bar(x + width/2, optimized_times, width, label='Optimize Edilmiş Süre', color='green', alpha=0.7)
        
        plt.title('Orijinal vs Optimize Edilmiş Süreler')
        plt.xlabel('Tasarım Kodu')
        plt.ylabel('Süre (dk)')
        plt.xticks(x, codes, rotation=45, ha='right')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'time_comparison.png'), dpi=100, bbox_inches='tight')
    
    plt.close('all')  # Tüm grafikleri kapat

def save_taguchi_results(tasarim_kodu, optimum_sure, iyilestirme_orani, method="Taguchi L27"):
    """Taguchi optimizasyon sonuçlarını veritabanına kaydet"""
    try:
        tasarim = TasarimKodu.objects.get(kod=tasarim_kodu)
        
        # Önceki sonucu güncelle veya yeni sonuç oluştur
        sonuc, created = TaguchiSonucu.objects.update_or_create(
            tasarim_kodu=tasarim_kodu,
            defaults={
                'optimum_sure': optimum_sure,
                'optimum_seviye': tasarim.optimum_yetkinlik_seviyesi,
                'iyilestirme_orani': iyilestirme_orani,
                'method': method,
                'departman': tasarim.departman,
                'guncellenme_tarihi': datetime.now()
            }
        )
        return True
    except Exception as e:
        print(f"Taguchi sonuçları kaydedilemedi: {str(e)}")
        return False

def main():
    """Ana optimizasyon fonksiyonu"""
    try:
    # Verileri yükle
        tasarim_kodlari, gecmis_veriler, gecmis_veriler_ham = load_data()
        if not all([tasarim_kodlari, gecmis_veriler, gecmis_veriler_ham]):
            return "Veri yükleme hatası!"
        
        sonuclar = {}
        for departman, veriler in gecmis_veriler_ham.items():
            print(f"\n{departman} departmanı için optimizasyon başlatılıyor...")
            
            for kod in veriler.keys():
                if kod not in tasarim_kodlari:
                    continue
    
    # Parametre seviyelerini oluştur
                parameter_levels = create_parameter_levels(
                    {kod: tasarim_kodlari[kod]}, 
                    {kod: gecmis_veriler[kod]},
                    level_count=3
                )

                # Taguchi optimizasyonunu gerçekleştir
                optimum_sure, iyilestirme = taguchi_optimization(
        parameter_levels, 
                    {kod: gecmis_veriler[kod]},
                    level_count=3
                )
                
                if optimum_sure is not None:
                    # Sonuçları veritabanına kaydet
                    save_taguchi_results(kod, optimum_sure, iyilestirme)
                    sonuclar[kod] = {
                        'optimum_sure': optimum_sure,
                        'iyilestirme': iyilestirme
                    }
        
        return "Taguchi optimizasyonu başarıyla tamamlandı ve sonuçlar veritabanına kaydedildi."
        
    except Exception as e:
        return f"Hata oluştu: {str(e)}"

if __name__ == "__main__":
    main()
