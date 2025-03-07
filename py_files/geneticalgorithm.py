import json
import os
import numpy as np
import copy
import random

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def load_dataset():
    """Veri setini yükle"""
    try:
        with open(os.path.join(ROOT_DIR, 'veri', 'tasarim_kodlari.json'), 'r', encoding='utf-8') as f:
            tasarim_kodlari = json.load(f)
        with open(os.path.join(ROOT_DIR, 'veri', 'calisan_yetkinlikleri.json'), 'r', encoding='utf-8') as f:
            calisan_yetkinlikleri = json.load(f)
        return tasarim_kodlari, calisan_yetkinlikleri
    except Exception as e:
        print(f"load_dataset hatası: {str(e)}")
        return None, None

def load_monte_carlo_results():
    """Monte Carlo simülasyon sonuçlarını yükle"""
    try:
        with open(os.path.join(ROOT_DIR, 'veri', 'monte_carlo_sonuclari.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Monte Carlo sonuçları yüklenemedi: {str(e)}")
        return None

def calculate_fitness(assignment, tasarim_kodlari, calisan_yetkinlikleri):
    """
    Her atama için uygunluk skoru (0-100).
    """
    total_fitness = 0
    if not assignment:
        return 0
    
    task_count = 0
    for task_id, workers in assignment.items():
        if not workers:
            continue
        
        task_fitness = 0
        for worker in workers:
            worker_fitness = calculate_worker_fitness_for_task(worker, task_id, tasarim_kodlari, calisan_yetkinlikleri)
            task_fitness += worker_fitness
        
        if len(workers) > 0:
            task_fitness /= len(workers)
            total_fitness += task_fitness
            task_count += 1
    
    if task_count == 0:
        return 0
    
    # İş yükü dengesini de hesaba kat
    worker_load = {}
    for task_id, workers in assignment.items():
        for worker in workers:
            if worker not in worker_load:
                worker_load[worker] = 0
            worker_load[worker] += 1
    
    # İş yükü dengesizliği cezası
    if worker_load:
        load_std = np.std(list(worker_load.values()))
        load_penalty = min(load_std * 5, 20)  # Maksimum %20 ceza
        total_fitness = total_fitness * (1 - load_penalty / 100)
    
    return total_fitness / task_count

def calculate_worker_fitness_for_task(worker, task, tasarim_kodlari, calisan_yetkinlikleri, verbose=False, is_kritik=False):
    """Belirli görev için çalışanın skorunu hesapla (0-100)."""
    # Monte Carlo sonuçlarını yükle
    mc_sonuclari = load_monte_carlo_results()
    
    # Eğer worker bir liste ise, ilk elemanı al
    if isinstance(worker, list):
        if not worker:  # Boş liste kontrolü
            return 0
        worker = worker[0]  # İlk çalışanı al
    
    # Temel uygunluk skorunu hesapla
    base_fitness = 0
    
    # Çalışanın yetkinlik seviyesi
    calisan_seviyesi = calisan_yetkinlikleri[worker]["yetkinlik_seviyesi"]
    
    # Görevin personel ihtiyacı
    personel_ihtiyaci = tasarim_kodlari[task].get("personel_ihtiyaci", {
        "ustabasi": 0,
        "kalifiyeli": 0,
        "cirak": 0
    })
    
    # Yetkinlik uyumu hesapla
    yetkinlik_uyumu = 0.5  # Varsayılan değer
    if calisan_seviyesi == 1 and personel_ihtiyaci.get("ustabasi", 0) > 0:
        yetkinlik_uyumu = 1.0
    elif calisan_seviyesi == 2 and personel_ihtiyaci.get("kalifiyeli", 0) > 0:
        yetkinlik_uyumu = 1.0
    elif calisan_seviyesi == 3 and personel_ihtiyaci.get("cirak", 0) > 0:
        yetkinlik_uyumu = 1.0
    
    # Tecrübe puanı
    tecrube_puani = min(calisan_yetkinlikleri[worker]["tecrube_yili"] / 10, 1)
    
    # Verimlilik puanı
    verimlilik_puani = calisan_yetkinlikleri[worker]["verimlilik_puani"]
    
    # Monte Carlo sonuçlarını kullan (eğer varsa)
    mc_bonus = 0
    if mc_sonuclari and worker in mc_sonuclari['calisanlar']:
        calisan_mc = mc_sonuclari['calisanlar'][worker]
        
        if is_kritik:
            # Kritik işler için Monte Carlo metriklerini daha fazla ağırlıklandır
            mc_bonus = (
                (1 - calisan_mc['risk_skoru']) * 0.4 +  # Düşük risk skoru bonus verir
                (1 - calisan_mc['gecikme_olasiligi']) * 0.4 +  # Düşük gecikme olasılığı bonus verir
                calisan_mc['ortalama_performans'] * 0.2  # Yüksek ortalama performans bonus verir
            ) * 20  # Monte Carlo bonusunu 20 puan ile sınırla
    
    # Toplam uygunluk skoru
    base_fitness = (yetkinlik_uyumu * 0.5 + tecrube_puani * 0.25 + verimlilik_puani * 0.25) * 100
    
    # Monte Carlo bonusunu ekle
    total_fitness = base_fitness + mc_bonus
    
    if verbose:
        print(f"[DEBUG] {worker}-{task} -> Base: {base_fitness:.2f}, MC Bonus: {mc_bonus:.2f}, Total: {total_fitness:.2f}")
    
    return min(total_fitness, 100)  # Maksimum 100 puan

def find_best_workers_for_task_by_level(task, level, tasarim_kodlari, calisan_yetkinlikleri, verbose=False):
    """Belirli bir yetkinlik seviyesi için en iyi çalışanları bul."""
    worker_scores = []
    for worker, info in calisan_yetkinlikleri.items():
        if info["yetkinlik_seviyesi"] == level:
            sc = calculate_worker_fitness_for_task(worker, task, tasarim_kodlari, calisan_yetkinlikleri, verbose=verbose)
            worker_scores.append((worker, sc))
    
    sorted_w = sorted(worker_scores, key=lambda x: -x[1])
    return sorted_w

def create_initial_population(tasks, workers_by_level, tasarim_kodlari, population_size=20):
    """Başlangıç popülasyonunu oluştur"""
    population = []
    
    for _ in range(population_size):
        assignment = {}
        
        for task in tasks:
            personel_ihtiyaci = tasarim_kodlari[task].get("personel_ihtiyaci", {
                "ustabasi": 0,
                "kalifiyeli": 0,
                "cirak": 0
            })
            
            assigned_workers = []
            
            # Ustabaşı ataması
            ustabasi_count = personel_ihtiyaci.get("ustabasi", 0)
            if ustabasi_count > 0 and workers_by_level[1]:
                # Rastgele seçim
                available_workers = workers_by_level[1].copy()
                random.shuffle(available_workers)
                assigned_workers.extend(available_workers[:ustabasi_count])
            
            # Kalifiye ataması
            kalifiyeli_count = personel_ihtiyaci.get("kalifiyeli", 0)
            if kalifiyeli_count > 0 and workers_by_level[2]:
                available_workers = workers_by_level[2].copy()
                random.shuffle(available_workers)
                assigned_workers.extend(available_workers[:kalifiyeli_count])
            
            # Çırak ataması
            cirak_count = personel_ihtiyaci.get("cirak", 0)
            if cirak_count > 0 and workers_by_level[3]:
                available_workers = workers_by_level[3].copy()
                random.shuffle(available_workers)
                assigned_workers.extend(available_workers[:cirak_count])
            
            assignment[task] = assigned_workers
        
        population.append(assignment)
    
    return population

def crossover(parent1, parent2, crossover_rate=0.7):
    """İki ebeveyn arasında çaprazlama yap"""
    if random.random() > crossover_rate:
        return copy.deepcopy(parent1)
    
    child = {}
    tasks = list(parent1.keys())
    
    # Rastgele bir kesim noktası seç
    crossover_point = random.randint(1, len(tasks) - 1)
    
    # İlk kısım parent1'den, ikinci kısım parent2'den
    for i, task in enumerate(tasks):
        if i < crossover_point:
            child[task] = copy.deepcopy(parent1[task])
        else:
            child[task] = copy.deepcopy(parent2[task])
    
    return child

def mutate(assignment, workers_by_level, tasarim_kodlari, mutation_rate=0.2):
    """Mutasyon uygula"""
    mutated = copy.deepcopy(assignment)
    
    for task in mutated.keys():
        if random.random() > mutation_rate:
            continue
        
        personel_ihtiyaci = tasarim_kodlari[task].get("personel_ihtiyaci", {
            "ustabasi": 0,
            "kalifiyeli": 0,
            "cirak": 0
        })
        
        # Rastgele bir çalışan seviyesi seç ve değiştir
        level = random.choice([1, 2, 3])
        
        if level == 1 and personel_ihtiyaci.get("ustabasi", 0) > 0 and workers_by_level[1]:
            # Ustabaşı değişimi
            current_ustabasi = [w for w in mutated[task] if w in workers_by_level[1]]
            if current_ustabasi:
                # Rastgele bir ustabaşını değiştir
                worker_to_replace = random.choice(current_ustabasi)
                available_workers = [w for w in workers_by_level[1] if w not in mutated[task]]
                if available_workers:
                    new_worker = random.choice(available_workers)
                    mutated[task] = [new_worker if w == worker_to_replace else w for w in mutated[task]]
        
        elif level == 2 and personel_ihtiyaci.get("kalifiyeli", 0) > 0 and workers_by_level[2]:
            # Kalifiyeli değişimi
            current_kalifiyeli = [w for w in mutated[task] if w in workers_by_level[2]]
            if current_kalifiyeli:
                worker_to_replace = random.choice(current_kalifiyeli)
                available_workers = [w for w in workers_by_level[2] if w not in mutated[task]]
                if available_workers:
                    new_worker = random.choice(available_workers)
                    mutated[task] = [new_worker if w == worker_to_replace else w for w in mutated[task]]
        
        elif level == 3 and personel_ihtiyaci.get("cirak", 0) > 0 and workers_by_level[3]:
            # Çırak değişimi
            current_cirak = [w for w in mutated[task] if w in workers_by_level[3]]
            if current_cirak:
                worker_to_replace = random.choice(current_cirak)
                available_workers = [w for w in workers_by_level[3] if w not in mutated[task]]
                if available_workers:
                    new_worker = random.choice(available_workers)
                    mutated[task] = [new_worker if w == worker_to_replace else w for w in mutated[task]]
    
    return mutated

def select_parents(population, fitness_scores, num_parents):
    """Turnuva seçimi ile ebeveynleri seç"""
    parents = []
    
    for _ in range(num_parents):
        # Rastgele 3 birey seç
        tournament_size = min(3, len(population))
        tournament_indices = random.sample(range(len(population)), tournament_size)
        
        # En iyi uygunluk değerine sahip bireyi seç
        best_idx = tournament_indices[0]
        for idx in tournament_indices:
            if fitness_scores[idx] > fitness_scores[best_idx]:
                best_idx = idx
        
        parents.append(population[best_idx])
    
    return parents

def genetic_algorithm(tasarim_kodlari, calisan_yetkinlikleri, 
                     population_size=20, generations=50, 
                     crossover_rate=0.7, mutation_rate=0.2, 
                     verbose=False, ilerleme_callback=None):
    """
    Genetik algoritma ile iş-çalışan ataması yapar.
    
    Parameters:
    -----------
    tasarim_kodlari : dict
        Tasarım kodları bilgileri
    calisan_yetkinlikleri : dict
        Çalışan yetkinlikleri bilgileri
    population_size : int
        Popülasyon büyüklüğü
    generations : int
        Nesil sayısı
    crossover_rate : float
        Çaprazlama oranı
    mutation_rate : float
        Mutasyon oranı
    verbose : bool
        Detaylı çıktı gösterme
    ilerleme_callback : function
        İlerleme durumunu bildirmek için callback fonksiyonu
        
    Returns:
    --------
    tuple
        (en_iyi_atama, fitness_gecmisi, gorev_calisan_siralamasi)
    """
    tasks = list(tasarim_kodlari.keys())
    if not tasks:
        return {}, [], {}

    # Çalışanları seviyelerine göre grupla
    workers_by_level = {1: [], 2: [], 3: []}
    for worker, info in calisan_yetkinlikleri.items():
        level = info["yetkinlik_seviyesi"]
        workers_by_level[level].append(worker)

    # Başlangıç popülasyonunu oluştur
    population = create_initial_population(tasks, workers_by_level, tasarim_kodlari, population_size)
    
    # Her görev için seviye bazlı en iyi çalışanlar
    task_worker_rankings = {}
    for task in tasks:
        # Seviye bazlı en iyi çalışanları bul
        ustabasi_rankings = find_best_workers_for_task_by_level(task, 1, tasarim_kodlari, calisan_yetkinlikleri, verbose)
        kalifiyeli_rankings = find_best_workers_for_task_by_level(task, 2, tasarim_kodlari, calisan_yetkinlikleri, verbose)
        cirak_rankings = find_best_workers_for_task_by_level(task, 3, tasarim_kodlari, calisan_yetkinlikleri, verbose)
        
        # Tüm sıralamaları kaydet
        task_worker_rankings[task] = {
            "ustabasi": ustabasi_rankings,
            "kalifiyeli": kalifiyeli_rankings,
            "cirak": cirak_rankings
        }
    
    # Nesiller boyunca evrim
    best_assignment = None
    best_fitness = -1
    fitness_history = []
    
    for generation in range(generations):
        # Popülasyondaki her bireyin uygunluğunu hesapla
        fitness_scores = [calculate_fitness(assignment, tasarim_kodlari, calisan_yetkinlikleri) 
                         for assignment in population]
        
        # En iyi bireyi bul
        best_idx = np.argmax(fitness_scores)
        current_best = population[best_idx]
        current_best_fitness = fitness_scores[best_idx]
        
        # Genel en iyi çözümü güncelle
        if current_best_fitness > best_fitness:
            best_assignment = copy.deepcopy(current_best)
            best_fitness = current_best_fitness
        
        fitness_history.append(current_best_fitness)
        
        if verbose and generation % 10 == 0:
            print(f"Nesil {generation}: En iyi uygunluk = {current_best_fitness:.2f}")
        
        # İlerleme bildirimi
        if ilerleme_callback:
            ilerleme_callback(generation+1, generations, best_fitness)
        
        # Yeni nesil oluştur
        new_population = []
        
        # Elitizm: En iyi bireyi doğrudan yeni nesile aktar
        new_population.append(current_best)
        
        # Çaprazlama ve mutasyon ile yeni bireyler oluştur
        while len(new_population) < population_size:
            # Ebeveyn seçimi
            parents = select_parents(population, fitness_scores, 2)
            
            # Çaprazlama
            child = crossover(parents[0], parents[1], crossover_rate)
            
            # Mutasyon
            child = mutate(child, workers_by_level, tasarim_kodlari, mutation_rate)
            
            new_population.append(child)
        
        population = new_population
    
    # Son popülasyonun uygunluğunu hesapla
    final_fitness_scores = [calculate_fitness(assignment, tasarim_kodlari, calisan_yetkinlikleri) 
                           for assignment in population]
    best_idx = np.argmax(final_fitness_scores)
    
    # En iyi çözümü döndür
    if final_fitness_scores[best_idx] > best_fitness:
        best_assignment = population[best_idx]
        best_fitness = final_fitness_scores[best_idx]
    
    if verbose:
        print(f"Optimizasyon tamamlandı. En iyi uygunluk = {best_fitness:.2f}")
    
    return best_assignment, fitness_history, task_worker_rankings

def main():
    tasarim_kodlari, calisanlar = load_dataset()
    if not tasarim_kodlari or not calisanlar:
        print("Veri setleri yüklenemedi!")
        return

    best_assignment, fitness_history, ranking = genetic_algorithm(
        tasarim_kodlari, 
        calisanlar, 
        population_size=30,  # Popülasyon boyutu
        generations=100,     # Nesil sayısı
        crossover_rate=0.8,  # Çaprazlama oranı
        mutation_rate=0.2,   # Mutasyon oranı
        verbose=True,        # Detaylı çıktı
        ilerleme_callback=None  # İlerleme bildirimi için None
    )

    results = {}
    for task, workers in best_assignment.items():
        personel_ihtiyaci = tasarim_kodlari[task].get("personel_ihtiyaci", {
            "ustabasi": 0,
            "kalifiyeli": 0,
            "cirak": 0
        })
        
        # Atanan çalışanları seviyelerine göre grupla
        atanan_calisanlar = {
            "ustabasi": [],
            "kalifiyeli": [],
            "cirak": []
        }
        
        for worker in workers:
            level = calisanlar[worker]["yetkinlik_seviyesi"]
            if level == 1:
                atanan_calisanlar["ustabasi"].append(worker)
            elif level == 2:
                atanan_calisanlar["kalifiyeli"].append(worker)
            else:
                atanan_calisanlar["cirak"].append(worker)
        
        # Eksik personel sayılarını hesapla
        eksik_personel = {
            "ustabasi": max(0, personel_ihtiyaci.get("ustabasi", 0) - len(atanan_calisanlar["ustabasi"])),
            "kalifiyeli": max(0, personel_ihtiyaci.get("kalifiyeli", 0) - len(atanan_calisanlar["kalifiyeli"])),
            "cirak": max(0, personel_ihtiyaci.get("cirak", 0) - len(atanan_calisanlar["cirak"]))
        }
        
        # Alternatif çalışanları seviyelerine göre grupla
        alternatif_calisanlar = []
        
        # Her seviye için alternatif çalışanları ekle
        for level_name, level_rankings in ranking[task].items():
            for worker, score in level_rankings:
                if worker not in workers:  # Atanmamış çalışanları alternatif olarak ekle
                    alternatif_calisanlar.append({
                        "calisan": worker,
                        "uygunluk": score,
                        "seviye": level_name  # Seviye bilgisini ekle
                    })
        
        results[task] = {
            "atanan_calisanlar": atanan_calisanlar,
            "eksik_personel": eksik_personel,
            "alternatif_calisanlar": alternatif_calisanlar,
            "personel_ihtiyaci": personel_ihtiyaci
        }

    output = os.path.join(ROOT_DIR, 'veri', 'genetik_sonuclari.json')
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    print(f"Genetik sonuç kaydedildi: {output}")
    
    # Fitness geçmişini de kaydet
    fitness_history_output = os.path.join(ROOT_DIR, 'veri', 'genetik_fitness_history.json')
    with open(fitness_history_output, 'w', encoding='utf-8') as f:
        json.dump({"fitness_history": fitness_history}, f, indent=4)
    print(f"Fitness geçmişi kaydedildi: {fitness_history_output}")

if __name__ == "__main__":
    main()
