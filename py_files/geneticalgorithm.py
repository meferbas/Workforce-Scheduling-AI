import json
import os
import numpy as np
import copy

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
    
    return total_fitness / task_count

def calculate_worker_fitness_for_task(worker, task, tasarim_kodlari, calisan_yetkinlikleri, verbose=False):
    """Belirli görev için çalışanın skorunu hesapla (0-100)."""
    # Eğer worker bir liste ise, ilk elemanı al
    if isinstance(worker, list):
        if not worker:  # Boş liste kontrolü
            return 0
        worker = worker[0]  # İlk çalışanı al
    
    # Çalışanın yetkinlik seviyesi
    calisan_seviyesi = calisan_yetkinlikleri[worker]["yetkinlik_seviyesi"]
    
    # Görevin personel ihtiyacı
    personel_ihtiyaci = tasarim_kodlari[task].get("personel_ihtiyaci", {
        "ustabasi": 0,
        "kalifiyeli": 0,
        "cirak": 0
    })
    
    # Yetkinlik uyumu: Çalışanın seviyesi görev için uygun mu?
    # 1 (Ustabaşı) > 2 (Kalifiyeli) > 3 (Çömez)
    yetkinlik_uyumu = 0.5  # Varsayılan değer
    
    if calisan_seviyesi == 1 and personel_ihtiyaci.get("ustabasi", 0) > 0:
        # Ustabaşı ihtiyacı varsa ve çalışan ustabaşı ise
        yetkinlik_uyumu = 1.0
    elif calisan_seviyesi == 2 and personel_ihtiyaci.get("kalifiyeli", 0) > 0:
        # Kalifiyeli ihtiyacı varsa ve çalışan kalifiyeli ise
        yetkinlik_uyumu = 1.0
    elif calisan_seviyesi == 3 and personel_ihtiyaci.get("cirak", 0) > 0:
        # Çırak ihtiyacı varsa ve çalışan çırak ise
        yetkinlik_uyumu = 1.0
    
    # Tecrübe puanı
    tecrube_puani = min(calisan_yetkinlikleri[worker]["tecrube_yili"] / 10, 1)
    
    # Verimlilik puanı
    verimlilik_puani = calisan_yetkinlikleri[worker]["verimlilik_puani"]
    
    # Toplam uygunluk skoru
    fitness = (yetkinlik_uyumu * 0.5 + tecrube_puani * 0.25 + verimlilik_puani * 0.25) * 100

    if verbose:
        print(f"[DEBUG] {worker}-{task} -> {fitness:.2f} (Seviye: {calisan_seviyesi}, Uyum: {yetkinlik_uyumu})")
    
    return fitness

def find_best_workers_for_task_by_level(task, level, tasarim_kodlari, calisan_yetkinlikleri, verbose=False):
    """Belirli bir yetkinlik seviyesi için en iyi çalışanları bul."""
    worker_scores = []
    for worker, info in calisan_yetkinlikleri.items():
        if info["yetkinlik_seviyesi"] == level:
            sc = calculate_worker_fitness_for_task(worker, task, tasarim_kodlari, calisan_yetkinlikleri, verbose=verbose)
            worker_scores.append((worker, sc))
    
    sorted_w = sorted(worker_scores, key=lambda x: -x[1])
    return sorted_w

def genetic_algorithm(tasarim_kodlari, calisan_yetkinlikleri, verbose=False):
    """
    Her tasarım kodu için gereken personel ihtiyacına göre en uygun çalışanları atar.
    """
    tasks = list(tasarim_kodlari.keys())
    if not tasks:
        return {}, [], {}

    # Her görev için seviye bazlı en iyi çalışanlar
    task_worker_rankings = {}
    assignment = {}

    # Çalışanları seviyelerine göre grupla
    workers_by_level = {1: [], 2: [], 3: []}
    for worker, info in calisan_yetkinlikleri.items():
        level = info["yetkinlik_seviyesi"]
        workers_by_level[level].append(worker)

    # Her görev için personel ihtiyacına göre en iyi çalışanları bul
    for task in tasks:
        personel_ihtiyaci = tasarim_kodlari[task].get("personel_ihtiyaci", {
            "ustabasi": 0,
            "kalifiyeli": 0,
            "cirak": 0
        })
        
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
        
        # Atama yapılacak çalışanlar
        assigned_workers = []
        
        # Ustabaşı ataması
        ustabasi_count = personel_ihtiyaci.get("ustabasi", 0)
        if ustabasi_count > 0 and ustabasi_rankings:
            assigned_workers.extend([w for w, _ in ustabasi_rankings[:ustabasi_count]])
        
        # Kalifiye ataması
        kalifiyeli_count = personel_ihtiyaci.get("kalifiyeli", 0)
        if kalifiyeli_count > 0 and kalifiyeli_rankings:
            assigned_workers.extend([w for w, _ in kalifiyeli_rankings[:kalifiyeli_count]])
        
        # Çırak ataması
        cirak_count = personel_ihtiyaci.get("cirak", 0)
        if cirak_count > 0 and cirak_rankings:
            assigned_workers.extend([w for w, _ in cirak_rankings[:cirak_count]])
        
        # Atamayı kaydet
        assignment[task] = assigned_workers

    return assignment, [], task_worker_rankings

def main():
    tasarim_kodlari, calisanlar = load_dataset()
    if not tasarim_kodlari or not calisanlar:
        print("Veri setleri yüklenemedi!")
        return

    best_assignment, _, ranking = genetic_algorithm(tasarim_kodlari, calisanlar, verbose=False)

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

if __name__ == "__main__":
    main()
