import json
import numpy as np
from itertools import product
import os
from scipy import stats

# Ana dizin yolunu belirle
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def load_data():
    """JSON dosyalarından verileri yükle"""
    try:
        with open(os.path.join(ROOT_DIR, 'veri', 'tasarim_kodlari.json'), 'r', encoding='utf-8') as f:
            tasarim_kodlari = json.load(f)
            print(f"Tasarım kodları yüklendi: {len(tasarim_kodlari)} adet kod bulundu")
        
        with open(os.path.join(ROOT_DIR, 'veri', 'gecmis_veriler.json'), 'r', encoding='utf-8') as f:
            gecmis_veriler_ham = json.load(f)
            
            # Departmanlardan verileri birleştir
            gecmis_veriler = {}
            for departman, veriler in gecmis_veriler_ham.items():
                gecmis_veriler.update(veriler)
            
            print(f"Geçmiş veriler yüklendi: {len(gecmis_veriler)} adet tasarım kodu için veri bulundu")
            
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
    minimum = np.min(sureler)
    
    # Normal dağılım varsayımı altında güven aralığı
    guven_araligi = stats.norm.interval(0.95, loc=ortalama, scale=std)
    
    # Optimum süre: Alt güven aralığı ile minimum arasında bir değer
    optimum_sure = (guven_araligi[0] + minimum) / 2
    
    return {
        "optimum_sure": optimum_sure,
        "ortalama": ortalama,
        "std": std,
        "minimum": minimum,
        "guven_araligi": guven_araligi
    }

def create_parameter_levels(tasarim_kodlari, gecmis_veriler):
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
            parameter_levels[kod] = [
                max(base_time * 0.9, historical_analysis["minimum"]),  # En az minimum kadar
                base_time,
                base_time * 1.1  # %10 tolerans
            ]
        else:
            # Geçmiş veri yoksa mevcut tahmini süreyi kullan
            base_time = bilgi["tahmini_montaj_suresi"]
            parameter_levels[kod] = [
                base_time * 0.8,
                base_time,
                base_time * 1.2
            ]
    return parameter_levels

def calculate_snr(values):
    """Sinyal/Gürültü oranını hesapla (Smaller is better)"""
    return -10 * np.log10(np.mean(np.array(values) ** 2))

def taguchi_optimization(parameter_levels, gecmis_veriler):
    """Taguchi optimizasyonu gerçekleştir"""
    experiments = list(product(*parameter_levels.values()))
    results = []
    snr_values = []

    # Her kombinasyon için toplam süre ve SNR hesapla
    for experiment in experiments:
        total_time = sum(experiment)
        results.append(total_time)
        snr_values.append(calculate_snr([total_time]))

    # En yüksek SNR olan kombinasyonu bul
    best_idx = np.argmax(snr_values)
    best_combination = experiments[best_idx]
    
    keys = list(parameter_levels.keys())
    best_parameters = dict(zip(keys, best_combination))

    # Geçmiş verilere dayalı iyileştirme oranlarını hesapla
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

    return best_parameters, results, snr_values, improvement_data

def main():
    print("Taguchi optimizasyonu başlatılıyor...")

    # Verileri yükle
    tasarim_kodlari, gecmis_veriler, gecmis_veriler_ham = load_data()
    if not tasarim_kodlari or not gecmis_veriler:
        raise Exception("Veriler yüklenemedi!")
    
    print("Parametre seviyeleri oluşturuluyor...")
    parameter_levels = create_parameter_levels(tasarim_kodlari, gecmis_veriler)

    print("Taguchi optimizasyonu yapılıyor...")
    best_parameters, results, snr_values, improvement_data = taguchi_optimization(parameter_levels, gecmis_veriler)

    print("\n=== Taguchi Optimizasyon Sonuçları ===")
    print("-" * 50)
    
    # Sonuçları hazırla ve departman bilgisini ekle
    improved_data = {}
    for kod, optimum_sure in best_parameters.items():
        improvement = None
        if kod in improvement_data:
            improvement = improvement_data[kod]["improvement"]
        else:
            original = tasarim_kodlari[kod]['tahmini_montaj_suresi']
            improvement = ((original - optimum_sure) / original) * 100

        # Departman bilgisini bul
        departman = None
        for dep, veriler in gecmis_veriler_ham.items():
            if kod in veriler:
                departman = dep
                break

        print(f"Tasarım Kodu: {kod}")
        print(f"  Departman: {departman if departman else 'Belirsiz'}")
        print(f"  Ürün: {tasarim_kodlari[kod]['urun_adi']}")
        print(f"  Optimize Edilmiş Süre: {optimum_sure:.1f} dakika")
        print(f"  İyileştirme: %{improvement:.1f}")
        print("-" * 50)
        
        improved_data[kod] = {
            "sure": float(optimum_sure),
            "optimum_seviye": tasarim_kodlari[kod].get('optimum_yetkinlik_seviyesi', 1),
            "iyilestirme_orani": float(improvement),
            "method": "Taguchi (Geçmiş Veriler)" if kod in improvement_data else "Taguchi",
            "departman": departman if departman else "Belirsiz"
        }

    # Ortalama iyileştirme oranı
    avg_improvement = np.mean([data["iyilestirme_orani"] for data in improved_data.values()])

    results_json = {
        "best_parameters": improved_data,
        "average_improvement": float(avg_improvement)
    }

    # Sonuçları kaydet
    output_path = os.path.join(ROOT_DIR, 'veri', 'taguchi_sonuclari.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results_json, f, ensure_ascii=False, indent=4)
    
    print(f"Taguchi optimizasyonu tamamlandı. Sonuçlar kaydedildi: {output_path}")

    # tasarim_kodlari.json'u güncelle
    for kod, data in improved_data.items():
        tasarim_kodlari[kod]['tahmini_montaj_suresi'] = data["sure"]
        tasarim_kodlari[kod]['departman'] = data["departman"]
    
    with open(os.path.join(ROOT_DIR, 'veri', 'tasarim_kodlari.json'), 'w', encoding='utf-8') as f:
        json.dump(tasarim_kodlari, f, ensure_ascii=False, indent=4)
    print("tasarim_kodlari.json güncellendi.")

    return results_json

if __name__ == "__main__":
    main()
