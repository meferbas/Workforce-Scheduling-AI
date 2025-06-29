// Global değişken tanımlaması
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
    // İş listesini yükle
    const isListesiData = document.getElementById('isListesiData');
    if (isListesiData && isListesiData.value) {
        try {
            isListesi = JSON.parse(isListesiData.value);
            console.log('İş listesi yüklendi:', isListesi);
        } catch (error) {
            console.error('İş listesi yüklenirken hata:', error);
            isListesi = [];
        }
    }

    initDashboard();
    initTimers();
    showLastAssignmentDetails();
});

function initDashboard() {
    try {
        // Geciken iş sayısını hesapla
        const bugun = new Date();
        let gecikenIs = 0;

        // isListesi'nin tanımlı ve dizi olduğundan emin ol
        if (window.isListesi && Array.isArray(window.isListesi)) {
            gecikenIs = window.isListesi.filter(is => {
                if (is && is.durum !== 'tamamlandi' && is.teslimat_tarihi) {
                    const teslimatTarihi = new Date(is.teslimat_tarihi);
                    return teslimatTarihi < bugun;
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
                
                const oncelikA = oncelikBadgeA ? oncelikBadgeA.textContent.trim() : '';
                const oncelikB = oncelikBadgeB ? oncelikBadgeB.textContent.trim() : '';
                
                if (oncelikA === 'Kritik' && oncelikB !== 'Kritik') return -1;
                if (oncelikA !== 'Kritik' && oncelikB === 'Kritik') return 1;
                return 0;
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

function initTimers() {
    let jobTimers = {};

    // Mevcut tablo satırlarını oku
    document.querySelectorAll('tr[data-tasarim-kodu]').forEach(row => {
        const kod = row.getAttribute('data-tasarim-kodu');
        const kalanSureEl = row.querySelector('.kalanSureText');
        let initial = 0;
        if(kalanSureEl){
            initial = parseInt(kalanSureEl.textContent.trim()) || 0;
        }
        jobTimers[kod] = {
            remaining: initial * 60,
            running: false,
            intervalId: null
        };
    });

    // Start/Stop butonları
    document.querySelectorAll('.startStopBtn').forEach(btn => {
        btn.addEventListener('click', () => {
            const kod = btn.getAttribute('data-kod');
            let timerData = jobTimers[kod];
            if(!timerData.running){
                startTimer(kod, btn, timerData);
            } else {
                stopTimer(kod, btn, timerData);
            }
        });
    });
}

function startTimer(kod, btn, timerData) {
    btn.textContent = 'Durdur';
    timerData.running = true;
    let saveCounter = 0;

    updateIsDurumu(kod, "devam_ediyor");

    timerData.intervalId = setInterval(() => {
        if(timerData.remaining > 0){
            timerData.remaining--;
            let hours = Math.floor(timerData.remaining / 3600);
            let minutes = Math.floor((timerData.remaining % 3600) / 60);
            let formattedTime = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;

            updateKalanSure(kod, formattedTime);

            saveCounter++;
            if(saveCounter % 60 === 0){
                saveRemainingTime(kod, timerData.remaining);
            }
        } else {
            clearInterval(timerData.intervalId);
            timerData.running = false;
            btn.textContent = 'Başlat';
            updateKalanSure(kod, "00:00");
            updateIsDurumu(kod, "tamamlandi");
        }
    }, 1000);
}

function stopTimer(kod, btn, timerData) {
    btn.textContent = 'Başlat';
    timerData.running = false;
    clearInterval(timerData.intervalId);
    timerData.intervalId = null;
    
    // İşi beklemeye al
    updateIsDurumu(kod, "beklemede");
}

function saveRemainingTime(kod, remaining) {
    try {
        const minutes = Math.ceil(remaining / 60);
        fetch('/api/update-kalan-sure', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tasarim_kodu: kod,
                kalan_sure: minutes
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Kalan süre kaydedilemedi:', data.message);
            }
        })
        .catch(error => console.error('Kalan süre kaydedilirken hata:', error));
    } catch (error) {
        console.error('Kalan süre kaydedilirken hata:', error);
    }
}

function updateKalanSure(kod, val){
    const row = document.querySelector(`tr[data-tasarim-kodu="${kod}"]`);
    if(!row) return;
    const span = row.querySelector('.kalanSureText');
    if(span){
        span.textContent = val;
    }
}

function updateIsDurumu(kod, yeniDurum, yeniOncelik) {
    const isItem = document.querySelector(`tr[data-tasarim-kodu="${kod}"]`);
    if (!isItem) return;

    // Durum badge'ini güncelle
    const durumBadge = isItem.querySelector('td:nth-child(7) .badge');
    if (durumBadge) {
        let durumText = '';
        let badgeClass = '';
        
        switch(yeniDurum) {
            case 'beklemede':
                durumText = 'Beklemede';
                badgeClass = 'bg-secondary';
                break;
            case 'devam_ediyor':
                durumText = 'Devam Ediyor';
                badgeClass = 'bg-warning';
                break;
            case 'tamamlandi':
                durumText = 'Tamamlandı';
                badgeClass = 'bg-success';
                break;
            default:
                return;
        }
        
        durumBadge.textContent = durumText;
        durumBadge.className = `badge ${badgeClass}`;
    }

    // Öncelik badge'ini güncelle
    if (yeniOncelik) {
        const oncelikBadge = isItem.querySelector('td:nth-child(6) .oncelik-badge');
        if (oncelikBadge) {
            const oncelikText = yeniOncelik.charAt(0).toUpperCase() + yeniOncelik.slice(1);
            oncelikBadge.textContent = oncelikText;
            oncelikBadge.className = `badge oncelik-badge ${yeniOncelik === 'kritik' ? 'bg-danger' : 'bg-info'}`;
        }
    }

    // Eğer iş tamamlandıysa ve tabloda görünmemesi gerekiyorsa satırı gizle
    if (yeniDurum === 'tamamlandi') {
        isItem.style.display = 'none';
    }
}

function updateIsStatus(kod, durum, tamamlanmaYuzdesi) {
    fetch('/api/is-durum-guncelle', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            tasarim_kodu: kod,
            durum: durum,
            tamamlanma_yuzdesi: tamamlanmaYuzdesi
        })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            console.error('İş durumu güncellenemedi:', data.message);
        }
    })
    .catch(error => console.error('İş durumu güncellenirken hata:', error));
}

