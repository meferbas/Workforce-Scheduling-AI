import json
import os
import numpy as np
import random
from ..models import TasarimKodu, Calisan, GenetikSonuc, GenetikAtama, MonteCarloSonuc
from django.db import transaction

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def load_dataset():
    """Veri setini Django modellerinden yükle"""
    try:
        tasarim_kodlari = {t.kod: {
            "urun_adi": t.urun_adi,
            "tahmini_montaj_suresi": t.tahmini_montaj_suresi,
            "personel_ihtiyaci": {
                "ustabasi": t.ustabasi,
                "kalifiyeli": t.kalifiyeli,
                "cirak": t.cirak
            }
        } for t in TasarimKodu.objects.all()}

        calisanlar = {c.ad_soyad: {
            "id": c.id,
            "yetkinlik_seviyesi": c.yetkinlik_seviyesi,
            "tecrube_yili": c.tecrube_yili,
            "verimlilik_puani": c.verimlilik_puani
        } for c in Calisan.objects.all()}

        return tasarim_kodlari, calisanlar
    except Exception as e:
        print(f"Veri yükleme hatası: {str(e)}")
        return None, None

def load_monte_carlo_results():
    """Monte Carlo simülasyon sonuçlarını Django modellerinden yükle"""
    try:
        sonuclar = {'calisanlar': {}}
        for sonuc in MonteCarloSonuc.objects.select_related('calisan').all():
            sonuclar['calisanlar'][sonuc.calisan.ad_soyad] = {
                'risk_skoru': sonuc.risk_skoru,
                'gecikme_olasiligi': sonuc.gecikme_olasiligi,
                'ortalama_performans': sonuc.ortalama_performans
            }
        return sonuclar
    except Exception as e:
        print(f"Monte Carlo sonuçları yüklenemedi: {str(e)}")
        return None

def calculate_worker_fitness_for_task(worker_name, task_id, tasarim_kodlari, calisanlar, mc_results, is_kritik=False):
    """Belirli bir çalışan ve görev için bireysel uygunluk puanını hesaplar (0-100)."""
    worker_info = calisanlar.get(worker_name)
    task_info = tasarim_kodlari.get(task_id)
    if not worker_info or not task_info:
        return 0

    worker_level = worker_info["yetkinlik_seviyesi"]
    ihtiyac = task_info["personel_ihtiyaci"]
    
    # Çalışanın bu görevde alabileceği en yüksek yetkinlik puanını hesapla.
    # Her bir ihtiyaç seviyesi için uygunluğunu ayrı ayrı kontrol et.
    puanlar = [0.1]  # Varsayılan düşük puan
    
    # 1. Ustabası rolü için uygunluk
    if ihtiyac.get("ustabasi", 0) > 0 and worker_level == 1:
        puanlar.append(1.0)
        
    # 2. Kalifiyeli rolü için uygunluk (Ustabası da yapabilir)
    if ihtiyac.get("kalifiyeli", 0) > 0 and worker_level <= 2:
        puanlar.append(0.9 if worker_level == 2 else 0.8)

    # 3. Çırak rolü için uygunluk (Herkes yapabilir)
    if ihtiyac.get("cirak", 0) > 0 and worker_level <= 3:
        puanlar.append(0.8 if worker_level == 3 else 0.7)

    yetkinlik_puani = max(puanlar)

    # Tecrübe Puanı (normalize edilmiş)
    tecrube_puani = min(worker_info["tecrube_yili"] / 15, 1.0)

    # Verimlilik Puanı
    verimlilik_puani = worker_info["verimlilik_puani"]

    # Monte Carlo Bonus Puanı
    mc_bonus = 0
    if mc_results and worker_name in mc_results.get('calisanlar', {}):
        calisan_mc = mc_results['calisanlar'][worker_name]
        
        # Kritik işlerde riskten kaçınma, normal işlerde performansı maksimize etme
        risk_w = 0.7 if is_kritik else 0.3
        performans_w = 0.3 if is_kritik else 0.7
        
        mc_bonus = (
            (1 - calisan_mc.get('risk_skoru', 0.5)) * risk_w +
            calisan_mc.get('ortalama_performans', 0.5) * performans_w
        ) * 20 # Max 20 bonus puan

    # Ağırlıklandırma
    if is_kritik:
        # Kritik işlerde tecrübe daha önemli
        w_yetkinlik = 0.30
        w_tecrube = 0.40  # Tecrübe ağırlığı artırıldı
        w_verimlilik = 0.30
    else:
        # Normal işlerde dengeli dağılım
        w_yetkinlik = 0.40
        w_tecrube = 0.20
        w_verimlilik = 0.40
    
    base_fitness = (
        yetkinlik_puani * w_yetkinlik +
        tecrube_puani * w_tecrube +
        verimlilik_puani * w_verimlilik
    ) * 100

    total_fitness = base_fitness + mc_bonus
    return min(total_fitness, 100)

