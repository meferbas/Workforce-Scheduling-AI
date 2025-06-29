# cizelgeleme/serializers.py

from rest_framework import serializers
from .models import GenetikSonuc, GenetikAtama, Calisan

class CalisanMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calisan
        fields = ['ad_soyad']

class GenetikAtamaSerializer(serializers.ModelSerializer):
    calisan = CalisanMiniSerializer()

    class Meta:
        model = GenetikAtama
        fields = ['calisan', 'seviye', 'atanma_tipi', 'uygunluk_orani']

class GenetikSonucSerializer(serializers.ModelSerializer):
    tasarim_kodu = serializers.CharField(source='tasarim.kod', read_only=True)
    atamalar = GenetikAtamaSerializer(many=True)

    class Meta:
        model = GenetikSonuc
        fields = ['tasarim_kodu', 'senaryo', 'kayit_tarihi', 'atamalar']