// İş güncelleme fonksiyonu
window.isGuncelle = function(tasarimKodu) {
    const isItem = document.querySelector(`tr[data-tasarim-kodu="${tasarimKodu}"]`);
    if (!isItem) {
        bildirimGoster('error', 'İş bulunamadı');
        return;
    }

    const modal = new bootstrap.Modal(document.getElementById('isGuncellemeModal'));
    const form = document.getElementById('isGuncellemeForm');

    // Form alanlarını doldur
    form.querySelector('[name="tasarim_kodu"]').value = tasarimKodu;
    form.querySelector('[name="is_id"]').value = isItem.querySelector('td:first-child').textContent;

    // Mevcut durum ve öncelik değerlerini al
    const durumBadge = isItem.querySelector('td:nth-child(7) .badge');
    const oncelikBadge = isItem.querySelector('td:nth-child(6) .oncelik-badge');

    const durumSelect = form.querySelector('[name="durum"]');
    const oncelikSelect = form.querySelector('[name="oncelik"]');

    // Mevcut durumu seç
    if (durumBadge) {
        const durumText = durumBadge.textContent.trim().toLowerCase();
        switch(durumText) {
            case 'beklemede':
                durumSelect.value = 'beklemede';
                break;
            case 'devam ediyor':
                durumSelect.value = 'devam_ediyor';
                break;
            case 'tamamlandı':
                durumSelect.value = 'tamamlandi';
                break;
        }
    }

    // Mevcut önceliği seç
    if (oncelikBadge) {
        oncelikSelect.value = oncelikBadge.textContent.trim().toLowerCase();
    }

    // Durum değişikliğini izle
    durumSelect.onchange = function() {
        if (this.value === 'tamamlandi') {
            oncelikSelect.closest('.mb-3').style.display = 'none';
        } else {
            oncelikSelect.closest('.mb-3').style.display = 'block';
        }
    };

    modal.show();
}

