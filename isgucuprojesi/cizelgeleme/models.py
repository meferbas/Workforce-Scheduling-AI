from django.db import models

class Calisan(models.Model):
    ad_soyad = models.CharField(max_length=100)
    yetkinlik_seviyesi = models.PositiveSmallIntegerField()
    tecrube_yili = models.FloatField()
    verimlilik_puani = models.FloatField()

    def __str__(self):
        return self.ad_soyad
class TasarimKodu(models.Model):
    kod = models.CharField(max_length=50, unique=True)
    urun_adi = models.CharField(max_length=150)
    tahmini_montaj_suresi = models.FloatField()
    minimum_yetkinlik_seviyesi = models.PositiveSmallIntegerField()
    optimum_yetkinlik_seviyesi = models.PositiveSmallIntegerField()
    ortalama_uretim_adedi = models.PositiveIntegerField()
    zorluk_derecesi = models.PositiveSmallIntegerField()
    departman = models.CharField(max_length=100)

    # Personel ihtiyacı ayrı sütunlar olarak tutulacak
    ustabasi = models.PositiveSmallIntegerField(default=0)
    kalifiyeli = models.PositiveSmallIntegerField(default=0)
    cirak = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"{self.kod} - {self.urun_adi}"

class PerformansDegerlendirme(models.Model):
    is_degerlendirmesi = models.ForeignKey('Is', on_delete=models.CASCADE, related_name='degerlendirmeler')
    calisan = models.ForeignKey('Calisan', on_delete=models.CASCADE)
    puan = models.PositiveSmallIntegerField(help_text="Çalışanın bu işteki performansı (1-10 arası)")
    notlar = models.TextField(blank=True, null=True, help_text="Bu değerlendirme ile ilgili ek notlar")
    degerlendirme_tarihi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.is_degerlendirmesi.proje_adi} - {self.calisan.ad_soyad}: {self.puan}/10"


class AtamaDetayi(models.Model):
    tarih = models.DateTimeField()
    tasarim_kodu = models.CharField(max_length=50)
    proje_adi = models.CharField(max_length=100)
    optimize_sure = models.FloatField()

    def __str__(self):
        return f"{self.tasarim_kodu} - {self.proje_adi} - {self.tarih}"

class AtamaKaydi(models.Model):
    SEVIYE_CHOICES = [
        ('ustabasi', 'Ustabaşı'),
        ('kalifiyeli', 'Kalifiye'),
        ('cirak', 'Çırak'),
    ]

    atama = models.ForeignKey(AtamaDetayi, on_delete=models.CASCADE, related_name='calisanlar')
    calisan = models.ForeignKey(Calisan, on_delete=models.SET_NULL, null=True)
    seviye = models.CharField(max_length=20, choices=SEVIYE_CHOICES)

    def __str__(self):
        return f"{self.calisan} → {self.atama.tasarim_kodu} ({self.seviye})"


class TaguchiSonucu(models.Model):
    tasarim_kodu = models.CharField(max_length=50, unique=True)
    optimum_sure = models.FloatField()
    optimum_seviye = models.PositiveSmallIntegerField()
    iyilestirme_orani = models.FloatField()
    method = models.CharField(max_length=100)
    departman = models.CharField(max_length=50)
    guncellenme_tarihi = models.DateTimeField()

    def __str__(self):
        return f"{self.tasarim_kodu} - {self.optimum_sure:.2f} dk"


class GenetikSonuc(models.Model):
    tasarim = models.ForeignKey(TasarimKodu, on_delete=models.CASCADE)
    senaryo = models.CharField(max_length=10, choices=[("normal", "Normal"), ("kritik", "Kritik")])
    kayit_tarihi = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tasarim', 'senaryo')

    def __str__(self):
        return f"{self.tasarim.kod} - {self.senaryo}"


