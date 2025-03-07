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
from taguchi import taguchi_optimization, create_parameter_levels
import shutil
from threading import Thread
import time
import threading
from monte_carlo_simulasyon import simulasyon_calistir

# Global değişkenler
monte_carlo_running = False
monte_carlo_result = None

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
        bildirim_gonder("Optimizasyon başlatıldı", "bilgi")
        
        # Taguchi optimizasyonu
        print("Taguchi optimizasyonu başlatılıyor...")
        bildirim_gonder("Taguchi optimizasyonu başlatıldı", "bilgi")
        optimizasyon_ilerlemesi("taguchi", 0, "Başlatılıyor...")
        
        try:
            taguchi.main()
            optimizasyon_ilerlemesi("taguchi", 100, "Tamamlandı")
            bildirim_gonder("Taguchi optimizasyonu tamamlandı", "basari")
            print("Taguchi optimizasyonu tamamlandı.")
        except Exception as e:
            error_msg = str(e)
            print(f"Taguchi optimizasyonu hatası: {error_msg}")
            bildirim_gonder(f"Taguchi optimizasyonu hatası: {error_msg}", "hata")
            optimizasyon_ilerlemesi("taguchi", 100, f"Hata: {error_msg}")
            
            # Hata sonuç dosyasına kaydedilmediyse kaydet
            if not os.path.exists('veri/taguchi_sonuclari.json') or os.path.getsize('veri/taguchi_sonuclari.json') == 0:
                with open('veri/taguchi_sonuclari.json', 'w', encoding='utf-8') as f:
                    json.dump({"error": error_msg}, f, ensure_ascii=False, indent=4)
            
            # Genetik algoritma optimizasyonuna devam et
        
        # Genetik algoritma optimizasyonu
        print("Genetik algoritma optimizasyonu başlatılıyor...")
        bildirim_gonder("Genetik algoritma optimizasyonu başlatıldı", "bilgi")
        optimizasyon_ilerlemesi("genetik", 0, "Başlatılıyor...")
        
        tasarim_kod_bilgileri, calisan_yetkinlikleri = geneticalgorithm.load_dataset()
        if not tasarim_kod_bilgileri or not calisan_yetkinlikleri:
            raise Exception("Veri setleri yüklenemedi!")
            
        print("Veri setleri yüklendi, genetik algoritma çalıştırılıyor...")
        optimizasyon_ilerlemesi("genetik", 10, "Veri setleri yüklendi")
        
        # İlerleme bildirimi için callback fonksiyonu
        def ilerleme_callback(nesil, toplam_nesil, en_iyi_uygunluk):
            ilerleme_yuzdesi = min(10 + int((nesil / toplam_nesil) * 90), 100)
            optimizasyon_ilerlemesi("genetik", ilerleme_yuzdesi, f"Nesil: {nesil}/{toplam_nesil}, En iyi uygunluk: {en_iyi_uygunluk:.2f}")
        
        best_assignment, fitness_history, task_worker_rankings = geneticalgorithm.genetic_algorithm(
            tasarim_kod_bilgileri, 
            calisan_yetkinlikleri,
            ilerleme_callback=ilerleme_callback
        )
        
        if not best_assignment:
            raise Exception("Genetik algoritma sonuç üretemedi!")
        
        print("Genetik algoritma tamamlandı, sonuçlar kaydediliyor...")
        optimizasyon_ilerlemesi("genetik", 95, "Sonuçlar kaydediliyor...")
        
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
        taguchi_durum = "beklemede"
        taguchi_mesaj = "Henüz başlatılmadı"
        
        if os.path.exists('veri/taguchi_sonuclari.json'):
            with open('veri/taguchi_sonuclari.json', 'r', encoding='utf-8') as f:
                taguchi_sonuclari = json.load(f)
                
            if "error" in taguchi_sonuclari:
                taguchi_durum = "hata"
                taguchi_mesaj = taguchi_sonuclari["error"]
                if "message" in taguchi_sonuclari:
                    taguchi_mesaj += " - " + taguchi_sonuclari["message"]
            elif taguchi_sonuclari:
                taguchi_durum = "tamamlandi"
                taguchi_mesaj = f"{len(taguchi_sonuclari)} tasarım kodu için optimum süreler hesaplandı"
        
        # Genetik algoritma sonuçlarını kontrol et
        genetik_sonuclari = {}
        genetik_durum = "beklemede"
        genetik_mesaj = "Henüz başlatılmadı"
        
        if os.path.exists('veri/genetik_sonuclari.json'):
            with open('veri/genetik_sonuclari.json', 'r', encoding='utf-8') as f:
                genetik_sonuclari = json.load(f)
                
            if genetik_sonuclari:
                genetik_durum = "tamamlandi"
                genetik_mesaj = "Genetik algoritma optimizasyonu tamamlandı"
                
        # Optimizasyon durumunu belirle
        optimizasyon_durum = "devam_ediyor"
        if taguchi_durum in ["tamamlandi", "hata"] and genetik_durum in ["tamamlandi", "hata"]:
            optimizasyon_durum = "tamamlandi"
            
        # Taguchi sonuçlarında hata varsa bile genetik algoritma çalışabilir
        if taguchi_durum == "hata" and genetik_durum == "beklemede":
            optimizasyon_durum = "devam_ediyor"
            
        # Sonuçları döndür
        return jsonify({
            "durum": optimizasyon_durum,
            "taguchi": {
                "durum": taguchi_durum,
                "mesaj": taguchi_mesaj,
                "sonuclar": taguchi_sonuclari if "error" not in taguchi_sonuclari else {}
            },
            "genetik": {
                "durum": genetik_durum,
                "mesaj": genetik_mesaj,
                "sonuclar": genetik_sonuclari
            }
        })
    except Exception as e:
        print(f"Optimizasyon durumu hatası: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
            # Yeni format (seviye bazlı atama) için kontrol
            if isinstance(is_item.get('atanan_calisan'), dict):
                for seviye, calisanlar in is_item['atanan_calisan'].items():
                    if isinstance(calisanlar, list):
                        for calisan in calisanlar:
                            if not calisan.startswith('Fason'):  # Fason işçileri hariç tut
                                mesgul_calisanlar.add(calisan)
            # Eski format (tek çalışan) için kontrol
            elif is_item.get('atanan_calisan') and not str(is_item.get('atanan_calisan')).startswith('Fason'):
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

@app.route('/api/is-kaydet', methods=['POST'])
def is_kaydet():
    try:
        data = request.get_json()
        tasarim_kodu = data.get('kod')
        
        if not tasarim_kodu:
            return jsonify({'success': False, 'mesaj': 'Tasarım kodu gerekli!'}), 400
        
        # İş listesini yükle
        is_listesi = load_json_file('veri/is_listesi.json')
        if not is_listesi:
            is_listesi = []
        
        # Yeni iş ID'si oluştur
        yeni_id = str(len(is_listesi) + 1)
        while any(is_item['id'] == yeni_id for is_item in is_listesi):
            yeni_id = str(int(yeni_id) + 1)
        
        # Taguchi optimizasyon sonuçlarını yükle
        taguchi_sonuclari = load_json_file('veri/taguchi_sonuclari.json')
        genetik_sonuclari = load_json_file('veri/genetik_sonuclari.json')
        monte_carlo_sonuclari = load_json_file('veri/monte_carlo_sonuclari.json')
        
        # Optimize edilmiş süreyi al
        if taguchi_sonuclari and tasarim_kodu in taguchi_sonuclari.get('best_parameters', {}):
            tahmini_sure = taguchi_sonuclari['best_parameters'][tasarim_kodu]['sure']
        else:
            tahmini_sure = tasarim_kod_bilgileri[tasarim_kodu].get('tahmini_montaj_suresi', 0)
        
        # Meşgul çalışanları bul
        mesgul_calisanlar = set()
        for is_item in is_listesi:
            if is_item['durum'] != 'tamamlandi':
                if isinstance(is_item.get('atanan_calisan'), dict):
                    for seviye, calisanlar in is_item['atanan_calisan'].items():
                        if isinstance(calisanlar, list):
                            mesgul_calisanlar.update(c for c in calisanlar if not c.startswith('Fason'))
                elif is_item.get('atanan_calisan') in calisan_yetkinlikleri:
                    mesgul_calisanlar.add(is_item['atanan_calisan'])
        
        # Personel ihtiyacını al
        personel_ihtiyaci = tasarim_kod_bilgileri[tasarim_kodu].get('personel_ihtiyaci', {
            'ustabasi': 0,
            'kalifiyeli': 0,
            'cirak': 0
        })
        
        # Tüm çalışanları seviyelerine göre grupla
        tum_calisanlar = {
            'ustabasi': [],
            'kalifiyeli': [],
            'cirak': []
        }
        
        for calisan, bilgi in calisan_yetkinlikleri.items():
            seviye = bilgi.get('yetkinlik_seviyesi')
            if seviye == 1:
                tum_calisanlar['ustabasi'].append(calisan)
            elif seviye == 2:
                tum_calisanlar['kalifiyeli'].append(calisan)
            elif seviye == 3:
                tum_calisanlar['cirak'].append(calisan)
        
        # En uygun çalışanları seç
        atanan_calisanlar = {
            'ustabasi': [],
            'kalifiyeli': [],
            'cirak': []
        }
        
        for seviye in ['ustabasi', 'kalifiyeli', 'cirak']:
            ihtiyac = personel_ihtiyaci.get(seviye, 0)
            if ihtiyac > 0:
                musait_calisanlar = [c for c in tum_calisanlar[seviye] if c not in mesgul_calisanlar]
                
                # Genetik algoritma sonuçlarını kullan
                if genetik_sonuclari and tasarim_kodu in genetik_sonuclari:
                    onerilen_calisanlar = genetik_sonuclari[tasarim_kodu].get('atanan_calisanlar', {}).get(seviye, [])
                    # Önerilen çalışanlardan müsait olanları öncelikle seç
                    for calisan in onerilen_calisanlar:
                        if calisan in musait_calisanlar and len(atanan_calisanlar[seviye]) < ihtiyac:
                            atanan_calisanlar[seviye].append(calisan)
                            musait_calisanlar.remove(calisan)
                
                # Hala ihtiyaç varsa, kalan müsait çalışanlardan Monte Carlo sonuçlarına göre en iyilerini seç
                eksik = ihtiyac - len(atanan_calisanlar[seviye])
                if eksik > 0 and musait_calisanlar:
                    if monte_carlo_sonuclari and 'calisanlar' in monte_carlo_sonuclari:
                        musait_calisanlar.sort(key=lambda x: (
                            monte_carlo_sonuclari['calisanlar'].get(x, {}).get('ortalama_performans', 0) * 0.4 +
                            (1 - monte_carlo_sonuclari['calisanlar'].get(x, {}).get('risk_skoru', 1)) * 0.3 +
                            monte_carlo_sonuclari['calisanlar'].get(x, {}).get('performans_kararliligi', 0) * 0.3
                        ), reverse=True)
                    
                    atanan_calisanlar[seviye].extend(musait_calisanlar[:eksik])
                    eksik = ihtiyac - len(atanan_calisanlar[seviye])
                
                # Hala eksik varsa fason işçi ekle
                if eksik > 0:
                    for i in range(eksik):
                        atanan_calisanlar[seviye].append(f'Fason İşçi ({seviye.capitalize()})')
        
        # Yeni iş kaydı oluştur
        yeni_is = {
            'id': yeni_id,
            'tasarim_kodu': tasarim_kodu,
            'proje_adi': data.get('proje_adi', ''),
            'teslimat_tarihi': data.get('teslimat_tarihi', ''),
            'durum': data.get('durum', 'beklemede'),
            'oncelik': data.get('oncelik', 'normal'),
            'kalan_sure': tahmini_sure,
            'atanan_calisan': atanan_calisanlar
        }
        
        # İş listesine ekle
        is_listesi.append(yeni_is)
        
        # İş listesini kaydet
        if not save_json_file('veri/is_listesi.json', is_listesi):
            raise Exception("İş listesi kaydedilemedi")
        
        # Atama detaylarını kaydet
        atama_detayi = {
            'tarih': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'tasarim_kodu': tasarim_kodu,
            'proje_adi': data.get('proje_adi', ''),
            'atanan_calisanlar': atanan_calisanlar,
            'optimize_sure': tahmini_sure
        }
        
        atama_detaylari = load_json_file('veri/atama_detaylari.json') or []
        atama_detaylari.append(atama_detayi)
        save_json_file('veri/atama_detaylari.json', atama_detaylari)
        
        # Bildirim gönder ve socket.io ile güncelleme yap
        bildirim_gonder('İş başarıyla kaydedildi', 'basari')
        socketio.emit('is_cizelgesi_guncelle')
        
        return jsonify({
            'success': True,
            'mesaj': 'İş başarıyla kaydedildi'
        })
        
    except Exception as e:
        print(f"İş kaydetme hatası: {str(e)}")
        return jsonify({
            'success': False,
            'mesaj': f'İş kaydedilirken hata oluştu: {str(e)}'
        }), 500

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
                eski_durum = is_item['durum']
                is_item['durum'] = durum
                is_item['oncelik'] = oncelik  # Öncelik güncelleme
                is_guncellendi = True
                
                # Durum değişikliği bildirimi gönder
                if eski_durum != durum:
                    is_durumu_guncellendi(is_item['id'], eski_durum, durum)
                    bildirim_gonder(f"İş durumu güncellendi: {is_item.get('proje_adi', tasarim_kodu)} - {durum}", "bilgi")
                
                break

        if not is_guncellendi:
            return jsonify({'success': False, 'message': 'İş bulunamadı'})

        # Güncellenmiş listeyi kaydet
        with open('veri/is_listesi.json', 'w', encoding='utf-8') as f:
            json.dump(is_listesi, f, ensure_ascii=False, indent=4)
            
        # İş çizelgesi güncellemesi gönder
        socketio.emit('is_cizelgesi_guncellendi', is_listesi)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/performans-simulasyonu', methods=['POST'])
def performans_simulasyonu():
    try:
        # Simülasyonu çalıştır
        sonuc = simulasyon_calistir()
        
        # Monte Carlo sonuçlarını oku
        try:
            with open(os.path.join(ROOT_DIR, 'veri', 'monte_carlo_sonuclari.json'), 'r', encoding='utf-8') as f:
                mc_sonuclari = json.load(f)
                if not mc_sonuclari:
                    raise Exception("Monte Carlo sonuçları boş")
        except Exception as e:
            return jsonify({
                'success': False,
                'mesaj': f'Monte Carlo sonuçları oluşturulamadı: {str(e)}'
            }), 500
        
        return jsonify({
            'success': True,
            'monte_carlo_sonuclari': mc_sonuclari,
            'mesaj': sonuc
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'mesaj': f'Simülasyon hatası: {str(e)}'
        }), 500

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

# Gerçek zamanlı izleme için SocketIO olayları
@socketio.on('connect')
def handle_connect():
    print('Yeni istemci bağlandı')
    emit('connection_response', {'status': 'Bağlantı başarılı'})

@socketio.on('disconnect')
def handle_disconnect():
    print('İstemci bağlantısı kesildi')

# İş durumu değişikliklerini gerçek zamanlı izleme
def bildirim_gonder(mesaj, tip="bilgi", veri=None):
    """Tüm bağlı istemcilere bildirim gönderir"""
    socketio.emit('bildirim', {
        'mesaj': mesaj,
        'tip': tip,  # bilgi, uyari, hata, basari
        'zaman': datetime.now().strftime('%H:%M:%S'),
        'veri': veri
    })

# İş durumu değişikliklerini izleme
def is_durumu_guncellendi(is_id, eski_durum, yeni_durum):
    """İş durumu değiştiğinde çağrılır ve tüm istemcilere bildirim gönderir"""
    socketio.emit('is_durumu_guncellendi', {
        'is_id': is_id,
        'eski_durum': eski_durum,
        'yeni_durum': yeni_durum,
        'zaman': datetime.now().strftime('%H:%M:%S')
    })

# Optimizasyon ilerleme durumunu izleme
def optimizasyon_ilerlemesi(tip, ilerleme, detay=None):
    """Optimizasyon sürecindeki ilerlemeyi bildirir"""
    socketio.emit('optimizasyon_ilerlemesi', {
        'tip': tip,  # genetik, taguchi, monte_carlo
        'ilerleme': ilerleme,  # 0-100 arası yüzde
        'detay': detay,
        'zaman': datetime.now().strftime('%H:%M:%S')
    })

# İş çizelgesi güncellemelerini izleme
@socketio.on('is_cizelgesi_guncelle')
def is_cizelgesi_guncelle():
    """İş çizelgesini gerçek zamanlı olarak günceller"""
    try:
        if os.path.exists('veri/is_listesi.json'):
            with open('veri/is_listesi.json', 'r', encoding='utf-8') as f:
                is_listesi = json.load(f)
            emit('is_cizelgesi_guncellendi', is_listesi)
        else:
            emit('is_cizelgesi_guncellendi', [])
    except Exception as e:
        emit('hata', {'mesaj': f'İş çizelgesi güncellenirken hata: {str(e)}'})

# Çalışan durumlarını izleme
@socketio.on('calisan_durumlarini_guncelle')
def calisan_durumlarini_guncelle():
    """Çalışanların mevcut durumlarını gerçek zamanlı olarak günceller"""
    try:
        # İş listesini oku
        is_listesi = load_json_file('veri/is_listesi.json') or []
        
        # Çalışan durumlarını hesapla
        calisan_durumlari = {}
        for calisan in calisan_yetkinlikleri:
            calisan_durumlari[calisan] = {
                'durum': 'müsait',
                'mevcut_is': None
            }
        
        # Aktif işleri kontrol et
        for is_item in is_listesi:
            if is_item['durum'] != 'tamamlandi':
                # Yeni format (seviye bazlı atama) için kontrol
                if isinstance(is_item.get('atanan_calisan'), dict):
                    for seviye, calisanlar in is_item['atanan_calisan'].items():
                        if isinstance(calisanlar, list):
                            for calisan in calisanlar:
                                if calisan in calisan_durumlari and not calisan.startswith('Fason'):
                                    calisan_durumlari[calisan] = {
                                        'durum': 'çalışıyor',
                                        'mevcut_is': is_item['id'],
                                        'tasarim_kodu': is_item['tasarim_kodu'],
                                        'kalan_sure': is_item.get('kalan_sure', 'Belirsiz')
                                    }
                # Eski format (tek çalışan) için kontrol
                elif is_item.get('atanan_calisan') in calisan_durumlari:
                    calisan = is_item['atanan_calisan']
                    calisan_durumlari[calisan] = {
                        'durum': 'çalışıyor',
                        'mevcut_is': is_item['id'],
                        'tasarim_kodu': is_item['tasarim_kodu'],
                        'kalan_sure': is_item.get('kalan_sure', 'Belirsiz')
                    }
        
        emit('calisan_durumlari_guncellendi', calisan_durumlari)
    except Exception as e:
        emit('hata', {'mesaj': f'Çalışan durumları güncellenirken hata: {str(e)}'})

@app.route('/api/dashboard-verileri')
def dashboard_verileri():
    """Dashboard için gerekli tüm verileri tek bir API çağrısında döndürür"""
    try:
        # İş listesini oku
        is_listesi = load_json_file('veri/is_listesi.json') or []
        
        # İş durumlarına göre sayıları hesapla
        is_durumlari = {
            'beklemede': 0,
            'devam_ediyor': 0,
            'tamamlandi': 0,
            'gecikti': 0,
            'toplam': len(is_listesi)
        }
        
        for is_item in is_listesi:
            durum = is_item.get('durum', 'beklemede')
            if durum in is_durumlari:
                is_durumlari[durum] += 1
        
        # Çalışan durumlarını hesapla
        calisan_durumlari = {
            'musait': 0,
            'calisiyor': 0,
            'toplam': len(calisan_yetkinlikleri)
        }
        
        mesgul_calisanlar = set()
        for is_item in is_listesi:
            if is_item['durum'] != 'tamamlandi':
                # Yeni format (seviye bazlı atama) için kontrol
                if isinstance(is_item.get('atanan_calisan'), dict):
                    for seviye, calisanlar in is_item['atanan_calisan'].items():
                        if isinstance(calisanlar, list):
                            for calisan in calisanlar:
                                if calisan in calisan_yetkinlikleri and not calisan.startswith('Fason'):
                                    mesgul_calisanlar.add(calisan)
                # Eski format (tek çalışan) için kontrol
                elif is_item.get('atanan_calisan') in calisan_yetkinlikleri:
                    mesgul_calisanlar.add(is_item['atanan_calisan'])
        
        calisan_durumlari['calisiyor'] = len(mesgul_calisanlar)
        calisan_durumlari['musait'] = calisan_durumlari['toplam'] - calisan_durumlari['calisiyor']
        
        # Öncelik dağılımını hesapla
        oncelik_dagilimi = {
            'kritik': 0,
            'yuksek': 0,
            'normal': 0,
            'dusuk': 0
        }
        
        for is_item in is_listesi:
            if is_item['durum'] != 'tamamlandi':
                oncelik = is_item.get('oncelik', 'normal')
                if oncelik in oncelik_dagilimi:
                    oncelik_dagilimi[oncelik] += 1
        
        return jsonify({
            'success': True,
            'is_durumlari': is_durumlari,
            'calisan_durumlari': calisan_durumlari,
            'oncelik_dagilimi': oncelik_dagilimi,
            'son_guncelleme': datetime.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        print(f"Dashboard verileri hatası: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Periyodik olarak dashboard verilerini güncelleme
def periyodik_guncelleme():
    """30 saniyede bir dashboard verilerini günceller ve tüm istemcilere gönderir"""
    while True:
        try:
            # İş listesini oku
            is_listesi = load_json_file('veri/is_listesi.json') or []
            
            # İş durumlarına göre sayıları hesapla
            is_durumlari = {
                'beklemede': 0,
                'devam_ediyor': 0,
                'tamamlandi': 0,
                'gecikti': 0,
                'toplam': len(is_listesi)
            }
            
            for is_item in is_listesi:
                durum = is_item.get('durum', 'beklemede')
                if durum in is_durumlari:
                    is_durumlari[durum] += 1
            
            # Verileri gönder
            socketio.emit('dashboard_guncelleme', {
                'is_durumlari': is_durumlari,
                'zaman': datetime.now().strftime('%H:%M:%S')
            })
            
            # İş çizelgesini güncelle
            socketio.emit('is_cizelgesi_guncellendi', is_listesi)
            
        except Exception as e:
            print(f"Periyodik güncelleme hatası: {str(e)}")
        
        # 30 saniye bekle
        time.sleep(30)

if __name__ == '__main__':
    # Periyodik güncelleme işlemini başlat
    thread = Thread(target=periyodik_guncelleme)
    thread.daemon = True
    thread.start()
    
    socketio.run(app, debug=True) 