def create_initial_population(task_id, tasarim_kodlari, calisanlar, pop_size):
    """Belirli bir görev için başlangıç popülasyonu (takım atamaları) oluşturur."""
    population = []
    ihtiyac = tasarim_kodlari[task_id]["personel_ihtiyaci"]
    
    # Çalışanları seviyelerine göre grupla
    workers_by_level = {1: [], 2: [], 3: []}
    for name, info in calisanlar.items():
        workers_by_level[info["yetkinlik_seviyesi"]].append(name)

    for _ in range(pop_size):
        individual = {}
        # Her seviye için gerekli sayıda, tekrarlanmayacak şekilde rastgele çalışan seç
        for seviye_str, seviye_int in [("ustabasi", 1), ("kalifiyeli", 2), ("cirak", 3)]:
            gereken_sayi = ihtiyac.get(seviye_str, 0)
            if gereken_sayi > 0:
                # O seviyedeki çalışan havuzundan rastgele seç
                aday_havuzu = workers_by_level.get(seviye_int, [])
                if len(aday_havuzu) >= gereken_sayi:
                    individual[seviye_str] = random.sample(aday_havuzu, gereken_sayi)
                else: # Yeterli çalışan yoksa, olanları ata
                    individual[seviye_str] = aday_havuzu
        population.append(individual)
    return population

def calculate_team_fitness(individual, task_id, tasarim_kodlari, calisanlar, mc_results, is_kritik):
    """Bir takımın (bireyin) toplam uygunluk puanını hesaplar."""
    total_fitness = 0
    # Atanan tüm çalışanların bireysel puanlarını topla
    for seviye, calisan_listesi in individual.items():
        for calisan_adi in calisan_listesi:
            total_fitness += calculate_worker_fitness_for_task(
                calisan_adi, task_id, tasarim_kodlari, calisanlar, mc_results, is_kritik
            )
    
    # İhtiyaç karşılanmadıysa ceza puanı uygula (çok önemli)
    ihtiyac = tasarim_kodlari[task_id]["personel_ihtiyaci"]
    for seviye, gereken_sayi in ihtiyac.items():
        atanan_sayi = len(individual.get(seviye, []))
        if atanan_sayi < gereken_sayi:
            total_fitness *= 0.5 * (atanan_sayi / gereken_sayi) # Ağır ceza
            
    return total_fitness

def select_parents(population, fitness_scores, num_parents):
    """Turnuva seçimi ile ebeveynleri seçer."""
    parents = []
    for _ in range(num_parents):
        # 3 rastgele rakip seç
        competitors_indices = random.sample(range(len(population)), k=min(3, len(population)))
        # Rakiplerin uygunluk puanlarını al
        fitness_values = [fitness_scores[i] for i in competitors_indices]
        # En yüksek puana sahip olanı ebeveyn olarak seç
        winner_index = competitors_indices[np.argmax(fitness_values)]
        parents.append(population[winner_index])
    return parents

