from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('calisanlar/', views.calisanlar, name='calisanlar'),
    path('tasarim-kodlari/', views.tasarim_kodlari, name='tasarim_kodlari'),
    path('api/calisan-ekle', views.calisan_ekle, name='calisan_ekle'),
    path('api/calisan-sil', views.calisan_sil, name='calisan_sil'),
    path('is-cizelgesi/', views.is_cizelgesi, name='is_cizelgesi'),
    path('api/tasarim-kodu-ekle', views.tasarim_kodu_ekle, name='tasarim_kodu_ekle'),
    path('api/tasarim-kodu-sil', views.tasarim_kodu_sil, name='tasarim_kodu_sil'),   

    path('api/is-kaydet', views.is_kaydet, name='is_kaydet'),
    path('api/is-guncelle/', views.is_guncelle, name='is_guncelle'),
    path('api/is-sil', views.is_sil, name='is_sil'),
    path('performans-simulasyonu/', views.performans_simulasyonu, name='performans_simulasyonu'),
    path('api/son-simulasyon-verileri', views.son_simulasyon_verileri, name='son_simulasyon_verileri'),
    path('api/genetik-optimizasyon', views.genetik_optimizasyon, name='genetik_optimizasyon'),
    path('api/son-genetik-sonuclari', views.son_genetik_sonuclari, name='son_genetik_sonuclari'),
    path('api/taguchi-optimizasyon', views.taguchi_optimizasyon, name='taguchi_optimizasyon'),
    path('api/son-atama-detayi', views.son_atama_detayi, name='son_atama_detayi'),
    path('api/performans-degerlendirme-kaydet/', views.performans_degerlendirme_kaydet, name='performans_degerlendirme_kaydet'),
    path('api/genetik-sonuclari/', views.get_genetik_sonuclari, name='genetik_sonuclari'),
    path('api/son-taguchi-sonuclari', views.son_taguchi_sonuclari, name='son_taguchi_sonuclari'),

    # Raporlar
    path('api/rapor/haftalik', views.rapor_haftalik, name='rapor_haftalik'),
    path('api/rapor/personel/<str:ad>', views.rapor_personel, name='rapor_personel'),
    path('api/rapor/excel', views.rapor_excel, name='rapor_excel'),
    path('api/get-calisanlar-for-is/', views.get_calisanlar_for_is, name='get_calisanlar_for_is'),

    # Raporlama sayfası
    path('raporlama/', views.raporlama_sayfasi, name='raporlama'),
    path('api/performans-trendi/', views.performans_trendi_api, name='performans_trendi_api'),
    path('api/arsivlenmis-is-sil/', views.arsivlenmis_is_sil, name='arsivlenmis_is_sil'),
]
