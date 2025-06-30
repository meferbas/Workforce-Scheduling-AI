from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
from django.db import models, transaction
from django.db.models import Avg, Q, Sum
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDate
from django.core.serializers.json import DjangoJSONEncoder
import logging

from .models import Calisan, TasarimKodu, Is, IsAtama, MonteCarloSonuc, GenetikSonuc, TaguchiSonucu, MonteCarloTasarimSonuc, PerformansDegerlendirme, GecmisPerformansVerisi, GecmisSureVerisi
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import GenetikSonucSerializer
from .algorithms.monte_carlo_simulasyon import monte_carlo_simulasyonu, performans_verilerini_oku
from .algorithms.geneticalgorithm import main as run_genetic_algorithm
from .algorithms.taguchi import main as taguchi_main_function
from asgiref.sync import async_to_sync


# Logger yapılandırması
logger = logging.getLogger(__name__)


def index(request):
    total_calisan = Calisan.objects.count()
    total_tasarim_kodu = TasarimKodu.objects.count()
    
    devam_eden_isler = Is.objects.filter(durum='devam_ediyor').count()
    beklemede_isler = Is.objects.filter(durum='beklemede').count()
    tamamlanan_isler = Is.objects.filter(durum='tamamlandi').count()
    
    aktif_isler = devam_eden_isler + beklemede_isler
    
    context = {
        'total_calisan': total_calisan,
        'total_tasarim_kodu': total_tasarim_kodu,
        'aktif_isler': aktif_isler,
        'devam_eden_isler': devam_eden_isler,
        'beklemede_isler': beklemede_isler,
        'tamamlanan_isler': tamamlanan_isler,
    }
    return render(request, 'cizelgeleme/index.html', context)


def tasarim_kodlari(request):
    if request.method == 'GET':
        kodlar = TasarimKodu.objects.all()
        return render(request, 'cizelgeleme/tasarim_kodlari.html', {'tasarim_kodlari': kodlar})