// İş güncelleme kaydet butonuna tıklandığında
document.addEventListener('DOMContentLoaded', function() {
    const kaydetBtn = document.getElementById('isGuncellemeKaydet');
    if (kaydetBtn) {
        kaydetBtn.addEventListener('click', function() {
            const form = document.getElementById('isGuncellemeForm');
            const tasarimKodu = form.querySelector('[name="tasarim_kodu"]').value;
            const isId = form.querySelector('[name="is_id"]').value;
            const durum = form.querySelector('[name="durum"]').value;
            const oncelik = form.querySelector('[name="oncelik"]').value;
            
            if (!isId) {
                bildirimGoster('error', 'İş ID bulunamadı');
                return;
            }
            
            if (durum === 'tamamlandi') {
                // Modal'ı kapat ve performans değerlendirmesini göster
                bootstrap.Modal.getInstance(document.getElementById('isGuncellemeModal')).hide();
                performansDegerlendirmesiGoster(tasarimKodu, isId);
            } else {
                // Normal güncelleme işlemi
                $.ajax({
                    url: '/api/is-guncelle',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        is_id: isId,
                        tasarim_kodu: tasarimKodu,
                        durum: durum,
                        oncelik: oncelik
                    }),
                    success: function(response) {
                        if (response.success) {
                            // Önce UI'ı güncelle
                            window.updateIsDurumu(tasarimKodu, durum, oncelik);
                            
                            // Sonra modalı kapat
                            const modal = bootstrap.Modal.getInstance(document.getElementById('isGuncellemeModal'));
                            if (modal) {
                                modal.hide();
                            }
                            
                            // En son bildirim göster
                            bildirimGoster('success', 'İş durumu güncellendi');
                        } else {
                            bildirimGoster('error', response.mesaj || 'İş güncellenemedi');
                        }
                    },
                    error: function(xhr) {
                        try {
                            const response = xhr.responseJSON || {};
                            bildirimGoster('error', response.mesaj || 'İş güncellenirken bir hata oluştu');
                        } catch (e) {
                            bildirimGoster('error', 'İş güncellenirken bir hata oluştu');
                        }
                    }
                });
            }
        });
    }
});

