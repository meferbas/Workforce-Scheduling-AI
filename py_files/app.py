from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
import matplotlib
matplotlib.use('Agg')  # GUI olmayan backend kullan
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
import sys
import traceback
import numpy as np
from monte_carlo import run_monte_carlo_simulation
from taguchi import taguchi_optimization, create_parameter_levels
import shutil
from threading import Thread

# JSON dosyasını yüklemek için yardımcı fonksiyon
def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Dosya okuma hatası ({file_path}): {str(e)}")
        return None

def save_json_file(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Dosya yazma hatası ({file_path}): {str(e)}")
        return False

# py_files klasörünü Python path'ine ekle
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'py_files'))

# Modülleri import et
import taguchi
import geneticalgorithm

# Ana dizin yolunu belirle
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Veri dosyalarının yolları
TASARIM_KODLARI_JSON = os.path.join(ROOT_DIR, 'veri', 'tasarim_kodlari.json')
CALISAN_YETKINLIKLERI_JSON = os.path.join(ROOT_DIR, 'veri', 'calisan_yetkinlikleri.json')

def veri_yukle():
    """JSON dosyalarından verileri yükle"""
    global tasarim_kod_bilgileri, calisan_yetkinlikleri
    
    try:
        with open(TASARIM_KODLARI_JSON, 'r', encoding='utf-8') as f:
            tasarim_kod_bilgileri = json.load(f)
    except FileNotFoundError:
        # Dosya bulunamadığında boş bir sözlük oluştur
        tasarim_kod_bilgileri = {}
        print("UYARI: tasarim_kodlari.json dosyası bulunamadı. Boş bir sözlük oluşturuldu.")
        
    try:
        with open(CALISAN_YETKINLIKLERI_JSON, 'r', encoding='utf-8') as f:
            calisan_yetkinlikleri = json.load(f)
    except FileNotFoundError:
        # Dosya bulunamadığında boş bir sözlük oluştur
        calisan_yetkinlikleri = {}
        print("UYARI: calisan_yetkinlikleri.json dosyası bulunamadı. Boş bir sözlük oluşturuldu.")