def crossover(parent1, parent2):
    """İki ebeveynden yeni bir çocuk (takım) oluşturur (çaprazlama)."""
    child = {}
    all_workers_p1 = set(w for L in parent1.values() for w in L)
    all_workers_p2 = set(w for L in parent2.values() for w in L)

    for seviye in parent1.keys():
        # Her seviyedeki çalışanları birleştir ve benzersiz olanları al
        combined_workers = list(set(parent1.get(seviye, []) + parent2.get(seviye, [])))
        # Gereken sayıda rastgele seç
        gereken_sayi = len(parent1.get(seviye, []))
        if len(combined_workers) >= gereken_sayi:
            child[seviye] = random.sample(combined_workers, gereken_sayi)
        else:
            child[seviye] = combined_workers # Yeterli aday yoksa hepsi
    return child

def mutate(individual, calisanlar):
    """Bir takımda rastgele bir çalışanı aynı seviyedeki başka bir çalışanla değiştirir (mutasyon)."""
    mutated_individual = individual.copy()
    
    # Mutasyona uğrayacak seviyeyi rastgele seç
    if not mutated_individual: return mutated_individual
    level_to_mutate = random.choice(list(mutated_individual.keys()))
    
    if not mutated_individual[level_to_mutate]: return mutated_individual
    
    # Değiştirilecek çalışanı seç
    worker_to_replace = random.choice(mutated_individual[level_to_mutate])

    # O seviyedeki tüm çalışanları bul
    seviye_int_map = {"ustabasi": 1, "kalifiyeli": 2, "cirak": 3}
    level_int = seviye_int_map[level_to_mutate]
    potential_replacements = [
        name for name, info in calisanlar.items() 
        if info["yetkinlik_seviyesi"] == level_int and name not in mutated_individual[level_to_mutate]
    ]

    if potential_replacements:
        # Yeni bir çalışan seç
        new_worker = random.choice(potential_replacements)
        # Değiştir
        mutated_individual[level_to_mutate].remove(worker_to_replace)
        mutated_individual[level_to_mutate].append(new_worker)

    return mutated_individual

