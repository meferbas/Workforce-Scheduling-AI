// Global değişken tanımlaması
let silinecekIsId = null;
let isListesi = [];

// Global fonksiyonlar
$(document).ready(function() {
window.showGenetikSonuclari = async function() {
    try {
        const response = await fetch('/api/genetik-sonuclari/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        gosterGenetikSonuclari(data);  // Bu doğru fonksiyon, id="genetikRaporu" ve id="genetikSonuclari" divlerini kullanıyor
    } catch (error) {
        console.error('Genetik sonuçları alınırken hata:', error);
        $('#genetikRaporu').html('<div class="alert alert-danger">Veri alınırken hata oluştu.</div>');
    }
};
});

function gosterGenetikSonuclari(genetik_sonuclari) {
    let sonucHTML = '<ul>';
    genetik_sonuclari.forEach(sonuc => {
        sonucHTML += `<li>${sonuc.tasarim.kod}: ${sonuc.senaryo}</li>`;
    });
    sonucHTML += '</ul>';
    $('#genetikSonuclari').html(sonucHTML);
}

function gosterAtamalar(genetikSonuclari, senaryo) {
    let html = '';

    for (const [tasarimKodu, senaryoBilgileri] of Object.entries(genetikSonuclari)) {
        const bilgiler = senaryoBilgileri[senaryo];

        if (!bilgiler || (!bilgiler.atanan || bilgiler.atanan.length === 0)) {
            continue; // Atama yoksa geç
        }

        const atananlar = bilgiler.atanan.map(a => 
            `<li>${a.calisan.ad_soyad} (${a.seviye})</li>`
        ).join('');

        const alternatifler = (bilgiler.alternatif || []).map(a => 
            `<li>${a.calisan.ad_soyad} (${a.seviye}, %${a.uygunluk_orani?.toFixed(1) ?? '-'})</li>`
        ).join('');

        html += `
            <div class="card mb-3">
                <div class="card-header bg-light">
                    <h6 class="mb-0">${tasarimKodu}</h6>
                </div>
                <div class="card-body p-2">
                    <div><strong>Atananlar:</strong></div>
                    <ul>${atananlar}</ul>
                    <div class="mt-2"><strong>Alternatifler:</strong></div>
                    <ul>${alternatifler || '<li>Yok</li>'}</ul>
                    <div class="text-muted small mt-2">
                        <i class="bi bi-clock"></i> Kayıt: ${new Date(bilgiler.kayit_tarihi).toLocaleString('tr-TR')}
                    </div>
                </div>
            </div>
        `;
    }

    if (html === '') {
        html = '<div class="alert alert-info">Bu öncelik seviyesinde atama bulunmamaktadır.</div>';
    }

    return html;
}



window.showTaguchiSonuclari = async function() {
    try {
        const response = await fetch('/api/optimizasyon-durumu');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        console.log('Taguchi sonuçları:', data);
        
        const taguchiDiv = document.getElementById('taguchiSonuclar');
        const taguchiTablo = document.getElementById('taguchiTablo');
        
        if (!taguchiDiv || !taguchiTablo) {
            console.error('Taguchi sonuçları için gerekli HTML elementleri bulunamadı');
            return;
        }

        taguchiDiv.style.display = 'block';
        taguchiTablo.innerHTML = '';

        if (!data || !data.taguchi_sonuclari || !data.taguchi_sonuclari.best_parameters) {
            console.warn('Taguchi sonuçları verisi boş veya hatalı format');
            taguchiTablo.innerHTML = '<tr><td colspan="3">Sonuç bulunamadı</td></tr>';
            return;
        }

        for (const [kod, sonuc] of Object.entries(data.taguchi_sonuclari.best_parameters)) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${kod}</td>
                <td>${sonuc.sure.toFixed(2)}</td>
                <td>${sonuc.iyilestirme_orani.toFixed(2)}%</td>
            `;
            taguchiTablo.appendChild(row);
        }
    } catch (error) {
        console.error('Taguchi sonuçları yükleme hatası:', error);
        const taguchiDiv = document.getElementById('taguchiSonuclar');
        if (taguchiDiv) {
            taguchiDiv.innerHTML = '<div class="alert alert-danger">Taguchi sonuçları yüklenirken hata oluştu</div>';
        }
    }
};

window.showGenetikDetay = function(tasarimKodu, sonuc) {
    const detayHTML = `
        <div class="modal fade" id="genetikDetayModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Genetik Algoritma Detayı - ${tasarimKodu}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Atanan Personel:</h6>
                                <div class="list-group mb-3">
                                    ${Object.entries(sonuc.atanan_calisanlar || {}).map(([seviye, calisanlar]) => {
                                        if (calisanlar && calisanlar.length > 0) {
                                            return `
                                                <div class="list-group-item">
                                                    <h6 class="mb-2">${seviye.charAt(0).toUpperCase() + seviye.slice(1)}:</h6>
                                                    ${calisanlar.map(calisan => 
                                                        `<div class="d-flex justify-content-between align-items-center">
                                                            <span>${calisan}</span>
                                                            <span class="badge bg-primary">Atandı</span>
                                                        </div>`
                                                    ).join('')}
                                                </div>
                                            `;
                                        }
                                        return '';
                                    }).join('')}
                                </div>
                            </div>
                            <div class="col-md-6">
                                <h6>Alternatif Personeller:</h6>
                                ${sonuc.alternatif_calisanlar && sonuc.alternatif_calisanlar.length > 0 ? `
                                    <div class="list-group">
                                        ${sonuc.alternatif_calisanlar
                                            .sort((a, b) => b.uygunluk - a.uygunluk)
                                            .map(alt => {
                                                const seviyeRenk = {
                                                    'ustabasi': 'danger',
                                                    'kalifiyeli': 'warning',
                                                    'cirak': 'info'
                                                };
                                                return `
                                                    <div class="list-group-item d-flex justify-content-between align-items-center">
                                                        <div>
                                                            <span class="badge bg-${seviyeRenk[alt.seviye]}">${alt.seviye.charAt(0).toUpperCase() + alt.seviye.slice(1)}</span>
                                                            ${alt.calisan}
                                                        </div>
                                                        <span class="badge bg-secondary">Uygunluk: ${alt.uygunluk.toFixed(1)}</span>
                                                    </div>
                                                `;
                                            }).join('')}
                                    </div>
                                ` : '<div class="alert alert-info">Alternatif personel bulunmamaktadır.</div>'}
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Kapat</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Varsa önceki modalı kaldır
    $('#genetikDetayModal').remove();
    
    // Yeni modalı ekle ve göster
    $('body').append(detayHTML);
    const modal = new bootstrap.Modal(document.getElementById('genetikDetayModal'));
    modal.show();
};

// İş çizelgesi ana fonksiyonları
document.addEventListener('DOMContentLoaded', function() {
    // isListesi değişkenini JSON script etiketinden güvenle oku
    try {
        const isListesiElement = document.getElementById('is-listesi-json');
        if (isListesiElement && isListesiElement.textContent.trim()) {
            const parsedData = JSON.parse(isListesiElement.textContent);
            if (Array.isArray(parsedData)) {
                isListesi = parsedData;
            }
        }
    } catch (e) {
        console.error("isListesi JSON verisi okunurken hata:", e);
        // isListesi zaten boş bir dizi olarak başlatıldı.
    }

    initDashboard();
    showLastAssignmentDetails();
});

function initDashboard() {
    try {
        // Geciken iş sayısını hesapla
        const bugun = new Date();
        let gecikenIs = 0;

        // isListesi'nin tanımlı ve dizi olduğundan emin ol
        if (isListesi && Array.isArray(isListesi)) {
            gecikenIs = isListesi.filter(is => {
                if (
                    is &&
                    (is.durum === 'beklemede' || is.durum === 'devam_ediyor') &&
                    is.teslimat_tarihi
                ) {
                    const teslimatTarihi = new Date(is.teslimat_tarihi);
                    // Sadece gün karşılaştırması için saatleri sıfırla
                    teslimatTarihi.setHours(0,0,0,0);
                    const bugunCopy = new Date(bugun);
                    bugunCopy.setHours(0,0,0,0);
                    return teslimatTarihi < bugunCopy;
                }
                return false;
            }).length;
        }
        
        const gecikenElement = document.getElementById('gecikenIsSayisi');
        if (gecikenElement) {
            gecikenElement.textContent = gecikenIs;
        }
        
        // İşleri önceliğe göre sırala
        const tbody = document.querySelector('.table tbody');
        if (tbody) {
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            rows.sort((a, b) => {
                const oncelikBadgeA = a.querySelector('.oncelik-badge');
                const oncelikBadgeB = b.querySelector('.oncelik-badge');
                
                const oncelikA = oncelikBadgeA ? oncelikBadgeA.textContent.trim() : 'Normal';
                const oncelikB = oncelikBadgeB ? oncelikBadgeB.textContent.trim() : 'Normal';

                // 1. Önceliğe göre sırala (Kritik işler en üstte)
                if (oncelikA === 'Kritik' && oncelikB !== 'Kritik') return -1;
                if (oncelikA !== 'Kritik' && oncelikB === 'Kritik') return 1;

                // 2. Aynı önceliğe sahipse teslimat tarihine göre sırala (erken olan önce)
                const teslimatTarihiTextA = a.querySelector('td:nth-child(5)').textContent.trim();
                const teslimatTarihiTextB = b.querySelector('td:nth-child(5)').textContent.trim();

                const tarihA = new Date(teslimatTarihiTextA);
                const tarihB = new Date(teslimatTarihiTextB);

                // Geçersiz tarihleri sıralamanın sonuna at
                if (isNaN(tarihA.getTime())) return 1;
                if (isNaN(tarihB.getTime())) return -1;

                return tarihA - tarihB;
            });
            
            // Sıralanmış satırları tabloya yerleştir
            tbody.innerHTML = '';
            rows.forEach(row => tbody.appendChild(row));
            
            // Geciken işleri vurgula
            rows.forEach(function(row) {
                const teslimatTarihi = new Date(row.querySelector('td:nth-child(5)').textContent);
                if (teslimatTarihi < bugun) {
                    row.classList.add('table-danger');
                }
            });
        }
    } catch (error) {
        console.error('Dashboard başlatılırken hata:', error);
    }
}

// İş silme fonksiyonu
window.isSil = function(isId) {
    silinecekIsId = isId;
    const modal = new bootstrap.Modal(document.getElementById('isSilmeOnayModal'));
    modal.show();
};

// İş Değiştirme ve Kritik İş Atama İşlemleri
async function handleKritikIsAtama(yeniIs, enUygunPersonel) {
    try {
        const mevcutIs = isListesi.find(is => 
            is.atanan_calisan === enUygunPersonel.calisan && 
            is.durum === 'devam_ediyor'
        );

        if (!mevcutIs) {
            // Personel zaten müsaitse direkt ata
            await atamaYap(yeniIs, enUygunPersonel.calisan);
            showAlert('success', `${enUygunPersonel.calisan} başarıyla atandı.`);
            return;
        }

        // Kritik iş için onay modalı göster
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'kritikIsModal';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Kritik İş Atama Onayı</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>Önceliği kritik olan bir iş kaydedildi. Buna en uygun personeliniz <strong>${enUygunPersonel.calisan}</strong>'dir.</p>
                        <p>Şu an önceliği normal olan <strong>${mevcutIs.proje_adi}</strong> projesinde çalışmaktadır.</p>
                        <p>İş değişikliği yapmasını ve kritik önceliğe sahip olan bu işe başlamasını ister misiniz?</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Hayır</button>
                        <button type="button" class="btn btn-primary" id="kritikIsOnay">Evet</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();

        document.getElementById('kritikIsOnay').addEventListener('click', async () => {
            try {
                // Mevcut işi bırakma ve yeni işe atama
                await personelDegistir(mevcutIs, yeniIs, enUygunPersonel.calisan);
                modalInstance.hide();
                modal.remove();
                showAlert('success', `${enUygunPersonel.calisan} başarıyla yeni işe atandı.`);
            } catch (error) {
                modalInstance.hide();
                modal.remove();
                showAlert('danger', 'İş değişikliği sırasında bir hata oluştu: ' + error.message);
            }
        });

        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    } catch (error) {
        showAlert('danger', 'Kritik iş atama sırasında bir hata oluştu: ' + error.message);
    }
}

async function personelDegistir(eskiIs, yeniIs, personel) {
    try {
        // Alternatif personel bul
        const alternatifPersonel = await bulAlternatifPersonel(eskiIs.tasarim_kodu);
        
        if (!alternatifPersonel) {
            throw new Error('Uygun alternatif personel bulunamadı. Fason işçi talep edilmeli!');
        }

        // Eski işi alternatif personele devret
        await isDevret(eskiIs.tasarim_kodu, alternatifPersonel);

        // Yeni işe personeli ata
        await atamaYap(yeniIs, personel);

        return {
            success: true,
            message: `${personel} yeni işe atandı. ${alternatifPersonel} eski işi devraldı.`
        };
    } catch (error) {
        throw error;
    }
}

async function bulAlternatifPersonel(tasarimKodu) {
    try {
        const response = await fetch(`/api/alternatif-personel/${tasarimKodu}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message);
        }

        // Müsait alternatif personeli bul
        for (const alternatif of data.alternatifler) {
            const mevcutIs = isListesi.find(is => 
                is.atanan_calisan === alternatif.calisan && 
                is.durum === 'devam_ediyor'
            );
            
            if (!mevcutIs) {
                return alternatif.calisan;
            }
        }

        // Müsait personel bulunamadı
        return null;
    } catch (error) {
        console.error('Alternatif personel bulma hatası:', error);
        return null;
    }
}

async function isDevret(tasarimKodu, yeniPersonel) {
    try {
        const response = await fetch('/api/is-devret', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                tasarim_kodu: tasarimKodu,
                yeni_personel: yeniPersonel
            })
        });

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.message);
        }

        return data;
    } catch (error) {
        console.error('İş devretme hatası:', error);
        throw error;
    }
}

async function atamaYap(is, personel) {
    try {
        // Önce personelin müsaitlik durumunu kontrol et
        const mevcutIsler = isListesi.filter(item => 
            item.durum !== 'tamamlandi' && 
            (Array.isArray(item.atanan_calisan) ? 
                item.atanan_calisan.includes(personel) : 
                item.atanan_calisan === personel)
        );

        if (mevcutIsler.length > 0) {
            // Personel başka bir işte çalışıyor, alternatif personel bul
            const alternatifResponse = await fetch(`/api/alternatif-personel/${is.tasarim_kodu}`);
            const alternatifData = await alternatifResponse.json();

            if (!alternatifData.success) {
                throw new Error('Alternatif personel bulunamadı');
            }

            // Personel ihtiyacını kontrol et
            const personelIhtiyaci = alternatifData.personel_ihtiyaci;
            const eksikPersonel = alternatifData.eksik_personel;

            // Müsait alternatif personel var mı kontrol et
            const musaitPersonel = {};
            let fasonIsciGerekli = false;

            ['ustabasi', 'kalifiyeli', 'cirak'].forEach(seviye => {
                musaitPersonel[seviye] = alternatifData.onerilen_calisanlar[seviye]
                    .filter(calisan => !isListesi.some(is => 
                        is.durum !== 'tamamlandi' && 
                        (Array.isArray(is.atanan_calisan) ? 
                            is.atanan_calisan.includes(calisan.calisan) : 
                            is.atanan_calisan === calisan.calisan)
                    ))
                    .map(c => c.calisan);

                if (musaitPersonel[seviye].length < personelIhtiyaci[seviye]) {
                    fasonIsciGerekli = true;
                }
            });

            // Atanacak personel listesini oluştur
            const atanacakPersonel = {
                ustabasi: [],
                kalifiyeli: [],
                cirak: []
            };

            ['ustabasi', 'kalifiyeli', 'cirak'].forEach(seviye => {
                // Müsait personelleri ekle
                atanacakPersonel[seviye] = musaitPersonel[seviye].slice(0, personelIhtiyaci[seviye]);
                
                // Eksik kalan pozisyonlar için fason işçi ekle
                const eksikSayi = personelIhtiyaci[seviye] - atanacakPersonel[seviye].length;
                for (let i = 0; i < eksikSayi; i++) {
                    atanacakPersonel[seviye].push(`Fason İşçi (${seviye.charAt(0).toUpperCase() + seviye.slice(1)})`);
                }
            });

            // İş atamasını yap
            const response = await fetch('/api/is-atama', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tasarim_kodu: is.tasarim_kodu,
                    proje_adi: is.proje_adi,
                    teslimat_tarihi: is.teslimat_tarihi,
                    durum: 'devam_ediyor',
                    oncelik: is.oncelik,
                    atanan_calisan: atanacakPersonel,
                    kalan_sure: is.kalan_sure,
                    fason_isci_kullanimi: fasonIsciGerekli
                })
            });

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.message);
            }

            return data;
        } else {
            // Personel müsait, normal atama yap
            const response = await fetch('/api/is-atama', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tasarim_kodu: is.tasarim_kodu,
                    proje_adi: is.proje_adi,
                    teslimat_tarihi: is.teslimat_tarihi,
                    durum: 'devam_ediyor',
                    oncelik: is.oncelik,
                    atanan_calisan: personel,
                    kalan_sure: is.kalan_sure
                })
            });

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.message);
            }

            return data;
        }
    } catch (error) {
        throw error;
    }
}

// Atama detaylarını kaydetme fonksiyonu
async function saveAssignmentDetails(requestData, responseData, kontrolData = null) {
    try {
        const now = new Date();

        // kontrolData yoksa oluştur
        if (!kontrolData) {
            // Çalışanın mevcut işini kontrol et
            const mevcutIs = isListesi.find(is => 
                is.atanan_calisan === responseData.atanan_calisan && 
                is.durum !== 'tamamlandi'
            );
            
            // Alternatif personel önerisi al
            const alternatifResponse = await fetch(`/api/alternatif-personel/${requestData.tasarim_kodu}`);
            const alternatifData = await alternatifResponse.json();
            
            let alternatifler = [];
            if (alternatifData.success && alternatifData.alternatifler) {
                alternatifler = alternatifData.alternatifler;
            }
            
            kontrolData = {
                en_uygun_personel: {
                    calisan: responseData.atanan_calisan,
                    alternatifler: alternatifler
                },
                mevcut_is: mevcutIs
            };
        }

        // Tasarım kodu bilgilerini al
        const tasarimKoduBilgileri = await fetch(`/api/tasarim-kodu-bilgileri/${requestData.tasarim_kodu}`).then(r => r.json());
        const gerekliYetkinlikler = tasarimKoduBilgileri.gerekli_yetkinlikler || [];

        // Çalışan bilgilerini al
        const calisanBilgileri = await fetch(`/api/calisan-bilgileri/${responseData.atanan_calisan}`).then(r => r.json());
        const calisanYetkinlikleri = calisanBilgileri.yetkinlikler || [];

        // Yetkinlik uyumunu hesapla
        const yetkinlikUyumu = gerekliYetkinlikler.length > 0 ? 
            (gerekliYetkinlikler.filter(y => calisanYetkinlikleri.includes(y)).length / gerekliYetkinlikler.length) * 100 : 0;

        // Tecrübe puanını hesapla (0-20 yıl arası normalize edilmiş)
        const tecrubePuani = Math.min(calisanBilgileri.tecrube_yili / 20 * 100, 100);

        // Verimlilik puanını al
        const verimlilikPuani = calisanBilgileri.verimlilik_puani * 100;

        // Genetik algoritma uygunluk skorunu al
        const genetikSonuclari = await fetch('/api/genetik-sonuclari').then(r => r.json());
        const genetikUygunluk = genetikSonuclari[requestData.tasarim_kodu]?.uygunluk || 0;

        const assignmentDetails = {
            tarih: now.toLocaleString('tr-TR'),
            timestamp: now.getTime(),
            is_bilgileri: {
                tasarim_kodu: requestData.tasarim_kodu,
                proje_adi: requestData.proje_adi,
                oncelik: requestData.oncelik,
                teslimat_tarihi: requestData.teslimat_tarihi,
                tahmini_sure: requestData.kalan_sure
            },
            atanan_calisan: responseData.atanan_calisan,
            atama_detaylari: {
                yetkinlik_uyumu: yetkinlikUyumu,
                tecrube_puani: tecrubePuani,
                verimlilik_puani: verimlilikPuani,
                is_yuku_etkisi: calculateWorkloadEffect(responseData.atanan_calisan),
                genetik_uygunluk: genetikUygunluk,
                tecrube_aciklama: `${calisanBilgileri.tecrube_yili} yıllık tecrübe baz alınarak hesaplandı (20 yıl üzeri %100)`
            },
            uygunluk_skoru: genetikUygunluk,
            alternatif_calisanlar: kontrolData.en_uygun_personel.alternatifler,
            atama_nedeni: kontrolData.mevcut_is ? 
                `Personel ${kontrolData.mevcut_is.proje_adi} projesinde çalışıyor (${kontrolData.mevcut_is.oncelik} öncelikli)` : 
                'Personel müsait'
        };

        const response = await fetch('/api/atama-detayi-kaydet', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(assignmentDetails)
        });

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.message);
        }

        // Atama detaylarını göster
        showLastAssignmentDetails();
    } catch (error) {
        console.error('Atama detayı kaydetme hatası:', error);
    }
}

// İş yükü etkisini hesaplama
function calculateWorkloadEffect(calisan) {
    let aktifIsSayisi = 0;
    let kritikIsSayisi = 0;

    isListesi.forEach(is => {
        if (is.atanan_calisan === calisan && is.durum !== 'tamamlandi') {
            aktifIsSayisi++;
            if (is.oncelik === 'kritik') kritikIsSayisi++;
        }
    });

    return {
        aktif_is_sayisi: aktifIsSayisi,
        kritik_is_sayisi: kritikIsSayisi,
        is_yuku_yuzdesi: (aktifIsSayisi / 3) * 100 // Maksimum 3 iş varsayımı
    };
}

// İş kaydetme
$('#isKaydet').click(function() {
    const form = $('#yeniIsForm');
    if (!form[0].checkValidity()) {
        form[0].reportValidity();
        return;
    }
    
    const tasarimKodu = form.find('#tasarimKoduSelect').val();
    if (!tasarimKodu) {
        bildirimGoster('error', 'Lütfen bir tasarım kodu seçiniz');
        return;
    }
    
    // Form verilerini topla
    const formData = {
        kod: tasarimKodu,
        proje_adi: form.find('input[name="proje_adi"]').val(),
        teslimat_tarihi: form.find('input[name="teslimat_tarihi"]').val(),
        durum: form.find('select[name="durum"]').val(),
        oncelik: form.find('select[name="oncelik"]').val()
    };
    
    console.log('Gönderilen form verisi:', formData); // Debug için log
    
    // API isteği gönder
    $.ajax({
        url: '/api/is-kaydet',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                // Başarılı mesajı göster
                bildirimGoster('success', response.mesaj || 'İş başarıyla kaydedildi');
                
                // Modalı kapat
                $('#yeniIsModal').modal('hide');
                
                // Formu temizle
                $('#yeniIsForm')[0].reset();
                
                // Sayfayı yenile
                setTimeout(function() {
                    window.location.reload();
                }, 1500);
            } else if (response.personel_yetersiz) {
                // Personel yetersiz, onay modalını göster
                let mesaj = 'Yetersiz personel bulundu. ';
                let eksikler = [];
                if (response.eksik_personel.ustabasi > 0) eksikler.push(`${response.eksik_personel.ustabasi} ustabaşı`);
                if (response.eksik_personel.kalifiyeli > 0) eksikler.push(`${response.eksik_personel.kalifiyeli} kalifiyeli`);
                if (response.eksik_personel.cirak > 0) eksikler.push(`${response.eksik_personel.cirak} çırak`);
                
                mesaj += `Eksik pozisyonlar: ${eksikler.join(', ')}. `;
                mesaj += 'Bu pozisyonlar için taşeron işçi temin edilerek işin kaydedilmesini onaylıyor musunuz?';

                $('#taseronOnayMesaji').text(mesaj);
                // Orijinal form verilerini modala ekle
                $('#taseronOnayModal').data('formData', formData); 
                const taseronModal = new bootstrap.Modal($('#taseronOnayModal'));
                taseronModal.show();
                $('#yeniIsModal').modal('hide');

            } else {
                bildirimGoster('error', response.mesaj || 'İş kaydedilemedi');
            }
        },
        error: function(xhr, status, error) {
            console.error('Hata:', error, xhr.responseText);
            try {
                const response = JSON.parse(xhr.responseText);
                bildirimGoster('error', response.mesaj || 'İş kaydedilirken bir hata oluştu');
            } catch (e) {
                bildirimGoster('error', 'İş kaydedilirken bir hata oluştu: ' + error);
            }
        }
    });
});

$('#taseronOnaylaBtn').on('click', function() {
    const formData = $('#taseronOnayModal').data('formData');
    if (!formData) return;

    // Taşeron onayını ekle
    formData.taseron_onayi = true;

    $.ajax({
        url: '/api/is-kaydet',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                bildirimGoster('success', response.mesaj || 'İş, taşeron desteğiyle başarıyla kaydedildi.');
                setTimeout(() => location.reload(), 1500);
            } else {
                bildirimGoster('error', response.mesaj || 'Onaya rağmen iş kaydedilemedi.');
            }
        },
        error: function(xhr) {
            try {
                const response = JSON.parse(xhr.responseText);
                bildirimGoster('error', response.mesaj || 'İş kaydedilirken bir hata oluştu');
            } catch (e) {
                bildirimGoster('error', 'İş kaydedilirken bir sunucu hatası oluştu.');
            }
        },
        complete: function() {
            const modalInstance = bootstrap.Modal.getInstance($('#taseronOnayModal'));
            if (modalInstance) {
                modalInstance.hide();
            }
        }
    });
});

// Bildirim gösterme fonksiyonu
function bildirimGoster(tip, mesaj) {
    // Mevcut bildirimleri temizle
    $('.toast').remove();
    $('.alert').remove();
    
    // Mesaj kontrolü
    const mesajText = mesaj && mesaj.trim() ? mesaj : (
        tip === 'success' ? 'İşlem başarıyla tamamlandı' :
        tip === 'error' ? 'Bir hata oluştu' :
        'Bildirim'
    );
    
    // Bootstrap toast bildirimi oluştur
    const bildirimHTML = `
        <div class="toast align-items-center text-white border-0 position-fixed top-0 end-0 m-3 bg-${tip}" 
             role="alert" aria-live="assertive" aria-atomic="true" style="z-index: 9999;">
            <div class="d-flex">
                <div class="toast-body">
                    ${mesajText}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    // Bildirimi ekle ve göster
    $('body').append(bildirimHTML);
    const toast = new bootstrap.Toast($('.toast').last(), {
        delay: 3000,
        animation: true
    });
    toast.show();
}

// showAlert fonksiyonunu bildirimGoster'a yönlendir
function showAlert(type, message) {
    bildirimGoster(type, message);
}

// Atama detayları işlemleri
function showLastAssignmentDetails() {
    $.ajax({
        url: '/api/son-atama-detayi',
        method: 'GET',
        success: function(response) {
            if (response.success && response.data) {
                $('#atamaDetaylari').show();
                $('#atananIs').text(`${response.data.is_bilgileri.tasarim_kodu} - ${response.data.is_bilgileri.urun_adi}`);
                $('#atananPersonel').text(response.data.atanan_calisan);
                
                // Atama kriterleri
                $('#yetkinlikUyumu').html(`${response.data.atama_detaylari.yetkinlik_uyumu.toFixed(1)}%`);
                $('#tecrubePuani').html(`${response.data.atama_detaylari.tecrube_puani.toFixed(1)}% <i class="bi bi-info-circle" data-bs-toggle="tooltip" title="${response.data.atama_detaylari.tecrube_aciklama}"></i>`);
                $('#verimlilikPuani').text(`${response.data.atama_detaylari.verimlilik_puani.toFixed(1)}%`);
                $('#toplamUygunluk').text(`${response.data.atama_detaylari.genetik_uygunluk.toFixed(1)}%`);

                // Tooltipleri aktifleştir
                $('[data-bs-toggle="tooltip"]').tooltip();

                // Alternatif personeller
                let alternatifHTML = '';
                if (response.data.alternatif_calisanlar && response.data.alternatif_calisanlar.length > 0) {
                    alternatifHTML = '<ul class="list-group">';
                    response.data.alternatif_calisanlar.forEach((alt, index) => {
                        alternatifHTML += `
                            <li class="list-group-item d-flex justify-content-between align-items-center">
                                ${index + 1}. ${alt.calisan}
                                <span class="badge bg-primary rounded-pill">${alt.uygunluk.toFixed(1)}%</span>
                            </li>`;
                    });
                    alternatifHTML += '</ul>';
                } else {
                    alternatifHTML = '<p class="text-muted">Alternatif personel bulunmamaktadır.</p>';
                }
                $('#alternatifPersoneller').html(alternatifHTML);
            } else {
                $('#atamaDetaylari').hide();
            }
        },
        error: function(xhr, status, error) {
            console.error('Son atama detayı hatası:', error);
            $('#atamaDetaylari').hide();
        }
    });
}

// Tüm atama detayları modal
$('#tumAtamaDetaylariModal').on('show.bs.modal', function() {
    $.get('/api/tum-atama-detaylari', function(response) {
        if (response.success) {
            const html = response.data.map(atama => `
                <tr>
                    <td>${atama.tarih}</td>
                    <td>${atama.is_bilgileri.tasarim_kodu}</td>
                    <td>${atama.is_bilgileri.proje_adi}</td>
                    <td>${atama.atanan_calisan}</td>
                    <td>${atama.uygunluk_skoru.toFixed(1)}%</td>
                    <td>
                        ${atama.alternatif_calisanlar ? atama.alternatif_calisanlar.map(alt => 
                            `<div>${alt.calisan} (${alt.uygunluk.toFixed(1)}%)</div>`
                        ).join('') : 'Alternatif yok'}
                    </td>
                </tr>
            `).join('');
            $('#tumAtamaDetaylariTablo').html(html);
        }
    });
});

// Tasarım kodu seçildiğinde süreyi otomatik doldur
document.addEventListener('DOMContentLoaded', function() {
    const selectEl = document.getElementById('tasarimKoduSelect');
    
    if(selectEl){
        // Süre ile ilgili kodlar kaldırıldı çünkü artık kalanSureInput elementi yok
        
        // Diğer event listener'lar ve işlemler buraya eklenebilir
    }
}); 

// Monte Carlo simülasyonu için
$(document).ready(function() {
    // Sayfa yüklendiğinde Monte Carlo sonuçlarını al
    getMonteCarloCurrent();
    
    // Her 60 saniyede bir güncelle
    setInterval(getMonteCarloCurrent, 60000);
    
    // Simülasyon başlatma butonu için event listener
    $('#simulasyonBaslat').click(function() {
        var btn = $(this);
        btn.prop('disabled', true);
        btn.html('<span class="spinner-border spinner-border-sm"></span> Simülasyon çalışıyor...');
        
        $.ajax({
            url: '/performans-simulasyonu/',
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            success: function(response) {
                if (response.success) {
                    // Bunun yerine kartı güncelleyelim, eğer HTML'de updateMonteCarloCard varsa
                    if (typeof updateMonteCarloCard === 'function') {
                        updateMonteCarloCard(response.monte_carlo_sonuclari);
                    } else {
                        // Alternatif olarak sadece konsola yazdırabilir veya başka bir işlem yapabilirsiniz.
                        console.log("Monte Carlo sonuçları alındı, ancak updateMonteCarloCard fonksiyonu bulunamadı.", response.monte_carlo_sonuclari);
                    }
                } else {
                    bildirimGoster('error', response.mesaj || 'Simülasyon sırasında bir hata oluştu');
                }
            },
            error: function() {
                bildirimGoster('error', 'Simülasyon sırasında bir hata oluştu');
            },
            complete: function() {
                btn.prop('disabled', false);
                btn.html('<i class="bi bi-play-circle"></i> Simülasyonu Başlat');
            }
        });
    });

    // Genetik Optimizasyon için
    $('#genetikOptimizasyonBaslat').click(function() {
        var btn = $(this);
        btn.prop('disabled', true);
        btn.html('<span class="spinner-border spinner-border-sm"></span> Optimizasyon çalışıyor...');
        
        $.ajax({
            url: '/api/genetik-optimizasyon',
            method: 'POST',
            success: function(response) {
                if (response.success) {
                    // Bunun yerine kartı güncelleyelim, eğer HTML'de updateMonteCarloCard varsa
                    if (typeof updateMonteCarloCard === 'function') {
                        updateMonteCarloCard(response.monte_carlo_sonuclari);
                    } else {
                        // Alternatif olarak sadece konsola yazdırabilir veya başka bir işlem yapabilirsiniz.
                        console.log("Monte Carlo sonuçları alındı, ancak updateMonteCarloCard fonksiyonu bulunamadı.", response.monte_carlo_sonuclari);
                    }
                } else {
                    bildirimGoster('error', response.mesaj || 'Genetik optimizasyon sırasında bir hata oluştu');
                }
            },
            error: function() {
                bildirimGoster('error', 'Genetik optimizasyon sırasında bir hata oluştu');
            },
            complete: function() {
                btn.prop('disabled', false);
                btn.html('Genetik Optimizasyonu Başlat');
            }
        });
    });

    // Taguchi Optimizasyon için
    $('#taguchiOptimizasyonBaslat').click(function() {
        var btn = $(this);
        btn.prop('disabled', true);
        btn.html('<span class="spinner-border spinner-border-sm"></span> Optimizasyon çalışıyor...');
        
        $.ajax({
            url: '/api/taguchi-optimizasyon',
            method: 'POST',
            success: function(response) {
                if (response.success) {
                    // Bunun yerine kartı güncelleyelim, eğer HTML'de updateMonteCarloCard varsa
                    if (typeof updateMonteCarloCard === 'function') {
                        updateMonteCarloCard(response.monte_carlo_sonuclari);
                    } else {
                        // Alternatif olarak sadece konsola yazdırabilir veya başka bir işlem yapabilirsiniz.
                        console.log("Monte Carlo sonuçları alındı, ancak updateMonteCarloCard fonksiyonu bulunamadı.", response.monte_carlo_sonuclari);
                    }
                } else {
                    bildirimGoster('error', response.mesaj || 'Taguchi optimizasyonu sırasında bir hata oluştu');
                }
            },
            error: function() {
                bildirimGoster('error', 'Taguchi optimizasyonu sırasında bir hata oluştu');
            },
            complete: function() {
                btn.prop('disabled', false);
                btn.html('Taguchi Optimizasyonu Başlat');
            }
        });
    });

    // YENİ BAŞLAT/DURDUR BUTONU İŞLEYİCİSİ
    $(document).on('click', '.startStopBtn', function() {
        const btn = $(this);
        const isId = btn.data('id');
        const currentStatus = btn.data('durum');

        if (!isId) {
            console.error('Butonda iş ID (data-id) bulunamadı.');
            bildirimGoster('error', 'İşlem gerçekleştirilemedi, ID eksik.');
            return;
        }

        const newStatus = (currentStatus === 'devam_ediyor') ? 'beklemede' : 'devam_ediyor';
        const originalText = btn.text();
        
        // Öncelik bilgisini satırdan al
        const oncelik = btn.closest('tr').find('.oncelik-badge').text().trim().toLowerCase();

        btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>');

        $.ajax({
            url: `/api/is-guncelle/`,
            method: 'POST',
            headers: {'X-CSRFToken': getCookie('csrftoken')},
            contentType: 'application/json',
            data: JSON.stringify({
                'is_id': isId,
                'durum': newStatus,
                'oncelik': oncelik // oncelik bilgisini de gönder
            }),
            success: function(response) {
                if(response.success) {
                    const isNowInProgress = (newStatus === 'devam_ediyor');
                    
                    btn.text(isNowInProgress ? 'Durdur' : 'Başlat');
                    btn.data('durum', newStatus);
                    
                    if (isNowInProgress) {
                        btn.removeClass('btn-primary').addClass('btn-danger');
                    } else {
                        btn.removeClass('btn-danger').addClass('btn-primary');
                    }

                    const row = btn.closest('tr');
                    const statusBadge = row.find('td:nth-child(7) .badge');
                    
                    const statusText = isNowInProgress ? 'Devam Ediyor' : 'Beklemede';
                    const badgeClass = isNowInProgress ? 'bg-warning' : 'bg-secondary';
                    
                    statusBadge.text(statusText).removeClass('bg-warning bg-secondary bg-success').addClass(badgeClass);
                    bildirimGoster('success', `İş durumu başarıyla '${statusText}' olarak güncellendi.`);
                    
                } else {
                    bildirimGoster('error', response.mesaj || 'Durum güncellenirken bir hata oluştu.');
                    btn.text(originalText);
                }
            },
            error: function() {
                bildirimGoster('error', 'Sunucuyla iletişim kurulamadı.');
                btn.text(originalText);
            },
            complete: function() {
                btn.prop('disabled', false);
            }
        });
    });
});

function getMonteCarloCurrent() {
    $.ajax({
        url: '/performans-simulasyonu/',
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        success: function(response) {
            if (response.success && response.monte_carlo_sonuclari) {
                // Bunun yerine kartı güncelleyelim, eğer HTML'de updateMonteCarloCard varsa
                if (typeof updateMonteCarloCard === 'function') {
                    updateMonteCarloCard(response.monte_carlo_sonuclari);
                } else {
                    // Alternatif olarak sadece konsola yazdırabilir veya başka bir işlem yapabilirsiniz.
                    console.log("Monte Carlo sonuçları alındı, ancak updateMonteCarloCard fonksiyonu bulunamadı.", response.monte_carlo_sonuclari);
                }
            }
        },
        error: function(xhr, status, error) {
            console.error('Monte Carlo sonuçları alınırken hata:', error);
        }
    });
}

function updateMonteCarloCard(data) {
    try {
        console.log('updateMonteCarloCard çağrıldı, data:', data);

        let results = null;
        if (data && typeof data === 'object') {
            if ('monte_carlo_sonuclari' in data && data.monte_carlo_sonuclari) {
                results = data.monte_carlo_sonuclari;
            } else if (Object.keys(data).length > 0) {
                results = data;
            }
        }

        if (!results || typeof results !== 'object' || Object.keys(results).length === 0) {
            console.log('Gelen Monte Carlo verisi boş veya geçersiz, güncelleme atlanıyor.');
            return;
        }

        let cardsHtml = '';
        let hasEmployeeData = false;

        Object.entries(results).forEach(([calisan, sonuc]) => {
            // Daha esnek filtre: Alt çizgi içeren veya boşluk içermeyen anahtarları atla.
            // Bu, "Ad Soyad" formatındaki tüm çalışanları yakalar ve "genel_istatistikler" gibi sistem anahtarlarını dışlar.
            if (calisan.includes('_') || !calisan.includes(' ')) {
                console.log(`'${calisan}' anahtarı bir çalışan olarak değerlendirilmedi ve atlandı.`);
                return;
            }
            
            hasEmployeeData = true;

            if (!sonuc || typeof sonuc !== 'object') return;
            
            const ort = ((sonuc.ortalama_performans || 0) * 100).toFixed(1);
            const risk = ((sonuc.risk_skoru || 0) * 100).toFixed(1);
            const gecikme = ((sonuc.gecikme_olasiligi || 0) * 100).toFixed(1);
            const kararlilik = ((sonuc.performans_kararliligi || 0) * 100).toFixed(1);

            const performansBadgeClass = sonuc.ortalama_performans >= 0.7 ? 'bg-success' : sonuc.ortalama_performans >= 0.5 ? 'bg-warning' : 'bg-danger';
            const riskBadgeClass = sonuc.risk_skoru <= 0.3 ? 'bg-success' : sonuc.risk_skoru <= 0.6 ? 'bg-warning' : 'bg-danger';
            const gecikmeBadgeClass = sonuc.gecikme_olasiligi <= 0.3 ? 'bg-success' : sonuc.gecikme_olasiligi <= 0.6 ? 'bg-warning' : 'bg-danger';

            let tasarimBazliHtml = `
                <div class="alert alert-info mt-3">
                    Tasarım bazlı performans verisi bulunmamaktadır.
                </div>`;

            if (sonuc.tasarim_bazli_performans && sonuc.tasarim_bazli_performans.length > 0) {
                // Tekilleştirme: Aynı tasarım kodundan birden fazla varsa sadece ilkini göster
                const tekilTasarimlar = [];
                const gorulenKodlar = new Set();
                sonuc.tasarim_bazli_performans.forEach(tasarim => {
                    if (!gorulenKodlar.has(tasarim.tasarim_kodu)) {
                        tekilTasarimlar.push(tasarim);
                        gorulenKodlar.add(tasarim.tasarim_kodu);
                    }
                });
                tasarimBazliHtml = `
                    <div class="mt-3">
                        <h6 class="border-bottom pb-2">Tasarım Bazlı Performans</h6>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Tasarım</th>
                                        <th>Performans</th>
                                        <th>Risk</th>
                                        <th>Gecikme</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${tekilTasarimlar.map(tasarim => `
                                        <tr>
                                            <td>${tasarim.tasarim_kodu || 'N/A'}</td>
                                            <td>%${((tasarim.performans_ort || 0) * 100).toFixed(1)}</td>
                                            <td>%${((tasarim.risk || 0) * 100).toFixed(1)}</td>
                                            <td>%${((tasarim.gecikme || 0) * 100).toFixed(1)}</td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>`;
            }

            cardsHtml += `
                <div class="col-md-4 mb-3">
                    <div class="card h-100">
                        <div class="card-header">
                            <h6 class="mb-0 d-flex justify-content-between align-items-center">
                                ${calisan}
                                <span class="badge ${performansBadgeClass}">
                                    %${ort}
                                </span>
                            </h6>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <div class="d-flex justify-content-between mb-2">
                                    <span>Risk Skoru:</span>
                                    <span class="badge ${riskBadgeClass}">
                                        %${risk}
                                    </span>
                                </div>
                                <div class="d-flex justify-content-between mb-2">
                                    <span>Gecikme Olasılığı:</span>
                                    <span class="badge ${gecikmeBadgeClass}">
                                        %${gecikme}
                                    </span>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <span>Performans Kararlılığı:</span>
                                    <span class="badge bg-info">%${kararlilik}</span>
                                </div>
                            </div>
                            ${tasarimBazliHtml}
                        </div>
                    </div>
                </div>`;
        });

        if (hasEmployeeData) {
            const sonuclarContainer = $('#monteCarloSonuclari');
            if (sonuclarContainer.length) {
                sonuclarContainer.html(cardsHtml);
            } else {
                console.error('#monteCarloSonuclari elementi bulunamadı. Güncelleme yapılamıyor.');
            }
        } else {
            console.log('Filtreleme sonrası gösterilecek çalışan verisi bulunamadı, arayüz güncellenmedi.');
        }
        
    } catch (err) {
        console.error('Monte Carlo kartları güncellenirken hata oluştu:', err);
        if (typeof bildirimGoster === 'function') {
            bildirimGoster('error', 'Monte Carlo kartları güncellenirken bir hata oluştu.');
        }
    }
}

// Personelin mevcut durumunu kontrol et
function getPersonelDurum(calisan) {
    // Fason işçiler her zaman müsait
    if (calisan.startsWith('Fason İşçi')) {
        return 'Müsait';
    }
    
    // Çalışanın mevcut işlerini kontrol et
    const mevcutIsler = isListesi.filter(is => 
        (Array.isArray(is.atanan_calisan) ? 
            is.atanan_calisan.includes(calisan) : 
            is.atanan_calisan === calisan) && 
        is.durum !== 'tamamlandi'
    );
    
    if (mevcutIsler.length === 0) {
        return 'Müsait';
    } else {
        const kritikIsSayisi = mevcutIsler.filter(is => is.oncelik === 'kritik').length;
        if (kritikIsSayisi > 0) {
            return `Meşgul (${kritikIsSayisi} kritik iş)`;
        } else {
            return `Meşgul (${mevcutIsler.length} iş)`;
        }
    }
}

// Optimizasyon sonuçlarını göster
document.addEventListener('DOMContentLoaded', function() {
    // Son atama detaylarını göster
    showLastAssignmentDetails();
});

// Taguchi sonuçlarını göster
function gosterTaguchiSonuclari(taguchi_sonuclari) {
    let sonucHTML = '<ul>';
    taguchi_sonuclari.forEach(sonuc => {
        sonucHTML += `<li>${sonuc.tasarim_kodu}: ${sonuc.optimum_sure}</li>`;
    });
    sonucHTML += '</ul>';
    $('#taguchiSonuclari').html(sonucHTML);
}

// Sayfa yüklendiğinde son Taguchi sonuçlarını getir
function getSonTaguchiSonuclari() {
    $.ajax({
        url: '/api/son-taguchi-sonuclari',
        method: 'GET',
        success: function(data) {
            if (data && data.best_parameters) {
                gosterTaguchiSonuclari(data);
            }
        },
        error: function(xhr, status, error) {
            console.error('Taguchi sonuçları alınırken hata oluştu:', error);
        }
    });
}

// CSRF token için yardımcı fonksiyon
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 1. Performans değerlendirme sonrası otomatik güncelleme kaldırılıyor
$('#degerlendirmeKaydet').on('click', function() {
    const form = $('#performansDegerlendirmeForm');
    const isId = form.find('#degerlendirmeIsId').val();
    let degerlendirmeler = [];

    $('#calisanDegerlendirmeleri .card').each(function() {
        const card = $(this);
        const calisanId = card.find('input[type="hidden"]').val();
        const puan = card.find('select').val();

        if (puan) {
            degerlendirmeler.push({
                calisan_id: calisanId,
                puan: puan
            });
        }
    });

    const payload = {
        is_id: isId,
        degerlendirmeler: degerlendirmeler,
        notlar: form.find('textarea[name="notlar"]').val()
    };

    $.ajax({
        url: '/api/performans-degerlendirme-kaydet/',
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken')},
        contentType: 'application/json',
        data: JSON.stringify(payload),
        success: function(response) {
            if (response.success) {
                $('#performansDegerlendirmeModal').modal('hide');
                bildirimGoster('success', 'Değerlendirme başarıyla kaydedildi! Sonuçlar simülasyon çalıştıktan sonra güncellenecektir.');
                // Otomatik sayfa yenileme veya kart güncelleme yapılmıyor!
            } else {
                alert('Değerlendirme kaydedilirken bir hata oluştu: ' + response.message);
            }
        },
        error: function(xhr) {
            let errorMessage = 'Sunucuyla iletişim kurulamadı.';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMessage = 'Bir hata oluştu: ' + xhr.responseJSON.message;
                if (xhr.responseJSON.trace) {
                    console.error("Sunucu Hatası:", xhr.responseJSON.trace);
                }
            } else if (xhr.responseText) {
                console.error("Sunucu Yanıtı:", xhr.responseText);
                errorMessage = 'Sunucudan beklenmeyen bir yanıt alındı. Detaylar için tarayıcı konsolunu (F12) kontrol edin.';
            }
            alert(errorMessage);
        }
    });
});

// 2. updateTimestamp fonksiyonu ve Son Güncelleme saati sadece WebSocket ile güncellenecek
// WebSocket mesajı geldiğinde updateTimestamp çağrılacak, sayfa yenilemede çağrılmayacak
// (Bunu is_cizelgesi.html'de de kontrol et, initAllTimestamps fonksiyonunu kaldır veya sadece ilk yüklemede göster)
// ... mevcut kod ... 

$('#isSilmeOnayla').on('click', function() {
    if (!silinecekIsId) return;

    // CSRF token'ını al
    const csrftoken = getCookie('csrftoken');

    fetch('/api/is-sil', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            is_id: silinecekIsId
        })
    })
    .then(response => response.json())
    .then(data => {
        const modalEl = document.getElementById('isSilmeOnayModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) {
            modal.hide();
        }

        if (data.success) {
            bildirimGoster('success', 'İş başarıyla silindi.');
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            bildirimGoster('error', 'İş silinirken bir hata oluştu: ' + (data.message || ''));
        }
        silinecekIsId = null;
    })
    .catch(error => {
        console.error('Hata:', error);
        const modalEl = document.getElementById('isSilmeOnayModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) {
            modal.hide();
        }
        bildirimGoster('error', 'İş silinirken bir sunucu hatası oluştu.');
        silinecekIsId = null;
    });
}); 

function updateTaguchiCard(data) {
    try {
        console.log('updateTaguchiCard çağrıldı, data:', data);

        const taguchiCard = $('#taguchi-card');
        const cardBody = taguchiCard.find('.card-body');

        if (!data || !data.taguchi_sonuclari || data.taguchi_sonuclari.length === 0) {
            cardBody.html(`
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Henüz Taguchi optimizasyon sonucu bulunmamaktadır.
                </div>
            `);
            return;
        }
        
        const sonuclar = data.taguchi_sonuclari;
        const istatistikler = data.istatistikler;

        let tableRows = '';
        sonuclar.forEach(sonuc => {
            const iyilestirme_orani = parseFloat(sonuc.iyilestirme_orani || 0);
            let badgeClass = 'bg-warning';
            if (iyilestirme_orani > 10) {
                badgeClass = 'bg-success';
            } else if (iyilestirme_orani > 5) {
                badgeClass = 'bg-info';
            }

            const guncellenme_tarihi = new Date(sonuc.guncellenme_tarihi).toLocaleString('tr-TR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            tableRows += `
                <tr>
                    <td>${sonuc.tasarim_kodu}</td>
                    <td>${(sonuc.optimum_sure || 0).toFixed(1)}</td>
                    <td>
                        <span class="badge ${badgeClass}">
                            %${iyilestirme_orani.toFixed(1)}
                        </span>
                    </td>
                    <td>${sonuc.departman}</td>
                    <td>${guncellenme_tarihi}</td>
                </tr>
            `;
        });

        const cardBodyHtml = `
            <div class="row mb-3">
                <div class="col-md-6">
                    <div class="alert alert-success">
                        <h6 class="mb-2">Optimizasyon Özeti</h6>
                        <p class="mb-0">Ortalama İyileştirme: <strong>%${(istatistikler.ortalama_iyilestirme || 0).toFixed(1)}</strong></p>
                    </div>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Tasarım Kodu</th>
                            <th>Optimum Süre (dk)</th>
                            <th>İyileştirme</th>
                            <th>Departman</th>
                            <th>Son Güncelleme</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${tableRows}
                    </tbody>
                </table>
            </div>
        `;
        
        cardBody.html(cardBodyHtml);

    } catch (err) {
        console.error('Taguchi kartı güncellenirken hata oluştu:', err);
        if (typeof bildirimGoster === 'function') {
            bildirimGoster('error', 'Taguchi kartı güncellenirken bir hata oluştu.');
        }
    }
} 