# Template ve static klasörlerinin yollarını belirle
template_dir = os.path.join(ROOT_DIR, 'templates')
static_dir = os.path.join(ROOT_DIR, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SECRET_KEY'] = 'gizli-anahtar-123'  # SocketIO için gerekli
socketio = SocketIO(app)


# Eski klasörleri temizle ve yeni klasör yapısını oluştur
def setup_directories():
    # Ana dizindeki klasörler
    required_dirs = {
        'veri': os.path.join(ROOT_DIR, 'veri'),
        'static': os.path.join(ROOT_DIR, 'static'),
        'static/img': os.path.join(ROOT_DIR, 'static', 'img'),
    }
    
    # Eski klasörleri temizle
    old_dirs = [
        os.path.join(ROOT_DIR, 'img'),
        os.path.join(ROOT_DIR, 'py_files', 'veri'),
        os.path.join(ROOT_DIR, 'py_files', 'img')
    ]
    
    for old_dir in old_dirs:
        if os.path.exists(old_dir):
            try:
                # Eğer klasörde dosya varsa, bunları yeni konuma taşı
                if os.path.exists(required_dirs['veri']) and 'veri' in old_dir:
                    for file in os.listdir(old_dir):
                        src = os.path.join(old_dir, file)
                        dst = os.path.join(required_dirs['veri'], file)
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                elif os.path.exists(required_dirs['static/img']) and 'img' in old_dir:
                    for file in os.listdir(old_dir):
                        src = os.path.join(old_dir, file)
                        dst = os.path.join(required_dirs['static/img'], file)
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                shutil.rmtree(old_dir)
                print(f"Eski klasör temizlendi: {old_dir}")
            except Exception as e:
                print(f"Klasör temizlenirken hata oluştu {old_dir}: {str(e)}")
    
    # Yeni klasörleri oluştur
    for dir_name, dir_path in required_dirs.items():
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Yeni klasör oluşturuldu: {dir_path}")

# Uygulama başlatılırken klasörleri düzenle
setup_directories()

# Verileri yükle
veri_yukle()

# Mevcut tasarım kodlarından komplekslik değerini kaldır
if os.path.exists(TASARIM_KODLARI_JSON):
    with open(TASARIM_KODLARI_JSON, 'r', encoding='utf-8') as f:
        tasarim_kod_bilgileri = json.load(f)
        for kod in tasarim_kod_bilgileri:
            if 'komplekslik' in tasarim_kod_bilgileri[kod]:
                del tasarim_kod_bilgileri[kod]['komplekslik']
    with open(TASARIM_KODLARI_JSON, 'w', encoding='utf-8') as f:
        json.dump(tasarim_kod_bilgileri, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tasarim-kodlari')
def tasarim_kodlari():
    return render_template('tasarim_kodlari.html', tasarim_kodlari=tasarim_kod_bilgileri)

@app.route('/calisanlar')
def calisanlar():
    return render_template('calisanlar.html', calisanlar=calisan_yetkinlikleri)

@app.route('/is-cizelgesi')
def is_cizelgesi():
    try:
        # İş listesini oku
        if not os.path.exists('veri/is_listesi.json'):
            is_listesi = []
        else:
            with open('veri/is_listesi.json', 'r', encoding='utf-8') as f:
                is_listesi = json.load(f)
        
        # Gantt şeması oluştur
        
        return render_template('is_cizelgesi.html', 
                             is_listesi=is_listesi,
                             tasarim_kodlari=tasarim_kod_bilgileri)
    except Exception as e:
        print(f"İş çizelgesi hatası: {str(e)}")
        return render_template('is_cizelgesi.html', 
                             is_listesi=[],
                             tasarim_kodlari=tasarim_kod_bilgileri,
                             error="İş çizelgesi yüklenirken bir hata oluştu.")

@app.route('/optimizasyon')
def optimizasyon():
    return render_template('optimizasyon.html')

def run_optimization():
    try:
        print("Optimizasyon başlatılıyor...")
        
        # Taguchi optimizasyonu
        print("Taguchi optimizasyonu başlatılıyor...")
        taguchi.main()
        print("Taguchi optimizasyonu tamamlandı.")
        
        # Genetik algoritma optimizasyonu
        print("Genetik algoritma optimizasyonu başlatılıyor...")
        tasarim_kod_bilgileri, calisan_yetkinlikleri = geneticalgorithm.load_dataset()
        if not tasarim_kod_bilgileri or not calisan_yetkinlikleri:
            raise Exception("Veri setleri yüklenemedi!")
            
        print("Veri setleri yüklendi, genetik algoritma çalıştırılıyor...")
        best_assignment, fitness_history, task_worker_rankings = geneticalgorithm.genetic_algorithm(tasarim_kod_bilgileri, calisan_yetkinlikleri)
        
        if not best_assignment:
            raise Exception("Genetik algoritma sonuç üretemedi!")
        
        print("Genetik algoritma tamamlandı, sonuçlar kaydediliyor...")
        # Sonuçları JSON olarak kaydet
        results = {}
        for task, workers in best_assignment.items():
            # Artık her görev için birden fazla çalışan olabilir
            # Çalışanları seviyelerine göre grupla
            atanan_calisanlar = {
                "ustabasi": [],
                "kalifiyeli": [],
                "cirak": []
            }
            
            for worker in workers:
                level = calisan_yetkinlikleri[worker]["yetkinlik_seviyesi"]
                if level == 1:
                    atanan_calisanlar["ustabasi"].append(worker)
                elif level == 2:
                    atanan_calisanlar["kalifiyeli"].append(worker)
                else:
                    atanan_calisanlar["cirak"].append(worker)
            
            # Personel ihtiyacını al
            personel_ihtiyaci = tasarim_kod_bilgileri[task].get("personel_ihtiyaci", {
                "ustabasi": 0,
                "kalifiyeli": 0,
                "cirak": 0
            })
            
            # Eksik personel sayılarını hesapla
            eksik_personel = {
                "ustabasi": max(0, personel_ihtiyaci.get("ustabasi", 0) - len(atanan_calisanlar["ustabasi"])),
                "kalifiyeli": max(0, personel_ihtiyaci.get("kalifiyeli", 0) - len(atanan_calisanlar["kalifiyeli"])),
                "cirak": max(0, personel_ihtiyaci.get("cirak", 0) - len(atanan_calisanlar["cirak"]))
            }
            
            # Alternatif çalışanları seviyelerine göre grupla
            alternatif_calisanlar = []
            
            # Her seviye için alternatif çalışanları ekle
            for level_name, level_rankings in task_worker_rankings[task].items():
                for worker, score in level_rankings:
                    if worker not in workers:  # Atanmamış çalışanları alternatif olarak ekle
                        alternatif_calisanlar.append({
                            "calisan": worker,
                            "uygunluk": float(score),
                            "seviye": level_name  # Seviye bilgisini ekle
                        })
            
            results[str(task)] = {
                "atanan_calisanlar": atanan_calisanlar,
                "eksik_personel": eksik_personel,
                "alternatif_calisanlar": alternatif_calisanlar,
                "personel_ihtiyaci": personel_ihtiyaci
            }
        
        # Sonuçları kaydet
        with open(os.path.join(ROOT_DIR, 'veri', 'genetik_sonuclari.json'), 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        print("Optimizasyon başarıyla tamamlandı!")
        return True
    except Exception as e:
        error_msg = f"Optimizasyon hatası: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        # Hata durumunda boş sonuç dosyaları oluştur
        error_result = {"error": error_msg}
        try:
            with open(os.path.join(ROOT_DIR, 'veri', 'genetik_sonuclari.json'), 'w', encoding='utf-8') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=4)
            with open(os.path.join(ROOT_DIR, 'veri', 'taguchi_sonuclari.json'), 'w', encoding='utf-8') as f:
                json.dump(error_result, f, ensure_ascii=False, indent=4)
        except:
            pass
            
        return False

@app.route('/api/optimizasyon-baslat', methods=['POST'])
def optimizasyon_baslat():
    try:
        # Veri klasörünün varlığını kontrol et
        if not os.path.exists('veri'):
            os.makedirs('veri')
        
        # Önceki sonuçları temizle
        if os.path.exists('veri/taguchi_sonuclari.json'):
            os.remove('veri/taguchi_sonuclari.json')
        if os.path.exists('veri/genetik_sonuclari.json'):
            os.remove('veri/genetik_sonuclari.json')
        
        # Boş sonuç dosyaları oluştur
        with open('veri/taguchi_sonuclari.json', 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        with open('veri/genetik_sonuclari.json', 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)
        
        # Optimizasyonu arka planda başlat
        thread = Thread(target=run_optimization)
        thread.daemon = True
        thread.start()
        
        return jsonify({"success": True, "message": "Optimizasyon başlatıldı"})
    except Exception as e:
        print(f"Optimizasyon hatası: {str(e)}")  # Hata loglaması ekle
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/optimizasyon-durumu')
def optimizasyon_durumu():
    try:
        # Taguchi sonuçlarını kontrol et
        taguchi_sonuclari = {}
        if os.path.exists('veri/taguchi_sonuclari.json'):
            with open('veri/taguchi_sonuclari.json', 'r', encoding='utf-8') as f:
                taguchi_sonuclari = json.load(f)
        
        # Genetik algoritma sonuçlarını kontrol et
        genetik_sonuclari = {}
        if os.path.exists('veri/genetik_sonuclari.json'):
            with open('veri/genetik_sonuclari.json', 'r', encoding='utf-8') as f:
                genetik_sonuclari = json.load(f)
                
                # Her tasarım kodu için alternatif çalışanları ekle
                for tasarim_kodu in genetik_sonuclari:
                    try:
                        # Tasarım kodunun personel ihtiyacını al
                        personel_ihtiyaci = tasarim_kod_bilgileri[tasarim_kodu].get('personel_ihtiyaci', {
                            "ustabasi": 0,
                            "kalifiyeli": 0,
                            "cirak": 0
                        })
                        
                        # Alternatif çalışanları bul
                        alternatif_calisanlar = []
                        for calisan, bilgi in calisan_yetkinlikleri.items():
                            seviye = bilgi.get('yetkinlik_seviyesi', 3)
                            seviye_str = 'cirak'
                            if seviye == 1:
                                seviye_str = 'ustabasi'
                            elif seviye == 2:
                                seviye_str = 'kalifiyeli'
                            
                            # Çalışanın uygunluk skorunu hesapla
                            from geneticalgorithm import calculate_worker_fitness_for_task
                            uygunluk = calculate_worker_fitness_for_task(calisan, tasarim_kodu, tasarim_kod_bilgileri, calisan_yetkinlikleri)
                            
                            # Eğer çalışan atanmış çalışanlar arasında değilse, alternatif olarak ekle
                            atanan_calisanlar = genetik_sonuclari[tasarim_kodu].get('atanan_calisanlar', {})
                            tum_atananlar = []
                            for seviye_calisanlar in atanan_calisanlar.values():
                                if isinstance(seviye_calisanlar, list):
                                    tum_atananlar.extend(seviye_calisanlar)
                            
                            if calisan not in tum_atananlar:
                                alternatif_calisanlar.append({
                                    "calisan": calisan,
                                    "seviye": seviye_str,
                                    "uygunluk": uygunluk
                                })
                        
                        # Alternatif çalışanları uygunluk puanına göre sırala
                        alternatif_calisanlar.sort(key=lambda x: x['uygunluk'], reverse=True)
                        
                        # En uygun alternatif çalışanları seç (her seviye için en fazla 5)
                        genetik_sonuclari[tasarim_kodu]['alternatif_calisanlar'] = alternatif_calisanlar[:15]
                        
                    except Exception as e:
                        print(f"Alternatif çalışanlar hesaplanırken hata: {str(e)}")
                        continue
        
        return jsonify({
            "taguchi_hazir": bool(taguchi_sonuclari),
            "genetik_hazir": bool(genetik_sonuclari),
            "taguchi_sonuclari": taguchi_sonuclari,
            "genetik_sonuclari": genetik_sonuclari
        })
    except Exception as e:
        return jsonify({
            "error": f"Optimizasyon durumu kontrol edilirken hata oluştu: {str(e)}"
        }), 500

@app.route('/api/tasarim-kodu-ekle', methods=['POST'])
def tasarim_kodu_ekle():
    try:
        data = request.json
        tasarim_kod_bilgileri[data['kod']] = {
            "urun_adi": data['urun_adi'],
            "tahmini_montaj_suresi": int(data['montaj_suresi']),
            "ortalama_uretim_adedi": int(data['uretim_adedi']),
            "personel_ihtiyaci": data['personel_ihtiyaci']
        }
        
        # Değişiklikleri JSON dosyasına kaydet
        with open(TASARIM_KODLARI_JSON, 'w', encoding='utf-8') as f:
            json.dump(tasarim_kod_bilgileri, f, ensure_ascii=False, indent=4)
        
        # Verileri yeniden yükle
        veri_yukle()
        
        # Gerçek zamanlı güncelleme gönder
        socketio.emit('tasarim_kodu_guncelleme', tasarim_kod_bilgileri)
        return jsonify({"success": True, "message": "Tasarım kodu başarıyla eklendi"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Hata oluştu: {str(e)}"}), 500

@app.route('/api/calisan-ekle', methods=['POST'])
def calisan_ekle():
    try:
        data = request.json
        calisan_yetkinlikleri[data['ad']] = {
            "yetkinlik_seviyesi": int(data['yetkinlik_seviyesi']),
            "tecrube_yili": int(data['tecrube']),
            "verimlilik_puani": float(data['verimlilik'])
        }
        
        # Değişiklikleri JSON dosyasına kaydet
        with open(CALISAN_YETKINLIKLERI_JSON, 'w', encoding='utf-8') as f:
            json.dump(calisan_yetkinlikleri, f, ensure_ascii=False, indent=4)
        
        # Verileri yeniden yükle
        veri_yukle()
        
        # Gerçek zamanlı güncelleme gönder
        socketio.emit('calisan_guncelleme', calisan_yetkinlikleri)
        return jsonify({"success": True, "message": "Çalışan başarıyla eklendi"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Hata oluştu: {str(e)}"}), 500

@app.route('/api/calisan-sil', methods=['POST'])
def calisan_sil():
    try:
        data = request.json
        calisan_adi = data['ad']
        
        # Çalışanı sözlükten sil
        if calisan_adi in calisan_yetkinlikleri:
            del calisan_yetkinlikleri[calisan_adi]
            
            # JSON dosyasını güncelle
            with open(CALISAN_YETKINLIKLERI_JSON, 'w', encoding='utf-8') as f:
                json.dump(calisan_yetkinlikleri, f, ensure_ascii=False, indent=4)
            
            return jsonify({"success": True, "message": "Çalışan başarıyla silindi"})
        else:
            return jsonify({"success": False, "message": "Çalışan bulunamadı"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Hata oluştu: {str(e)}"}), 500

@app.route('/api/tasarim-kodu-sil', methods=['POST'])
def tasarim_kodu_sil():
    try:
        data = request.json
        kod = data['kod']
        
        # Tasarım kodunu sözlükten sil
        if kod in tasarim_kod_bilgileri:
            del tasarim_kod_bilgileri[kod]
            
            # JSON dosyasını güncelle
            with open(TASARIM_KODLARI_JSON, 'w', encoding='utf-8') as f:
                json.dump(tasarim_kod_bilgileri, f, ensure_ascii=False, indent=4)
            
            return jsonify({"success": True, "message": "Tasarım kodu başarıyla silindi"})
        else:
            return jsonify({"success": False, "message": "Tasarım kodu bulunamadı"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Hata oluştu: {str(e)}"}), 500

@app.route('/api/is-sil', methods=['POST'])
def is_sil():
    try:
        data = request.json
        is_id = data['is_id']  # tasarim_kodu yerine is_id kullanıyoruz
        
        # İş listesini oku
        with open('veri/is_listesi.json', 'r', encoding='utf-8') as f:
            is_listesi = json.load(f)
        
        # İşi ID'ye göre bul ve sil
        yeni_liste = [is_item for is_item in is_listesi if is_item['id'] != is_id]
        
        if len(yeni_liste) == len(is_listesi):
            return jsonify({"success": False, "message": "İş bulunamadı"}), 404
        
        # Güncellenmiş listeyi kaydet
        with open('veri/is_listesi.json', 'w', encoding='utf-8') as f:
            json.dump(yeni_liste, f, ensure_ascii=False, indent=4)
        
        return jsonify({"success": True, "message": "İş başarıyla silindi"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Hata oluştu: {str(e)}"}), 500

def musait_calisanlari_bul(is_listesi):
    """Şu anda aktif işi olmayan çalışanları bulur"""
    mesgul_calisanlar = set()
    for is_item in is_listesi:
        if is_item['durum'] != 'tamamlandi':
            mesgul_calisanlar.add(is_item['atanan_calisan'])
    
    tum_calisanlar = set(calisan_yetkinlikleri.keys())
    return list(tum_calisanlar - mesgul_calisanlar)

@app.route('/api/alternatif-personel/<tasarim_kodu>')
def alternatif_personel(tasarim_kodu):
    try:
        # Tasarım kodunun personel ihtiyacını al
        personel_ihtiyaci = tasarim_kod_bilgileri[tasarim_kodu].get('personel_ihtiyaci', {
            "ustabasi": 0,
            "kalifiyeli": 0,
            "cirak": 0
        })
        
        # Çalışanları seviyelerine göre grupla
        ustabasi_calisanlar = []
        kalifiyeli_calisanlar = []
        cirak_calisanlar = []
        
        for calisan, bilgi in calisan_yetkinlikleri.items():
            seviye = bilgi.get('yetkinlik_seviyesi', 3)
            
            # Çalışanın uygunluk skorunu hesapla
            from geneticalgorithm import calculate_worker_fitness_for_task
            uygunluk = calculate_worker_fitness_for_task(calisan, tasarim_kodu, tasarim_kod_bilgileri, calisan_yetkinlikleri)
            
            calisan_bilgisi = {
                "calisan": calisan,
                "uygunluk": uygunluk
            }
            
            if seviye == 1:
                ustabasi_calisanlar.append(calisan_bilgisi)
            elif seviye == 2:
                kalifiyeli_calisanlar.append(calisan_bilgisi)
            else:
                cirak_calisanlar.append(calisan_bilgisi)
        
        # Uygunluk skoruna göre sırala
        ustabasi_calisanlar.sort(key=lambda x: x['uygunluk'], reverse=True)
        kalifiyeli_calisanlar.sort(key=lambda x: x['uygunluk'], reverse=True)
        cirak_calisanlar.sort(key=lambda x: x['uygunluk'], reverse=True)
        
        # Mevcut çalışan sayılarını hesapla
        mevcut_ustabasi = len(ustabasi_calisanlar)
        mevcut_kalifiyeli = len(kalifiyeli_calisanlar)
        mevcut_cirak = len(cirak_calisanlar)
        
        # Eksik personel sayılarını hesapla
        eksik_ustabasi = max(0, personel_ihtiyaci.get('ustabasi', 0) - mevcut_ustabasi)
        eksik_kalifiyeli = max(0, personel_ihtiyaci.get('kalifiyeli', 0) - mevcut_kalifiyeli)
        eksik_cirak = max(0, personel_ihtiyaci.get('cirak', 0) - mevcut_cirak)
        
        # Önerilen çalışanları seç
        onerilen_ustabasi = ustabasi_calisanlar[:personel_ihtiyaci.get('ustabasi', 0)]
        onerilen_kalifiyeli = kalifiyeli_calisanlar[:personel_ihtiyaci.get('kalifiyeli', 0)]
        onerilen_cirak = cirak_calisanlar[:personel_ihtiyaci.get('cirak', 0)]
        
        return jsonify({
            "success": True,
            "personel_ihtiyaci": personel_ihtiyaci,
            "onerilen_calisanlar": {
                "ustabasi": onerilen_ustabasi,
                "kalifiyeli": onerilen_kalifiyeli,
                "cirak": onerilen_cirak
            },
            "eksik_personel": {
                "ustabasi": eksik_ustabasi,
                "kalifiyeli": eksik_kalifiyeli,
                "cirak": eksik_cirak
            }
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/is-devret-ve-kaydet', methods=['POST'])
def is_devret_ve_kaydet():
    try:
        data = request.json
        tasarim_kodu = data.get('tasarim_kodu')
        mevcut_is_kodu = data.get('mevcut_is_kodu')
        atanan_calisan = data.get('atanan_calisan')

        if not all([tasarim_kodu, mevcut_is_kodu, atanan_calisan]):
            return jsonify({"success": False, "message": "Eksik parametreler"}), 400

        # İş listesini oku
        with open('veri/is_listesi.json', 'r', encoding='utf-8') as f:
            is_listesi = json.load(f)

        # Mevcut işi bul
        mevcut_is = None
        for is_item in is_listesi:
            if (is_item['tasarim_kodu'] == mevcut_is_kodu and 
                is_item['atanan_calisan'] == atanan_calisan and
                is_item['durum'] != 'tamamlandi'):
                mevcut_is = is_item
                break

        if not mevcut_is:
            return jsonify({"success": False, "message": "Mevcut iş bulunamadı"}), 404

        # Genetik algoritma sonuçlarını al
        with open('veri/genetik_sonuclari.json', 'r', encoding='utf-8') as f:
            genetik_sonuclari = json.load(f)

        # Alternatif personel bul
        alternatif_personel = None
        if mevcut_is_kodu in genetik_sonuclari:
            for alt in genetik_sonuclari[mevcut_is_kodu]['alternatif_calisanlar']:
                # Personelin başka işi var mı kontrol et
                personel_musait = True
                for is_item in is_listesi:
                    if (is_item['atanan_calisan'] == alt['calisan'] and 
                        is_item['durum'] != 'tamamlandi'):
                        personel_musait = False
                        break
                
                if personel_musait:
                    alternatif_personel = alt['calisan']
                    break

        if not alternatif_personel:
            return jsonify({
                "success": False, 
                "message": "Uygun alternatif personel bulunamadı"
            }), 400

        # Mevcut işi alternatif personele devret
        mevcut_is['atanan_calisan'] = alternatif_personel

        # Yeni işi ekle
        yeni_is = {
            "id": str(len(is_listesi) + 1),
            "tasarim_kodu": tasarim_kodu,
            "proje_adi": data.get('proje_adi', ''),
            "teslimat_tarihi": data.get('teslimat_tarihi', ''),
            "durum": data.get('durum', 'beklemede'),
            "oncelik": data.get('oncelik', 'kritik'),
            "kalan_sure": data.get('kalan_sure', ''),
            "atanan_calisan": atanan_calisan
        }
        is_listesi.append(yeni_is)

        # Güncellenmiş listeyi kaydet
        with open('veri/is_listesi.json', 'w', encoding='utf-8') as f:
            json.dump(is_listesi, f, ensure_ascii=False, indent=4)

        return jsonify({
            "success": True,
            "message": "İş başarıyla devredildi ve yeni iş kaydedildi"
        })

    except Exception as e:
        print(f"İş devretme ve kaydetme hatası: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/is-atama', methods=['POST'])
def is_atama():
    try:
        data = request.get_json()
        
        # Tasarım kodu bilgilerini al
        tasarim_kodu = data.get('kod')
        if not tasarim_kodu:
            return jsonify({'success': False, 'message': 'Tasarım kodu gerekli'})
            
        # Genetik algoritma sonuçlarını kontrol et
        genetik_sonuclari = load_json_file('veri/genetik_sonuclari.json')
        if not genetik_sonuclari or tasarim_kodu not in genetik_sonuclari:
            return jsonify({'success': False, 'message': 'Genetik algoritma sonuçları bulunamadı'})
            
        # Mevcut işleri kontrol et
        is_listesi = load_json_file('veri/is_listesi.json') or []
        
        # Yeni iş için benzersiz ID oluştur
        yeni_id = str(len(is_listesi) + 1)
        while any(is_['id'] == yeni_id for is_ in is_listesi):
            yeni_id = str(int(yeni_id) + 1)
        
        # Meşgul çalışanları bul
        mesgul_calisanlar = set()
        for is_ in is_listesi:
            if is_['durum'] != 'tamamlandi':
                for seviye, calisanlar in is_['atanan_calisan'].items():
                    if isinstance(calisanlar, list):
                        mesgul_calisanlar.update(calisanlar)
                    else:
                        mesgul_calisanlar.add(calisanlar)

        # Her seviye için müsait çalışanları bul ve ata
        final_atama = {
            'ustabasi': [],
            'kalifiyeli': [],
            'cirak': []
        }

        # Personel ihtiyacını al
        personel_ihtiyaci = tasarim_kod_bilgileri[tasarim_kodu].get('personel_ihtiyaci', {})
        
        # Genetik algoritma sonuçlarından birincil ve alternatif çalışanları al
        birincil_atamalar = genetik_sonuclari[tasarim_kodu].get('atanan_calisanlar', {})
        alternatif_calisanlar = genetik_sonuclari[tasarim_kodu].get('alternatif_calisanlar', [])
        
        # Her seviye için çalışan ataması yap
        for seviye in ['ustabasi', 'kalifiyeli', 'cirak']:
            ihtiyac = personel_ihtiyaci.get(seviye, 0)
            if ihtiyac == 0:
                continue
            
            # Önce birincil atamaları kontrol et
            birincil_calisanlar = birincil_atamalar.get(seviye, [])
            for calisan in birincil_calisanlar:
                if calisan not in mesgul_calisanlar and len(final_atama[seviye]) < ihtiyac:
                    final_atama[seviye].append(calisan)
            
            # Eğer hala ihtiyaç varsa, alternatif çalışanları kontrol et
            kalan_ihtiyac = ihtiyac - len(final_atama[seviye])
            if kalan_ihtiyac > 0:
                # Bu seviye için uygun alternatif çalışanları filtrele
                uygun_calisanlar = [
                    calisan for calisan in alternatif_calisanlar 
                    if calisan['seviye'] == seviye and 
                    calisan['calisan'] not in mesgul_calisanlar and
                    calisan['calisan'] not in final_atama[seviye]
                ]
                
                # Uygunluk puanına göre sırala
                uygun_calisanlar.sort(key=lambda x: x['uygunluk'], reverse=True)
                
                # Kalan ihtiyaç kadar çalışan seç
                for i in range(min(kalan_ihtiyac, len(uygun_calisanlar))):
                    final_atama[seviye].append(uygun_calisanlar[i]['calisan'])
            
            # Hala eksik varsa fason işçi ekle
            eksik = ihtiyac - len(final_atama[seviye])
            if eksik > 0:
                for _ in range(eksik):
                    final_atama[seviye].append(f'Fason İşçi ({seviye.capitalize()})')
        
        # Yeni iş kaydını oluştur
        yeni_is = {
            'id': yeni_id,
            'tasarim_kodu': tasarim_kodu,
            'proje_adi': data['proje_adi'],
            'teslimat_tarihi': data['teslimat_tarihi'],
            'durum': data['durum'],
            'oncelik': data['oncelik'],
            'kalan_sure': data['kalan_sure'],
            'atanan_calisan': final_atama
        }
        
        is_listesi.append(yeni_is)
        save_json_file('veri/is_listesi.json', is_listesi)
        
        return jsonify({
            'success': True,
            'message': 'İş başarıyla kaydedildi',
            'atanan_calisanlar': final_atama
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/is-guncelle', methods=['POST'])
def is_guncelle():
    try:
        data = request.get_json()
        tasarim_kodu = data.get('tasarim_kodu')
        durum = data.get('durum')
        oncelik = data.get('oncelik')  # Yeni eklenen öncelik parametresi

        if not all([tasarim_kodu, durum, oncelik]):  # oncelik kontrolü eklendi
            return jsonify({'success': False, 'message': 'Eksik parametreler'})

        # is_listesi.json dosyasını oku
        with open('veri/is_listesi.json', 'r', encoding='utf-8') as f:
            is_listesi = json.load(f)

        # İşi bul ve güncelle
        is_guncellendi = False
        for is_item in is_listesi:
            if is_item['tasarim_kodu'] == tasarim_kodu:
                is_item['durum'] = durum
                is_item['oncelik'] = oncelik  # Öncelik güncelleme
                is_guncellendi = True
                break

        if not is_guncellendi:
            return jsonify({'success': False, 'message': 'İş bulunamadı'})

        # Güncellenmiş listeyi kaydet
        with open('veri/is_listesi.json', 'w', encoding='utf-8') as f:
            json.dump(is_listesi, f, ensure_ascii=False, indent=4)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

monte_carlo_result = None
monte_carlo_running = False

@app.route('/api/monte-carlo-baslat', methods=['POST'])
def monte_carlo_baslat():
    global monte_carlo_result, monte_carlo_running
    data = request.json
    if monte_carlo_running:
        return jsonify({"success": False, "message": "Monte Carlo zaten çalışıyor."})
    monte_carlo_running = True
    monte_carlo_result = None

    def run_mc():
        from monte_carlo import run_monte_carlo_simulation, load_dataset
        tasarim_kodlari, calisanlar = load_dataset()
        if not tasarim_kodlari or not calisanlar:
            # hata
            pass
        else:
            sonuc = run_monte_carlo_simulation(
                tasarim_kodlari, calisanlar,
                n_scenarios=data.get('n_scenarios',100),
                absence_prob=data.get('absence_prob',0.05),
                performance_std=data.get('performance_std',0.05)
            )
            global monte_carlo_result, monte_carlo_running
            monte_carlo_result = sonuc
            monte_carlo_running = False

    th = Thread(target=run_mc)
    th.start()

    return jsonify({"success": True, "message": "Monte Carlo başlatıldı"})

@app.route('/api/monte-carlo-durumu', methods=['GET'])
def monte_carlo_durumu():
    global monte_carlo_result, monte_carlo_running
    if monte_carlo_running:
        return jsonify({"hazir": False})
    else:
        if monte_carlo_result:
            return jsonify({"hazir": True, "sonuc": monte_carlo_result})
        else:
            return jsonify({"hazir": False})
        

@app.route('/api/update-kalan-sure', methods=['POST'])
def update_kalan_sure():
    """
    data = { tasarim_kodu: "...", kalan_sure: 123 }
    """
    try:
        data = request.json
        tasarim_kodu = data['tasarim_kodu']
        new_sure = int(data['kalan_sure'])

        # is_listesi.json oku
        with open('veri/is_listesi.json','r', encoding='utf-8') as f:
            is_listesi = json.load(f)

        # bul
        for is_item in is_listesi:
            if is_item['tasarim_kodu'] == tasarim_kodu:
                is_item['kalan_sure'] = new_sure
                # Opsiyon: eğer new_sure <=0 => durumu "tamamlandi"
                # is_item['durum'] = 'tamamlandi'
                break

        # kaydet
        with open('veri/is_listesi.json','w',encoding='utf-8') as f:
            json.dump(is_listesi, f, ensure_ascii=False, indent=4)

        return jsonify({"success": True, "message": "kalan_sure güncellendi"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/son-atama-detayi', methods=['GET'])
def son_atama_detayi():
    try:
        atama_detaylari_dosyasi = os.path.join('veri', 'atama_detaylari.json')
        if not os.path.exists(atama_detaylari_dosyasi):
            with open(atama_detaylari_dosyasi, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            return jsonify({"success": True, "data": None})
            
        with open(atama_detaylari_dosyasi, 'r', encoding='utf-8') as f:
            atama_detaylari = json.load(f)
            if not atama_detaylari:
                return jsonify({"success": True, "data": None})
            return jsonify({"success": True, "data": atama_detaylari[-1]})
    except Exception as e:
        print(f"Son atama detayı hatası: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/tum-atama-detaylari', methods=['GET'])
def tum_atama_detaylari():
    try:
        with open('veri/atama_detaylari.json', 'r', encoding='utf-8') as f:
            return jsonify({"success": True, "data": json.load(f)})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/atama-detayi-kaydet', methods=['POST'])
def atama_detayi_kaydet():
    try:
        data = request.get_json()
        
        # Mevcut atama detaylarını oku
        atama_detaylari = []
        try:
            with open('veri/atama_detaylari.json', 'r', encoding='utf-8') as f:
                atama_detaylari = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            atama_detaylari = []
        
        # Yeni atama detayını ekle
        atama_detaylari.append(data)
        
        # Atama detaylarını kaydet
        with open('veri/atama_detaylari.json', 'w', encoding='utf-8') as f:
            json.dump(atama_detaylari, f, ensure_ascii=False, indent=4)
        
        return jsonify({
            'success': True,
            'message': 'Atama detayları başarıyla kaydedildi'
        })
        
    except Exception as e:
        print('Atama detayı kaydetme hatası:', str(e))
        return jsonify({
            'success': False,
            'message': f'Atama detayları kaydedilirken bir hata oluştu: {str(e)}'
        })

@app.route('/api/tasarim-kodu-bilgileri/<tasarim_kodu>')
def tasarim_kodu_bilgileri(tasarim_kodu):
    try:
        if tasarim_kodu in tasarim_kod_bilgileri:
            return jsonify({
                "success": True,
                "personel_ihtiyaci": tasarim_kod_bilgileri[tasarim_kodu].get("personel_ihtiyaci", {"ustabasi": 0, "kalifiyeli": 0, "cirak": 0}),
                "urun_adi": tasarim_kod_bilgileri[tasarim_kodu].get("urun_adi", "")
            })
        return jsonify({"success": False, "message": "Tasarım kodu bulunamadı"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/calisan-bilgileri/<calisan_adi>')
def calisan_bilgileri(calisan_adi):
    try:
        if calisan_adi in calisan_yetkinlikleri:
            return jsonify({
                "success": True,
                "yetkinlikler": calisan_yetkinlikleri[calisan_adi].get("yetkinlikler", []),
                "tecrube_yili": calisan_yetkinlikleri[calisan_adi].get("tecrube_yili", 0),
                "verimlilik_puani": calisan_yetkinlikleri[calisan_adi].get("verimlilik_puani", 0)
            })
        return jsonify({"success": False, "message": "Çalışan bulunamadı"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/genetik-sonuclari')
def genetik_sonuclari():
    try:
        with open('veri/genetik_sonuclari.json', 'r', encoding='utf-8') as f:
            sonuclar = json.load(f)
        return jsonify(sonuclar)
    except Exception as e:
        return jsonify({}), 500

@app.route('/api/monte-carlo-simulasyonu', methods=['POST'])
def monte_carlo_simulasyonu():
    try:
        # Tasarım kodları ve çalışan bilgilerini yükle
        tasarim_kodlari = load_json_file('veri/tasarim_kodlari.json')
        calisan_yetkinlikleri = load_json_file('veri/calisan_yetkinlikleri.json')
        is_listesi = load_json_file('veri/is_listesi.json')
        
        # Aktif işleri filtrele
        aktif_isler = [is_item for is_item in is_listesi if is_item['durum'] != 'tamamlandi']
        
        if not aktif_isler:
            return jsonify({
                'error': 'Aktif iş bulunamadı. Monte Carlo simülasyonu için en az bir aktif iş gereklidir.'
            }), 400
        
        # Monte Carlo simülasyonunu çalıştır
        from py_files.monte_carlo import run_monte_carlo_simulation
        
        sonuclar = run_monte_carlo_simulation(
            tasarim_kodlari=tasarim_kodlari,
            calisan_yetkinlikleri=calisan_yetkinlikleri,
            aktif_isler=aktif_isler,
            n_scenarios=50
        )
        
        # Sonuçları JSON formatında döndür
        return jsonify(sonuclar)
    except Exception as e:
        print(f"Monte Carlo simülasyonu hatası: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True) 