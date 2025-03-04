# monte_carlo.py

import random
import json
import copy
import numpy as np
import os

# Genetik algoritma ve veri yükleme fonksiyonlarını import et
from geneticalgorithm import genetic_algorithm, load_dataset, calculate_fitness

def simulate_worker_states(original_workers,
                           absence_prob=0.05,
                           performance_std=0.05):
    """
    Her çalışanın aynı devamsızlık olasılığı (absence_prob) ve
    küçük bir performans dalgalanması (performance_std) ile
    simüle edilir.
    
    Yeni yapıda yetkinlik seviyesi değişmez, sadece verimlilik puanı değişir.
    """
    updated_workers = copy.deepcopy(original_workers)

    for worker_name, info in updated_workers.items():
        # 1) Gelmeme
        if random.random() < absence_prob:
            updated_workers[worker_name]["verimlilik_puani"] = 0
            continue

        # 2) Performans dalgalanması
        mean_perf = info["verimlilik_puani"]
        new_perf = random.gauss(mean_perf, performance_std)

        if new_perf < 0:
            new_perf = 0
        elif new_perf > 1:
            new_perf = 1

        updated_workers[worker_name]["verimlilik_puani"] = new_perf

    return updated_workers

def run_monte_carlo_simulation(tasarim_kodlari,
                               calisan_yetkinlikleri,
                               aktif_isler=[],
                               n_scenarios=50,
                               absence_prob=0.05,
                               performance_std=0.05):
    """
    n_scenarios kez çalışanların devamsızlığını/perf dalgalanmasını
    simüle ederek Genetik Algoritmayı çalıştırır ve her senaryonun
    fitness'ını kaydeder. Sonuçta ortalama, en iyi, en kötü, std döndürür.
    """
    scenario_fitness_list = []
    scenarios = []  # Her senaryonun detaylarını saklamak için
    
    # Yetkinlik seviyelerine göre çalışan dağılımını hesapla
    seviye_dagilimi = {1: 0, 2: 0, 3: 0}
    for worker, info in calisan_yetkinlikleri.items():
        seviye = info["yetkinlik_seviyesi"]
        seviye_dagilimi[seviye] += 1
    
    # Personel ihtiyacı dağılımını hesapla
    personel_ihtiyaci_dagilimi = {
        "ustabasi": 0,
        "kalifiyeli": 0,
        "cirak": 0
    }
    
    for task, info in tasarim_kodlari.items():
        ihtiyac = info.get("personel_ihtiyaci", {})
        personel_ihtiyaci_dagilimi["ustabasi"] += ihtiyac.get("ustabasi", 0)
        personel_ihtiyaci_dagilimi["kalifiyeli"] += ihtiyac.get("kalifiyeli", 0)
        personel_ihtiyaci_dagilimi["cirak"] += ihtiyac.get("cirak", 0)

    for scenario_idx in range(n_scenarios):
        updated_workers = simulate_worker_states(
            calisan_yetkinlikleri,
            absence_prob=absence_prob,
            performance_std=performance_std
        )

        # Genetik algoritma
        best_assignment, _, _ = genetic_algorithm(tasarim_kodlari, updated_workers)

        # Uygunluk skorunu hesapla
        scenario_fitness = calculate_fitness(best_assignment,
                                             tasarim_kodlari,
                                             updated_workers)
        scenario_fitness_list.append(scenario_fitness)
        
        # Senaryo detaylarını kaydet
        scenarios.append({
            "id": scenario_idx + 1,
            "fitness": float(scenario_fitness),
            "absent_workers": [w for w, info in updated_workers.items() if info["verimlilik_puani"] == 0]
        })

    avg_fitness = np.mean(scenario_fitness_list)
    std_fitness = np.std(scenario_fitness_list)
    min_fitness = np.min(scenario_fitness_list)
    max_fitness = np.max(scenario_fitness_list)

    # Sonuçları hazırla
    results = {
        "avg_fitness": float(avg_fitness),
        "std_fitness": float(std_fitness),
        "min_fitness": float(min_fitness),
        "max_fitness": float(max_fitness),
        "seviye_dagilimi": seviye_dagilimi,
        "personel_ihtiyaci_dagilimi": personel_ihtiyaci_dagilimi,
        "scenarios": scenarios  # Senaryo detaylarını ekle
    }

    # Sonuçları JSON dosyasına kaydet
    output_path = os.path.join(os.path.dirname(__file__), '..', 'veri', 'monte_carlo_sonuclari.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    return results

if __name__ == "__main__":
    tasarim_kodlari, calisan_yetkinlikleri = load_dataset()
    if tasarim_kodlari and calisan_yetkinlikleri:
        results = run_monte_carlo_simulation(tasarim_kodlari, calisan_yetkinlikleri)
        print(f"Monte Carlo Sonuçları: {results}")
    else:
        print("Veri setleri yüklenemedi!")