@csrf_exempt
@require_http_methods(["POST"])
def tasarim_kodu_ekle(request):
    try:
        data = json.loads(request.body)
        TasarimKodu.objects.create(
            kod=data['kod'],
            urun_adi=data['urun_adi'],
            tahmini_montaj_suresi=data['montaj_suresi'],
            ortalama_uretim_adedi=data['uretim_adedi'],
            ustabasi=data['personel_ihtiyaci']['ustabasi'],
            kalifiyeli=data['personel_ihtiyaci']['kalifiyeli'],
            cirak=data['personel_ihtiyaci']['cirak'],
            minimum_yetkinlik_seviyesi=1,
            optimum_yetkinlik_seviyesi=1,
            zorluk_derecesi=1,
            departman="Genel"
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def tasarim_kodu_sil(request):
    try:
        data = json.loads(request.body)
        kod = data.get('kod')
        tasarim = TasarimKodu.objects.get(kod=kod)
        tasarim.delete()
        return JsonResponse({'success': True})
    except TasarimKodu.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Tasarım kodu bulunamadı.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def calisan_ekle(request):
    try:
        data = json.loads(request.body)
        yeni = Calisan.objects.create(
            ad_soyad=data.get('ad'),
            yetkinlik_seviyesi=data.get('yetkinlik_seviyesi'),
            tecrube_yili=data.get('tecrube'),
            verimlilik_puani=data.get('verimlilik')
        )
        return JsonResponse({'success': True, 'id': yeni.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def calisan_sil(request):
    try:
        data = json.loads(request.body)
        ad = data.get('ad')
        calisan = Calisan.objects.get(ad_soyad=ad)
        calisan.delete()
        return JsonResponse({'success': True})
    except Calisan.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Çalışan bulunamadı.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def calisanlar(request):
    calisanlar = Calisan.objects.all().order_by('yetkinlik_seviyesi')
    for c in calisanlar:
        c.verimlilik_yuzde = round(c.verimlilik_puani * 100, 2)
    return render(request, 'cizelgeleme/calisanlar.html', {'calisanlar': calisanlar})


@require_http_methods(["GET"])
def son_simulasyon_verileri(request):
    try:
        # En son simülasyon sonuçlarını al
        monte_carlo_sonuclari = MonteCarloSonuc.objects.select_related('calisan').all()
        tasarim_bazli_sonuclar = MonteCarloTasarimSonuc.objects.select_related('calisan', 'tasarim').all()

        calisan_sonuclari = {}

        for sonuc in monte_carlo_sonuclari:
            if sonuc.calisan:
                calisan_adi = sonuc.calisan.ad_soyad
                if calisan_adi not in calisan_sonuclari:
                    calisan_sonuclari[calisan_adi] = {
                        'ortalama_performans': sonuc.ortalama_performans,
                        'risk_skoru': sonuc.risk_skoru,
                        'gecikme_olasiligi': sonuc.gecikme_olasiligi,
                        'performans_kararliligi': sonuc.performans_kararliligi,
                        'tasarim_bazli_performans': []
                    }

        for tasarim_sonuc in tasarim_bazli_sonuclar:
            if tasarim_sonuc.calisan and tasarim_sonuc.tasarim:
                calisan_adi = tasarim_sonuc.calisan.ad_soyad
                if calisan_adi in calisan_sonuclari:
                    calisan_sonuclari[calisan_adi]['tasarim_bazli_performans'].append({
                        'tasarim_kodu': tasarim_sonuc.tasarim.kod,
                        'performans_ort': tasarim_sonuc.ortalama,
                        'risk': tasarim_sonuc.risk_skoru,
                        'gecikme': tasarim_sonuc.gecikme_olasiligi
                    })

        return JsonResponse({
            "success": True,
            "monte_carlo_sonuclari": calisan_sonuclari
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "mesaj": f"Simülasyon verileri alınırken hata oluştu: {str(e)}"
        }, status=500)


@require_http_methods(["GET"])
def son_genetik_sonuclari(request):
    return JsonResponse({"success": True, "genetik_sonuclari": {}})


@csrf_exempt
@require_http_methods(["POST"])
def genetik_optimizasyon(request):
    try:
        genetik_sonuclari = GenetikSonuc.objects.all()
        # Verileri JSON formatına dönüştürün
        data = {
            "genetik_sonuclari": list(genetik_sonuclari.values())
        }
        return JsonResponse({"success": True, "genetik_sonuclari": data})
    except Exception as e:
        return JsonResponse({"success": False, "mesaj": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def is_kaydet(request):
    try:
        data = json.loads(request.body)
        tasarim_kodu_str = data.get("kod")
        oncelik = data.get("oncelik")
        taseron_onayi = data.get("taseron_onayi", False)

        tasarim = TasarimKodu.objects.get(kod=tasarim_kodu_str)
        
        genetik_sonuc = GenetikSonuc.objects.prefetch_related('atamalar__calisan').filter(
            tasarim=tasarim, 
            senaryo=oncelik
        ).order_by('-kayit_tarihi').first()

        if not genetik_sonuc:
            return JsonResponse({"success": False, "mesaj": f"'{tasarim.kod}' için '{oncelik}' senaryosunda genetik algoritma sonucu bulunamadı. Lütfen önce optimizasyonu çalıştırın."})

        aktif_isler = Is.objects.filter(durum__in=['beklemede', 'devam_ediyor'])
        mesgul_calisan_idler = set(IsAtama.objects.filter(is_objesi__in=aktif_isler).values_list('calisan_id', flat=True))

        ihtiyac = {
            'ustabasi': tasarim.ustabasi,
            'kalifiyeli': tasarim.kalifiyeli,
            'cirak': tasarim.cirak
        }
        
        atanacak_calisanlar = {'ustabasi': [], 'kalifiyeli': [], 'cirak': []}
        atanan_calisan_idler_bu_is_icin = set()
        
        tum_adaylar = genetik_sonuc.atamalar.select_related('calisan').order_by('-uygunluk_orani')

        seviyeler = ['ustabasi', 'kalifiyeli', 'cirak']
        for seviye in seviyeler:
            gereken_sayi = ihtiyac[seviye]
            if gereken_sayi == 0: continue

            adaylar = [
                aday for aday in tum_adaylar
                if aday.seviye == seviye and aday.calisan.id not in mesgul_calisan_idler and aday.calisan.id not in atanan_calisan_idler_bu_is_icin
            ]
            
            for aday in adaylar:
                if len(atanacak_calisanlar[seviye]) < gereken_sayi:
                    atanacak_calisanlar[seviye].append(aday.calisan)
                    atanan_calisan_idler_bu_is_icin.add(aday.calisan.id)
        
        eksik_personel = {
            'ustabasi': ihtiyac['ustabasi'] - len(atanacak_calisanlar['ustabasi']),
            'kalifiyeli': ihtiyac['kalifiyeli'] - len(atanacak_calisanlar['kalifiyeli']),
            'cirak': ihtiyac['cirak'] - len(atanacak_calisanlar['cirak'])
        }

        toplam_eksik = sum(eksik_personel.values())

        if toplam_eksik > 0 and not taseron_onayi:
            return JsonResponse({
                "success": False,
                "personel_yetersiz": True,
                "eksik_personel": eksik_personel,
                "mesaj": "Yeterli sayıda müsait çalışan bulunamadı."
            })

        with transaction.atomic():
            # Taguchi optimizasyonundan optimum süreyi al
            taguchi_sonucu = TaguchiSonucu.objects.filter(tasarim_kodu=tasarim.kod).order_by('-guncellenme_tarihi').first()
            if taguchi_sonucu:
                kalan_sure = taguchi_sonucu.optimum_sure
            else:
                kalan_sure = tasarim.tahmini_montaj_suresi

            yeni_is = Is.objects.create(
                tasarim=tasarim,
                proje_adi=data.get("proje_adi"),
                teslimat_tarihi=parse_date(data.get("teslimat_tarihi")),
                durum=data.get("durum", "beklemede"),
                oncelik=oncelik,
                kalan_sure=kalan_sure,
                # Taşeron sayılarını kaydet
                taseron_ustabasi=eksik_personel.get('ustabasi', 0) if taseron_onayi else 0,
                taseron_kalifiyeli=eksik_personel.get('kalifiyeli', 0) if taseron_onayi else 0,
                taseron_cirak=eksik_personel.get('cirak', 0) if taseron_onayi else 0
            )

            # Sadece gerçek çalışanlar için atama kaydı oluştur
            for seviye, calisan_listesi in atanacak_calisanlar.items():
                for calisan in calisan_listesi:
                    IsAtama.objects.create(
                        is_objesi=yeni_is,
                        calisan=calisan,
                        seviye=seviye
                    )
            
            mesaj = "İş başarıyla kaydedildi ve atamalar yapıldı."
            if taseron_onayi and toplam_eksik > 0:
                mesaj = "İş, taşeron desteğiyle başarıyla kaydedildi."

            return JsonResponse({"success": True, "mesaj": mesaj})

    except TasarimKodu.DoesNotExist:
        return JsonResponse({"success": False, "mesaj": "Geçersiz tasarım kodu."}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "mesaj": f"Bir hata oluştu: {str(e)}"}, status=500)


@require_http_methods(["GET"])
def son_atama_detayi(request):
    return JsonResponse({
        "success": True,
        "data": {
            "is_bilgileri": {
                "tasarim_kodu": "N/A",
                "urun_adi": "N/A"
            },
            "atanan_calisan": "N/A",
            "atama_detaylari": {
                "yetkinlik_uyumu": 0,
                "tecrube_puani": 0,
                "verimlilik_puani": 0,
                "genetik_uygunluk": 0,
                "tecrube_aciklama": "Veri yok"
            },
            "alternatif_calisanlar": []
        }
    })


@require_http_methods(["GET"])
def rapor_haftalik(request):
    return JsonResponse({"success": True, "rapor_url": "/raporlar/haftalik.pdf"})


@require_http_methods(["GET"])
def rapor_personel(request, ad):
    return JsonResponse({"success": True, "rapor_url": f"/raporlar/personel_{ad}.pdf"})


@require_http_methods(["GET"])
def rapor_excel(request):
    return JsonResponse({"success": True, "rapor_url": "/raporlar/performans.xlsx"})


@csrf_exempt
@require_http_methods(["POST"])
def is_guncelle(request):
    try:
        data = json.loads(request.body)
        is_id = data.get("is_id")
        durum = data.get("durum")
        oncelik = data.get("oncelik")

        is_obj = Is.objects.get(id=is_id)
        
        if durum is not None:
            is_obj.durum = durum
        if oncelik is not None:
            is_obj.oncelik = oncelik
            
        is_obj.save()

        return JsonResponse({"success": True})
    except Is.DoesNotExist:
        return JsonResponse({"success": False, "mesaj": "İş bulunamadı."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "mesaj": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def performans_degerlendirme_kaydet(request):
    try:
        data = json.loads(request.body)
        is_id = data.get('is_id')
        degerlendirmeler = data.get('degerlendirmeler', [])
        notlar = data.get('notlar', '')

        if not is_id:
            return JsonResponse({'success': False, 'message': 'İş ID eksik.'}, status=400)

        is_nesnesi = get_object_or_404(Is, pk=is_id)

        # İşlemi atomik hale getirerek veri bütünlüğünü sağlıyoruz
        with transaction.atomic():
            # Tamamlanma süresini ve durumunu güncelle
            tamamlanma_suresi = data.get('tamamlanma_suresi')
            is_nesnesi.durum = 'tamamlandi'
            if tamamlanma_suresi:
                # Geçmiş Süre Verisi'ni Taguchi için kaydet
                GecmisSureVerisi.objects.create(
                    tasarim=is_nesnesi.tasarim,
                    departman=is_nesnesi.tasarim.departman,
                    urun_adi=is_nesnesi.tasarim.urun_adi,
                    sure=int(tamamlanma_suresi),
                    kayit_index=GecmisSureVerisi.objects.count() + 1
                )
            is_nesnesi.save()

            # Performans Değerlendirmelerini kaydet/güncelle
            for degerlendirme_data in degerlendirmeler:
                calisan_id = degerlendirme_data.get('calisan_id')
                puan = degerlendirme_data.get('puan')

                if calisan_id and puan:
                    calisan = get_object_or_404(Calisan, pk=calisan_id)
                    
                    # update_or_create kullanarak veri tekrarını engelliyoruz
                    PerformansDegerlendirme.objects.update_or_create(
                        is_degerlendirmesi=is_nesnesi,
                        calisan=calisan,
                        defaults={
                            'puan': puan,
                            'notlar': notlar
                        }
                    )
                    
                    # Monte Carlo simülasyonu için geçmiş performans verisi oluştur
                    verimlilik_puani = float(puan) / 10.0  # Puanı 0-1 arasına normalize et
                    
                    # Bu tasarıma ait yeni proje index'ini belirle
                    proje_index = GecmisPerformansVerisi.objects.filter(
                        tasarim=is_nesnesi.tasarim
                    ).count() + 1

                    GecmisPerformansVerisi.objects.create(
                        tasarim=is_nesnesi.tasarim,
                        calisan=calisan,
                        verimlilik_puani=verimlilik_puani,
                        proje_index=proje_index
                    )
        
        return JsonResponse({'success': True, 'message': 'Değerlendirme başarıyla kaydedildi.'})

    except Is.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'İş bulunamadı.'}, status=404)
    except Exception as e:
        logger.error(f"Performans değerlendirme hatası: {e}", exc_info=True)
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def is_sil(request):
    try:
        data = json.loads(request.body)
        is_id = data.get("is_id")

        is_obj = Is.objects.get(id=is_id)

        # İlişkili atamaları da sil (on_delete=models.CASCADE zaten yeterli ama manuel de temizlenebilir)
        IsAtama.objects.filter(is_objesi=is_obj).delete()

        # İşi sil
        is_obj.delete()

        return JsonResponse({"success": True})
    except Is.DoesNotExist:
        return JsonResponse({"success": False, "mesaj": "İş bulunamadı."}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "mesaj": str(e)}, status=500)


@require_http_methods(["GET"])
def get_calisanlar_for_is(request):
    is_id = request.GET.get('is_id')
    if not is_id:
        return JsonResponse({'success': False, 'message': 'İş IDsi gerekli.'}, status=400)
    
    try:
        is_obj = Is.objects.get(id=is_id)
        atanan_calisanlar = IsAtama.objects.filter(is_objesi=is_obj).select_related('calisan')
        
        calisan_listesi = []
        for atama in atanan_calisanlar:
            calisan_listesi.append({
                'id': atama.calisan.id,
                'ad_soyad': atama.calisan.ad_soyad,
                'seviye': atama.seviye
            })
            
        return JsonResponse({'success': True, 'calisanlar': calisan_listesi})
    except Is.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'İş bulunamadı.'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def taguchi_optimizasyon(request):
    try:
        taguchi_sonuclari = TaguchiSonucu.objects.all()
        # Verileri JSON formatına dönüştürün
        data = {
            "taguchi_sonuclari": list(taguchi_sonuclari.values())
        }
        return JsonResponse({"success": True, "taguchi_sonuclari": data})
    except Exception as e:
        return JsonResponse({"success": False, "mesaj": str(e)}, status=500)


def is_cizelgesi(request):
    # İş listesi ve tasarım kodları
    is_listesi = Is.objects.select_related('tasarim').prefetch_related('atananlar__calisan')
    tasarim_kodlari = TasarimKodu.objects.all()

    durum_map = {
        'beklemede': 'Beklemede',
        'devam_ediyor': 'Devam Ediyor',
        'tamamlandi': 'Tamamlandı'
    }

    gorsel_is_listesi = []
    for is_obj in is_listesi:
        atanan_calisanlar = {'ustabasi': [], 'kalifiyeli': [], 'cirak': []}
        for atama in is_obj.atananlar.all():
            if atama.calisan:
                atanan_calisanlar[atama.seviye].append(atama.calisan.ad_soyad)
        
        # Taşeronları ekle
        if is_obj.taseron_ustabasi > 0:
            atanan_calisanlar['ustabasi'].extend([f"Taşeron İşçi (Ustabaşı)"] * is_obj.taseron_ustabasi)
        if is_obj.taseron_kalifiyeli > 0:
            atanan_calisanlar['kalifiyeli'].extend([f"Taşeron İşçi (Kalifiyeli)"] * is_obj.taseron_kalifiyeli)
        if is_obj.taseron_cirak > 0:
            atanan_calisanlar['cirak'].extend([f"Taşeron İşçi (Çırak)"] * is_obj.taseron_cirak)

        is_obj.atanan_calisanlar = atanan_calisanlar

        gorsel_is_listesi.append({
            'id': is_obj.id,
            'kod': is_obj.tasarim.kod,
            'proje_adi': is_obj.proje_adi,
            'teslimat_tarihi': is_obj.teslimat_tarihi,
            'oncelik': is_obj.oncelik,
            'durum': is_obj.durum,
            'durum_gosterim': durum_map.get(is_obj.durum, is_obj.durum),
            'kalan_sure': is_obj.kalan_sure,
            'atanan_calisanlar': atanan_calisanlar
        })

    # Monte Carlo sonuçlarını hazırla
    monte_carlo_sonuclari = MonteCarloSonuc.objects.select_related('calisan').all()
    tasarim_bazli_sonuclar = MonteCarloTasarimSonuc.objects.select_related('calisan', 'tasarim').all()
    
    calisan_sonuclari = {}
    for sonuc in monte_carlo_sonuclari:
        if sonuc.calisan:
            calisan_adi = sonuc.calisan.ad_soyad
            if calisan_adi not in calisan_sonuclari:
                calisan_sonuclari[calisan_adi] = {
                    'ortalama_performans': sonuc.ortalama_performans,
                    'risk_skoru': sonuc.risk_skoru,
                    'gecikme_olasiligi': sonuc.gecikme_olasiligi,
                    'performans_kararliligi': sonuc.performans_kararliligi,
                    'tasarim_bazli_performans': []
                }

    for tasarim_sonuc in tasarim_bazli_sonuclar:
        if tasarim_sonuc.calisan and tasarim_sonuc.tasarim:
            calisan_adi = tasarim_sonuc.calisan.ad_soyad
            if calisan_adi in calisan_sonuclari:
                calisan_sonuclari[calisan_adi]['tasarim_bazli_performans'].append({
                    'tasarim_kodu': tasarim_sonuc.tasarim.kod,
                    'performans_ort': tasarim_sonuc.ortalama,
                    'risk': tasarim_sonuc.risk_skoru,
                    'gecikme': tasarim_sonuc.gecikme_olasiligi
                })

    # Genetik Algoritma sonuçlarını al ve grupla
    genetik_sonuclari = GenetikSonuc.objects.select_related('tasarim').prefetch_related(
        'atamalar', 
        'atamalar__calisan'
    ).order_by('-kayit_tarihi')

    # Genetik sonuçları senaryolara göre grupla
    genetik_gruplu = {
        'normal': [],
        'kritik': []
    }
    for sonuc in genetik_sonuclari:
        atamalar = list(sonuc.atamalar.filter(atanma_tipi='atanan').select_related('calisan'))
        alternatifler = list(sonuc.atamalar.filter(atanma_tipi='alternatif').select_related('calisan').order_by('-uygunluk_orani'))
        if atamalar:
            genetik_gruplu[sonuc.senaryo].append({
                'tasarim_kodu': sonuc.tasarim.kod,
                'atamalar': atamalar,
                'alternatifler': alternatifler,
                'kayit_tarihi': sonuc.kayit_tarihi
            })

    # Taguchi sonuçlarını al
    taguchi_sonuclari = TaguchiSonucu.objects.all().order_by('-guncellenme_tarihi')

    # İstatistikler
    tamamlanan = Is.objects.filter(durum='tamamlandi').count()
    devam_eden = Is.objects.filter(durum='devam_ediyor').count()
    bekleyen = Is.objects.filter(durum='beklemede').count()

    # Monte Carlo istatistikleri
    if monte_carlo_sonuclari.exists():
        ortalama_performans = monte_carlo_sonuclari.aggregate(Avg('ortalama_performans'))['ortalama_performans__avg']
        ortalama_risk = monte_carlo_sonuclari.aggregate(Avg('risk_skoru'))['risk_skoru__avg']
    else:
        ortalama_performans = 0
        ortalama_risk = 0

    # Taguchi istatistikleri
    if taguchi_sonuclari.exists():
        ortalama_iyilestirme = taguchi_sonuclari.aggregate(Avg('iyilestirme_orani'))['iyilestirme_orani__avg']
    else:
        ortalama_iyilestirme = 0

    is_listesi_json = json.dumps(gorsel_is_listesi, cls=DjangoJSONEncoder)

    context = {
        'is_listesi': gorsel_is_listesi,
        'tasarim_kodlari': tasarim_kodlari,
        'monte_carlo_sonuclari': calisan_sonuclari,
        'genetik_gruplu': genetik_gruplu,
        'taguchi_sonuclari': taguchi_sonuclari,
        'tamamlanan': tamamlanan,
        'devam_eden': devam_eden,
        'bekleyen': bekleyen,
        'istatistikler': {
            'ortalama_performans': ortalama_performans,
            'ortalama_risk': ortalama_risk,
            'ortalama_iyilestirme': ortalama_iyilestirme
        },
        'is_listesi_json': is_listesi_json
    }

    return render(request, 'cizelgeleme/is_cizelgesi.html', context)


@require_http_methods(["GET"])
def son_taguchi_sonuclari(request):
    return JsonResponse({
        "success": True,
        "taguchi_sonuclari": {
            "best_parameters": {},
            "average_improvement": 0
        }
    })

@api_view(['GET'])
def get_genetik_sonuclari(request):
    queryset = GenetikSonuc.objects.prefetch_related('atamalar__calisan').select_related('tasarim')
    serializer = GenetikSonucSerializer(queryset, many=True)

    sonuc_dict = {}

    for entry in serializer.data:
        kod = entry['tasarim_kodu']
        senaryo = entry['senaryo']
        atanan = [a for a in entry['atamalar'] if a['atanma_tipi'] == 'atanan']
        alternatif = [a for a in entry['atamalar'] if a['atanma_tipi'] == 'alternatif']

        if kod not in sonuc_dict:
            sonuc_dict[kod] = {}

        sonuc_dict[kod][senaryo] = {
            "atanan": atanan,
            "alternatif": alternatif,
            "kayit_tarihi": entry['kayit_tarihi']
        }

    return Response(sonuc_dict)

@csrf_exempt
@require_http_methods(["POST"])
def performans_simulasyonu(request):
    try:
        # Monte Carlo sonuçlarını al
        monte_carlo_sonuclari = MonteCarloSonuc.objects.select_related('calisan').all()
        tasarim_bazli_sonuclar = MonteCarloTasarimSonuc.objects.select_related('calisan', 'tasarim').all()

        # Çalışan bazlı sonuçları hazırla
        calisan_sonuclari = {}

        # Monte Carlo sonuçlarını işle
        for sonuc in monte_carlo_sonuclari:
            if sonuc.calisan:
                calisan_adi = sonuc.calisan.ad_soyad
                calisan_sonuclari[calisan_adi] = {
                    'ortalama_performans': float(sonuc.ortalama_performans),
                    'risk_skoru': float(sonuc.risk_skoru),
                    'gecikme_olasiligi': float(sonuc.gecikme_olasiligi),
                    'performans_kararliligi': float(sonuc.performans_kararliligi),
                    'tasarim_bazli_performans': []
                }

        # Tasarım bazlı sonuçları ekle
        for tasarim_sonuc in tasarim_bazli_sonuclar:
            if tasarim_sonuc.calisan and tasarim_sonuc.tasarim:
                calisan_adi = tasarim_sonuc.calisan.ad_soyad
                if calisan_adi in calisan_sonuclari:
                    calisan_sonuclari[calisan_adi]['tasarim_bazli_performans'].append({
                        'tasarim_kodu': tasarim_sonuc.tasarim.kod,
                        'performans_ort': float(tasarim_sonuc.ortalama),
                        'risk': float(tasarim_sonuc.risk_skoru),
                        'gecikme': float(tasarim_sonuc.gecikme_olasiligi)
                    })

        # Sonuçları kontrol et
        if not calisan_sonuclari:
            return JsonResponse({
                "success": False,
                "mesaj": "Simülasyon sonuçları bulunamadı."
            })
            
        return JsonResponse({
            "success": True,
            "monte_carlo_sonuclari": calisan_sonuclari
            })

    except Exception as e:
        import traceback
        return JsonResponse({
            "success": False,
            "mesaj": f"Simülasyon sırasında bir hata oluştu: {str(e)}",
            "hata_detay": traceback.format_exc()
        }, status=500)

def raporlama_sayfasi(request):
    """
    Raporlama ve analiz sayfasını render eder.
    """
    # Genel Pano Verileri
    toplam_personel_sayisi = Calisan.objects.exclude(ad_soyad__icontains='Taşeron İşçi').count()

    # Aktif personel sayısı (beklemede veya devam eden işlerdeki)
    aktif_isler = Is.objects.filter(durum__in=['beklemede', 'devam_ediyor'])
    aktif_personel_idler = IsAtama.objects.filter(is_objesi__in=aktif_isler).values_list('calisan_id', flat=True).distinct()
    aktif_personel_sayisi = len(aktif_personel_idler)
    
    # Performans skorları
    genel_performans_skoru = PerformansDegerlendirme.objects.aggregate(ortalama=Avg('puan'))['ortalama'] or 0

    tamamlanan_is_sayisi = Is.objects.filter(durum='tamamlandi').count()

    # Tamamlanmış İşler Arşivi Verileri
    tamamlanmis_isler = []
    # İlgili tüm verileri önceden çekerek N+1 probleminden kaçınıyoruz
    sorgu = Is.objects.filter(durum='tamamlandi').select_related('tasarim').prefetch_related(
        'degerlendirmeler__calisan'
    ).annotate(
        son_degerlendirme_tarihi=models.Max('degerlendirmeler__degerlendirme_tarihi')
    ).order_by('-son_degerlendirme_tarihi').distinct()

    for is_nesnesi in sorgu:
        degerlendirmeler_listesi = []
        genel_notlar = ""
        # Bu işe ait tüm değerlendirmeleri döngü ile alıyoruz
        for degerlendirme in is_nesnesi.degerlendirmeler.all():
            degerlendirmeler_listesi.append({
                'calisan_adi': degerlendirme.calisan.ad_soyad,
                'puan': degerlendirme.puan
            })
            # Genel notları (eğer varsa) alıyoruz
            if degerlendirme.notlar:
                genel_notlar = degerlendirme.notlar

        tamamlanmis_isler.append({
            'id': is_nesnesi.id,
            'proje_adi': is_nesnesi.proje_adi,
            'tasarim_kodu': is_nesnesi.tasarim.kod,
            'tamamlanma_tarihi': is_nesnesi.son_degerlendirme_tarihi,
            'degerlendirmeler': degerlendirmeler_listesi,
            'notlar': genel_notlar
        })

    en_yuksek_performansli = Calisan.objects.annotate(
        ortalama_puan=Avg('performansdegerlendirme__puan')
    ).order_by('-ortalama_puan').first()

    # Personel Tablosu Verileri
    personel_verileri = []
    # Taşeron işçileri hariç tutarak ve puana göre sıralayarak sorgulama
    tum_calisanlar = Calisan.objects.exclude(ad_soyad__icontains='Taşeron İşçi').annotate(
        ortalama_puan=Avg('performansdegerlendirme__puan', default=0)
    ).order_by('-ortalama_puan')
    
    seviye_map = {1: 'Ustabaşı', 2: 'Kalifiyeli', 3: 'Çırak'}

    for calisan in tum_calisanlar:
        # Tamamladığı iş sayısı
        tamamlanan_isler_sayisi = Is.objects.filter(
            durum='tamamlandi',
            atananlar__calisan=calisan
        ).distinct().count()

        # Monte Carlo sonuçları
        son_mc_sonuc = calisan.montecarlosonuc_set.order_by('-simulasyon_zamani').first()
        mc_performans = son_mc_sonuc.ortalama_performans * 100 if son_mc_sonuc else 0
        mc_risk = son_mc_sonuc.risk_skoru * 100 if son_mc_sonuc else 0
        
        personel_verileri.append({
            'ad_soyad': calisan.ad_soyad,
            'seviye': seviye_map.get(calisan.yetkinlik_seviyesi, 'Bilinmiyor'),
            'tamamladigi_isler': tamamlanan_isler_sayisi,
            'ortalama_puan': calisan.ortalama_puan,
            'mc_performans': mc_performans,
            'mc_risk': mc_risk,
        })

    # Geciken iş sayısı
    bugun = timezone.now().date()
    geciken_is_sayisi = Is.objects.filter(durum__in=['beklemede', 'devam_ediyor'], teslimat_tarihi__lt=bugun).count()

    # Kapasite kullanımı
    kisi_basi_gunluk_kapasite = 480  # dakika
    toplam_kapasite = aktif_personel_sayisi * kisi_basi_gunluk_kapasite
    gerceklesen_is_yuku = Is.objects.filter(durum='devam_ediyor').aggregate(toplam=Sum('kalan_sure'))['toplam'] or 0
    if toplam_kapasite > 0:
        kapasite_kullanimi = (gerceklesen_is_yuku / toplam_kapasite) * 100
    else:
        kapasite_kullanimi = 0

    context = {
        'toplam_personel_sayisi': toplam_personel_sayisi,
        'aktif_personel_sayisi': aktif_personel_sayisi,
        'genel_performans_skoru': genel_performans_skoru,
        'tamamlanan_is_sayisi': tamamlanan_is_sayisi,
        'geciken_is_sayisi': geciken_is_sayisi,
        'kapasite_kullanimi': kapasite_kullanimi,
        'en_yuksek_performansli': en_yuksek_performansli,
        'personel_verileri': personel_verileri,
        'tamamlanmis_isler': tamamlanmis_isler,
    }
    return render(request, 'cizelgeleme/raporlama.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def arsivlenmis_is_sil(request):
    try:
        data = json.loads(request.body)
        is_id = data.get('is_id')
        if not is_id:
            return JsonResponse({'success': False, 'message': 'İş ID eksik.'}, status=400)
        
        is_nesnesi = Is.objects.get(pk=is_id, durum='tamamlandi')
        is_nesnesi.delete()
        
        return JsonResponse({'success': True, 'message': 'İş başarıyla arşivden silindi.'})
    except Is.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'İş bulunamadı veya zaten silinmiş.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@require_http_methods(["GET"])
def performans_trendi_api(request):
    try:
        # Son 30 günün tarih aralığını belirle
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=29)

        # Veritabanından son 30 günün performans değerlendirmelerini çek
        trend_data_qs = (
            PerformansDegerlendirme.objects
            .filter(degerlendirme_tarihi__date__range=[start_date, end_date])
            .annotate(gun=TruncDate('degerlendirme_tarihi'))
            .values('gun')
            .annotate(ortalama_puan=Avg('puan'))
            .order_by('gun')
        )
        
        # Hızlı arama için bir sözlük oluştur
        data_map = {item['gun']: item['ortalama_puan'] for item in trend_data_qs}

        # Son 30 gün için tüm tarihleri oluştur
        labels = []
        data = []
        for i in range(30):
            current_date = start_date + timedelta(days=i)
            labels.append(current_date.strftime('%d %b'))
            data.append(data_map.get(current_date, 0)) # O gün için veri yoksa 0 kullan

        return JsonResponse({
            'success': True,
            'labels': labels,
            'data': data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'mesaj': str(e)}, status=500)