@transaction.atomic
def save_genetic_results(task_id, best_team, tasarim_kodlari, calisanlar, mc_results, is_kritik):
    """
    En iyi takımı 'atanan' olarak, diğer TÜM çalışanları ise 'alternatif' olarak,
    bireysel uygunluk puanlarına göre sıralayarak kaydeder.
    """
    try:
        tasarim = TasarimKodu.objects.get(kod=task_id)
        senaryo = "kritik" if is_kritik else "normal"
        
        # Bu görev/senaryo için önceki sonuçları temizle
        GenetikSonuc.objects.filter(tasarim=tasarim, senaryo=senaryo).delete()
        
        sonuc_obj = GenetikSonuc.objects.create(tasarim=tasarim, senaryo=senaryo)

        # 1. 'Atanan' çalışanları kaydet
        assigned_worker_names = set()
        for seviye_str, calisan_listesi in best_team.items():
            for worker_name in calisan_listesi:
                assigned_worker_names.add(worker_name)
                try:
                    calisan = Calisan.objects.get(ad_soyad=worker_name)
                    GenetikAtama.objects.create(
                        sonuc=sonuc_obj,
                        calisan=calisan,
                        seviye=seviye_str,
                        atanma_tipi="atanan",
                        uygunluk_orani=calculate_worker_fitness_for_task(
                            worker_name, task_id, tasarim_kodlari, calisanlar, mc_results, is_kritik
                        )
                    )
                except Calisan.DoesNotExist:
                    print(f"Atanan çalışan bulunamadı: {worker_name}")

        # 2. Diğer TÜM çalışanları 'alternatif' olarak kaydet
        all_worker_names = set(calisanlar.keys())
        alternative_worker_names = all_worker_names - assigned_worker_names

        for worker_name in alternative_worker_names:
            try:
                calisan = Calisan.objects.get(ad_soyad=worker_name)
                seviye_int = calisan.yetkinlik_seviyesi
                seviye_str = "ustabasi" if seviye_int == 1 else "kalifiyeli" if seviye_int == 2 else "cirak"

                fitness = calculate_worker_fitness_for_task(
                    worker_name, task_id, tasarim_kodlari, calisanlar, mc_results, is_kritik
                )

                GenetikAtama.objects.create(
                    sonuc=sonuc_obj,
                    calisan=calisan,
                    seviye=seviye_str,
                    atanma_tipi="alternatif",
                    uygunluk_orani=fitness
                )
            except Calisan.DoesNotExist:
                print(f"Alternatif çalışan bulunamadı: {worker_name}")
        
        print(f"'{task_id}' için sonuçlar kaydedildi. Atanan: {len(assigned_worker_names)}, Alternatif: {len(alternative_worker_names)}")
        return True
    except Exception as e:
        print(f"'{task_id}' için sonuçlar kaydedilemedi: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def genetic_algorithm_for_task(task_id, tasarim_kodlari, calisanlar, mc_results, is_kritik=False,
                               pop_size=50, generations=100, mutation_rate=0.1):
    """Tek bir görev için genetik algoritmayı çalıştırır ve en iyi takımı döndürür."""
    
    print(f"'{task_id}' görevi için GA başlatılıyor ({'kritik' if is_kritik else 'normal'})...")
    
    # 1. Başlangıç popülasyonu
    population = create_initial_population(task_id, tasarim_kodlari, calisanlar, pop_size)
    best_overall_fitness = -1
    best_overall_individual = None

    # 2. Nesiller boyu evrim
    for gen in range(generations):
        # Uygunluk hesapla
        fitness_scores = [calculate_team_fitness(ind, task_id, tasarim_kodlari, calisanlar, mc_results, is_kritik) for ind in population]

        # En iyi bireyi takip et
        best_gen_fitness = max(fitness_scores)
        if best_gen_fitness > best_overall_fitness:
            best_overall_fitness = best_gen_fitness
            best_overall_individual = population[np.argmax(fitness_scores)]

        # Ebeveyn seçimi
        parents = select_parents(population, fitness_scores, pop_size)
        
        # Yeni nesil oluşturma
        next_population = []
        for i in range(0, pop_size, 2):
            if i + 1 < len(parents):
                parent1, parent2 = parents[i], parents[i+1]
                child1 = crossover(parent1, parent2)
                child2 = crossover(parent1, parent2)
                
                # Mutasyon
                if random.random() < mutation_rate:
                    child1 = mutate(child1, calisanlar)
                if random.random() < mutation_rate:
                    child2 = mutate(child2, calisanlar)
                    
                next_population.extend([child1, child2])
        
        population = next_population[:pop_size] # Popülasyon boyutunu koru

    print(f"'{task_id}' için en iyi takım uygunluğu: {best_overall_fitness:.2f}")
    return best_overall_individual

def main():
    print("Genetik Algoritma Optimizasyonu Başlatılıyor...")
    tasarim_kodlari, calisanlar = load_dataset()
    mc_results = load_monte_carlo_results()

    if not tasarim_kodlari or not calisanlar or not mc_results:
        print("Veri yüklenemedi, işlem durduruluyor.")
        return

    all_tasks = list(tasarim_kodlari.keys())

    for senaryo in ["normal", "kritik"]:
        is_kritik_senaryo = (senaryo == "kritik")
        print(f"\n--- {senaryo.upper()} SENARYOSU İŞLENİYOR ---")
        
        for task in all_tasks:
            # Her görev için en iyi takımı bul
            best_team = genetic_algorithm_for_task(
                task, tasarim_kodlari, calisanlar, mc_results, is_kritik=is_kritik_senaryo
            )
            
            if best_team:
                # Sonuçları kaydet (atananlar + tüm alternatifler)
                save_genetic_results(
                    task, best_team, tasarim_kodlari, calisanlar, mc_results, is_kritik=is_kritik_senaryo
                )
            else:
                print(f"'{task}' için uygun takım bulunamadı.")

    print("\nGenetik Algoritma Optimizasyonu Tamamlandı.")

if __name__ == '__main__':
    main()
