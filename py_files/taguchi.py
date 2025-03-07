import json
import numpy as np
from itertools import product
import os
from scipy import stats
import matplotlib.pyplot as plt
from datetime import datetime

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
    
    # Normal dağılım varsayımı altında güven aralığı
    guven_araligi = stats.norm.interval(0.95, loc=ortalama, scale=std)
    
    # Optimum süre: Alt güven aralığı ile minimum arasında bir değer
    optimum_sure = (guven_araligi[0] + minimum) / 2
    
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
    Taguchi optimizasyonu gerçekleştir
    
    Parametreler:
    - parameter_levels: Parametre seviyeleri
    - gecmis_veriler: Geçmiş veriler
    - level_count: Seviye sayısı
    - snr_type: SNR tipi
    """
    keys = list(parameter_levels.keys())
    parameter_count = len(keys)
    
    print(f"Toplam parametre sayısı: {parameter_count}, Seviye sayısı: {level_count}")
    
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
    else:
        # Parametre sayısı çok fazla ise
        if parameter_count > 15 or (level_count ** parameter_count) > 1000000:
            print("Parametre sayısı çok fazla, rastgele örnekleme yöntemi kullanılıyor...")
            print("Bu yöntem, tam faktöriyel tasarım yerine rastgele seçilmiş kombinasyonları değerlendirir.")
            
            # Rastgele örnekleme için maksimum kombinasyon sayısı
            max_combinations = 10000
            print(f"Toplam {max_combinations} rastgele kombinasyon değerlendirilecek.")
            
            # Parametre seviyelerini liste olarak hazırla
            level_lists = [parameter_levels[key] for key in keys]
            
            # En iyi kombinasyonu bulmak için değişkenler
            best_combination = None
            best_snr = float('-inf')
            best_total_time = float('inf')
            
            # İlerleme takibi için değişkenler
            processed_count = 0
            last_progress_report = 0
            start_time = datetime.now()
            
            print("Rastgele kombinasyonlar değerlendiriliyor...")
            
            # Rastgele kombinasyonları değerlendir
            import random
            for _ in range(max_combinations):
                # Her parametre için rastgele bir seviye seç
                combination = [random.choice(levels) for levels in level_lists]
                
                total_time = sum(combination)
                snr_value = calculate_snr([total_time], snr_type)
                
                # En iyi kombinasyonu güncelle
                if snr_value > best_snr:
                    best_snr = snr_value
                    best_combination = combination
                    best_total_time = total_time
                
                # İlerleme durumunu güncelle
                processed_count += 1
                progress_percent = (processed_count / max_combinations) * 100
                
                # Her %10'luk ilerleme için rapor ver
                if progress_percent - last_progress_report >= 10:
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    estimated_total_time = elapsed_time / (progress_percent / 100)
                    remaining_time = estimated_total_time - elapsed_time
                    
                    print(f"İlerleme: %{progress_percent:.1f} - "
                          f"İşlenen: {processed_count}/{max_combinations} - "
                          f"Tahmini kalan süre: {remaining_time/60:.1f} dakika")
                    
                    last_progress_report = progress_percent
            
            # Sonuçları hazırla
            best_parameters = dict(zip(keys, best_combination))
            results = [best_total_time]
            snr_values = [best_snr]
            
            print(f"Rastgele örnekleme değerlendirmesi tamamlandı. En iyi SNR: {best_snr:.2f}, Toplam süre: {best_total_time:.2f}")
            
        else:
            # Tam faktöriyel tasarım
            print("Tam faktöriyel tasarım kullanılıyor. Bu işlem zaman alabilir...")
            print(f"Toplam {level_count ** parameter_count} kombinasyon hesaplanacak.")
            
            # Daha verimli bir yaklaşım: Tüm kombinasyonları bir kerede oluşturmak yerine
            # her seferinde bir kombinasyon oluştur ve değerlendir
            
            # Parametre seviyelerini liste olarak hazırla
            level_lists = [parameter_levels[key] for key in keys]
            
            # En iyi kombinasyonu bulmak için değişkenler
            best_combination = None
            best_snr = float('-inf')
            best_total_time = float('inf')
            
            # İlerleme takibi için değişkenler
            total_combinations = level_count ** parameter_count
            processed_count = 0
            last_progress_report = 0
            start_time = datetime.now()
            
            print("Kombinasyonlar değerlendiriliyor...")
            
            # Her bir kombinasyonu değerlendir
            for combination in product(*level_lists):
                total_time = sum(combination)
                snr_value = calculate_snr([total_time], snr_type)
                
                # En iyi kombinasyonu güncelle
                if snr_value > best_snr:
                    best_snr = snr_value
                    best_combination = combination
                    best_total_time = total_time
                
                # İlerleme durumunu güncelle
                processed_count += 1
                progress_percent = (processed_count / total_combinations) * 100
                
                # Her %5'lik ilerleme için rapor ver
                if progress_percent - last_progress_report >= 5:
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    estimated_total_time = elapsed_time / (progress_percent / 100)
                    remaining_time = estimated_total_time - elapsed_time
                    
                    print(f"İlerleme: %{progress_percent:.1f} - "
                          f"İşlenen: {processed_count}/{total_combinations} - "
                          f"Tahmini kalan süre: {remaining_time/60:.1f} dakika")
                    
                    last_progress_report = progress_percent
            
            # Sonuçları hazırla
            best_parameters = dict(zip(keys, best_combination))
            results = [best_total_time]
            snr_values = [best_snr]
            
            print(f"Tam faktöriyel değerlendirme tamamlandı. En iyi SNR: {best_snr:.2f}, Toplam süre: {best_total_time:.2f}")
    
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

def main():
    print("Taguchi optimizasyonu başlatılıyor...")

    # Verileri yükle
    tasarim_kodlari, gecmis_veriler, gecmis_veriler_ham = load_data()
    if not tasarim_kodlari or not gecmis_veriler:
        raise Exception("Veriler yüklenemedi!")
    
    print(f"Toplam {len(tasarim_kodlari)} tasarım kodu bulundu.")
    
    # Parametre sayısını kontrol et ve kullanıcıya bilgi ver
    if len(tasarim_kodlari) > 15:
        print(f"UYARI: Çok fazla tasarım kodu ({len(tasarim_kodlari)}) bulundu.")
        print("Optimizasyon uzun sürebilir, ancak tüm tasarım kodları kullanılacak.")
        print("İşlem sırasında ilerleme durumu gösterilecektir.")
    
    # Parametre seviyelerini oluştur
    print("Parametre seviyeleri oluşturuluyor...")
    level_count = 5  # 5 seviyeli Taguchi tasarımı kullan
    parameter_levels = create_parameter_levels(tasarim_kodlari, gecmis_veriler, level_count)

    print("Taguchi optimizasyonu yapılıyor...")
    best_parameters, results, snr_values, improvement_data = taguchi_optimization(
        parameter_levels, 
        gecmis_veriler, 
        level_count=level_count,
        snr_type="smaller"  # Süre için "smaller is better"
    )
    
    # Rastgele örnekleme kullanıldı mı kontrol et
    is_random_sampling = len(tasarim_kodlari) > 15 or (level_count ** len(tasarim_kodlari)) > 1000000
    
    # Parametre etkilerini analiz et
    print("Parametre etkileri analiz ediliyor...")
    try:
        # Rastgele örnekleme için özel bir yaklaşım kullan
        if is_random_sampling:
            # Rastgele örnekleme için tüm kombinasyonları oluşturmak yerine
            # en iyi kombinasyonu ve çevresindeki kombinasyonları kullan
            best_combination = [best_parameters[key] for key in best_parameters.keys()]
            
            # Analiz için kullanılacak kombinasyonlar
            analysis_experiments = [best_combination]
            analysis_snr_values = [snr_values[0]]
            
            # Her parametre için en iyi değeri değiştirerek ek kombinasyonlar oluştur
            for i, key in enumerate(best_parameters.keys()):
                for level_value in parameter_levels[key]:
                    if abs(level_value - best_combination[i]) > 0.001:  # En iyi değerden farklıysa
                        new_combination = best_combination.copy()
                        new_combination[i] = level_value
                        
                        # Bu kombinasyonun SNR değerini hesapla
                        total_time = sum(new_combination)
                        snr_value = calculate_snr([total_time], "smaller")
                        
                        analysis_experiments.append(new_combination)
                        analysis_snr_values.append(snr_value)
            
            parameter_effects = analyze_parameter_effects(
                parameter_levels, 
                analysis_experiments, 
                analysis_snr_values,
                is_random_sampling=True
            )
        else:
            # Normal Taguchi analizi
            parameter_effects = analyze_parameter_effects(
                parameter_levels, 
                list(product(*[parameter_levels[key] for key in best_parameters.keys()])), 
                snr_values
            )
        
        # Görselleştirmeleri oluştur
        print("Görselleştirmeler oluşturuluyor...")
        create_taguchi_visualizations(parameter_effects, improvement_data)
    except Exception as e:
        print(f"Parametre etkileri analizi sırasında hata: {str(e)}")
        print("Analiz ve görselleştirme adımları atlanıyor, sadece optimum değerler kaydedilecek.")
        parameter_effects = {}

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

    # parameter_effects formatını düzelt
    formatted_parameter_effects = {}
    if parameter_effects:
        for key, value_dict in parameter_effects.items():
            if isinstance(value_dict, dict):
                # Yeni format: Her seviye için bir değer içeren sözlük
                formatted_parameter_effects[key] = {str(level): float(effect) for level, effect in value_dict.items()}
            else:
                # Eski format: Liste olarak etkiler
                formatted_parameter_effects[key] = [float(v) for v in value_dict]

    results_json = {
        "best_parameters": improved_data,
        "average_improvement": float(avg_improvement),
        "parameter_effects": formatted_parameter_effects,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