// İş silme fonksiyonu
window.isSil = function(isId) {
    if (confirm('Bu işi silmek istediğinize emin misiniz?')) {
        fetch('/api/is-sil', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                is_id: isId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Başarılı silme işlemi
                location.reload(); // Sayfayı yenile
            } else {
                // Hata durumu
                alert('İş silinirken bir hata oluştu: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Hata:', error);
            alert('İş silinirken bir hata oluştu');
        });
    }
}

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
        const mevcutIsler = window.isListesi.filter(item => 
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
                    .filter(calisan => !window.isListesi.some(is => 
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
            const mevcutIs = window.isListesi.find(is => 
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

    window.isListesi.forEach(is => {
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
    const form = $('#yeniIsForm')[0];
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const tasarimKodu = $('#tasarimKoduSelect').val();
    if (!tasarimKodu) {
        bildirimGoster('error', 'Lütfen bir tasarım kodu seçiniz');
        return;
    }
    
    // Form verilerini topla
    const formData = {
        kod: tasarimKodu,
        proje_adi: $('input[name="proje_adi"]').val(),
        teslimat_tarihi: $('input[name="teslimat_tarihi"]').val(),
        durum: $('select[name="durum"]').val(),
        oncelik: $('select[name="oncelik"]').val()
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
                    location.reload(); // Sayfayı yenile
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
                    location.reload(); // Sayfayı yenile
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
                    location.reload(); // Sayfayı yenile
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
                location.reload(); // Sayfayı yenile
            }
        },
        error: function(xhr, status, error) {
            console.error('Monte Carlo sonuçları alınırken hata:', error);
        }
    });
}

function gosterMonteCarloSonuclari(sonuclar) {
    const container = $('#monteCarloSonuclari');
    container.empty();

    // Sonuçlar boş veya tanımsızsa uyarı göster
    if (!sonuclar || Object.keys(sonuclar).length === 0) {
        container.html(`
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Henüz simülasyon sonucu bulunmamaktadır.
            </div>
        `);
        return;
    }

    // Genel istatistikler
    let toplamPerformans = 0;
    let toplamRisk = 0;
    let calisanSayisi = Object.keys(sonuclar).length;

    // Genel istatistikleri hesapla
    Object.values(sonuclar).forEach(data => {
        toplamPerformans += data.ortalama_performans;
        toplamRisk += data.risk_skoru;
    });

    // Genel istatistikleri ekle
    container.append(`
        <div class="col-12 mb-4">
            <div class="alert alert-info">
                <h6 class="mb-2">Genel İstatistikler</h6>
                <div class="row">
                    <div class="col-md-6">
                        <strong>Ortalama Performans:</strong> %${((toplamPerformans / calisanSayisi) * 100).toFixed(1)}
                    </div>
                    <div class="col-md-6">
                        <strong>Ortalama Risk:</strong> %${((toplamRisk / calisanSayisi) * 100).toFixed(1)}
                    </div>
                </div>
            </div>
        </div>
    `);

    // Her çalışan için kart oluştur
    Object.entries(sonuclar).forEach(([calisan, data]) => {
        const performansClass = data.ortalama_performans >= 0.7 ? 'bg-success' : 
                              data.ortalama_performans >= 0.5 ? 'bg-warning' : 'bg-danger';

        const calisanHTML = `
            <div class="col-md-4 mb-3">
                <div class="card h-100">
                    <div class="card-header">
                        <h6 class="mb-0 d-flex justify-content-between align-items-center">
                            ${calisan}
                            <span class="badge ${performansClass}">%${(data.ortalama_performans * 100).toFixed(1)}</span>
                        </h6>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <div class="d-flex justify-content-between mb-2">
                                <span>Risk Skoru:</span>
                                <span class="badge ${data.risk_skoru <= 0.3 ? 'bg-success' : data.risk_skoru <= 0.6 ? 'bg-warning' : 'bg-danger'}">
                                    %${(data.risk_skoru * 100).toFixed(1)}
                                </span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <span>Gecikme Olasılığı:</span>
                                <span class="badge ${data.gecikme_olasiligi <= 0.3 ? 'bg-success' : data.gecikme_olasiligi <= 0.6 ? 'bg-warning' : 'bg-danger'}">
                                    %${(data.gecikme_olasiligi * 100).toFixed(1)}
                                </span>
                            </div>
                            <div class="d-flex justify-content-between">
                                <span>Performans Kararlılığı:</span>
                                <span class="badge bg-info">%${(data.performans_kararliligi * 100).toFixed(1)}</span>
                            </div>
                        </div>
                        
                        ${data.tasarim_bazli_performans && data.tasarim_bazli_performans.length > 0 ? `
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
                                            ${data.tasarim_bazli_performans.map(tasarim => `
                                                <tr>
                                                    <td>${tasarim.tasarim_kodu}</td>
                                                    <td>%${(tasarim.performans_ort * 100).toFixed(1)}</td>
                                                    <td>%${(tasarim.risk * 100).toFixed(1)}</td>
                                                    <td>%${(tasarim.gecikme * 100).toFixed(1)}</td>
                                                </tr>
                                            `).join('')}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ` : '<div class="alert alert-info mt-3">Tasarım bazlı performans verisi bulunmamaktadır.</div>'}
                    </div>
                </div>
            </div>
        `;
        container.append(calisanHTML);
    });
}

// Personelin mevcut durumunu kontrol et
function getPersonelDurum(calisan) {
    // Fason işçiler her zaman müsait
    if (calisan.startsWith('Fason İşçi')) {
        return 'Müsait';
    }
    
    // Çalışanın mevcut işlerini kontrol et
    const mevcutIsler = window.isListesi.filter(is => 
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

// Sayfa yüklendiğinde çalışacak fonksiyonlar
$(document).ready(function() {
    // ... existing code ...
    
    // Son Taguchi sonuçlarını getir
    getSonTaguchiSonuclari();
    
    // Taguchi optimizasyonu başlat butonu
    $('#taguchiOptimizasyonBaslat').click(function() {
        $(this).prop('disabled', true);
        $('#taguchiLoading').show();
        
        $.ajax({
            url: '/api/taguchi-optimizasyon',
            method: 'POST',
            success: function(data) {
                $('#taguchiLoading').hide();
                $('#taguchiOptimizasyonBaslat').prop('disabled', false);
                
                if (data.success && data.taguchi_sonuclari) {
                    gosterTaguchiSonuclari(data.taguchi_sonuclari);
                    bildirimGoster('success', 'Taguchi optimizasyonu başarıyla tamamlandı.');
                } else {
                    bildirimGoster('error', 'Taguchi optimizasyonu sırasında bir hata oluştu.');
                }
            },
            error: function(xhr, status, error) {
                $('#taguchiLoading').hide();
                $('#taguchiOptimizasyonBaslat').prop('disabled', false);
                bildirimGoster('error', 'Taguchi optimizasyonu başlatılırken hata oluştu: ' + error);
            }
        });
    });
});

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