class GenetikAtama(models.Model):
    sonuc = models.ForeignKey(GenetikSonuc, on_delete=models.CASCADE, related_name="atamalar")
    calisan = models.ForeignKey('Calisan', on_delete=models.SET_NULL, null=True)
    seviye = models.CharField(max_length=20)
    atanma_tipi = models.CharField(max_length=20, choices=[("atanan", "Atanan"), ("alternatif", "Alternatif")])
    uygunluk_orani = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.calisan} ({self.atanma_tipi})"


class MonteCarloSonuc(models.Model):
    calisan = models.ForeignKey('Calisan', on_delete=models.SET_NULL, null=True)
    ortalama_performans = models.FloatField()
    risk_skoru = models.FloatField()
    gecikme_olasiligi = models.FloatField()
    performans_kararliligi = models.FloatField()
    simulasyon_zamani = models.DateTimeField()

    def __str__(self):
        return f"{self.calisan} - Simülasyon"

class MonteCarloTasarimSonuc(models.Model):
    calisan = models.ForeignKey('Calisan', on_delete=models.SET_NULL, null=True)
    tasarim = models.ForeignKey('TasarimKodu', on_delete=models.SET_NULL, null=True)
    ortalama = models.FloatField()
    risk_skoru = models.FloatField()
    gecikme_olasiligi = models.FloatField()

    def __str__(self):
        return f"{self.calisan} - {self.tasarim}"
    

class GecmisPerformansVerisi(models.Model):
    tasarim = models.ForeignKey('TasarimKodu', on_delete=models.CASCADE)
    calisan = models.ForeignKey('Calisan', on_delete=models.SET_NULL, null=True)
    verimlilik_puani = models.FloatField()
    proje_index = models.PositiveIntegerField(help_text="Geçmiş projeyi temsil eden sıra numarası")

    def __str__(self):
        return f"{self.tasarim.kod} | {self.calisan.ad_soyad} | P{self.proje_index}"


class GecmisSureVerisi(models.Model):
    tasarim = models.ForeignKey('TasarimKodu', on_delete=models.CASCADE)
    departman = models.CharField(max_length=100)
    urun_adi = models.CharField(max_length=150)
    sure = models.PositiveIntegerField()
    kayit_index = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.tasarim.kod} | {self.sure} sn (#{self.kayit_index})"


class Is(models.Model):
    tasarim = models.ForeignKey('TasarimKodu', on_delete=models.CASCADE)
    proje_adi = models.CharField(max_length=150)
    teslimat_tarihi = models.DateField()
    durum = models.CharField(max_length=50, choices=[
        ('beklemede', 'Beklemede'),
        ('devam_ediyor', 'Devam Ediyor'),  # eksikse ekle
        ('tamamlandi', 'Tamamlandı')
    ])
    oncelik = models.CharField(max_length=50, choices=[
        ('normal', 'Normal'),
        ('kritik', 'Kritik')  
    ], default='normal')
    kalan_sure = models.FloatField()

    # Taşeron sayıları
    taseron_ustabasi = models.PositiveSmallIntegerField(default=0, help_text="Bu işe atanan taşeron ustabaşı sayısı")
    taseron_kalifiyeli = models.PositiveSmallIntegerField(default=0, help_text="Bu işe atanan taşeron kalifiyeli sayısı")
    taseron_cirak = models.PositiveSmallIntegerField(default=0, help_text="Bu işe atanan taşeron çırak sayısı")

    def __str__(self):
        return f"{self.proje_adi} - {self.tasarim.kod}"


class IsAtama(models.Model):
    is_objesi = models.ForeignKey('Is', on_delete=models.CASCADE, related_name='atananlar')
    calisan = models.ForeignKey('Calisan', on_delete=models.SET_NULL, null=True)
    seviye = models.CharField(max_length=20, choices=[
        ('ustabasi', 'Ustabaşı'),
        ('kalifiyeli', 'Kalifiyeli'),
        ('cirak', 'Çırak')
    ])

    def __str__(self):
        return f"{self.calisan.ad_soyad} → {self.is_objesi.proje_adi} ({self.seviye})"

