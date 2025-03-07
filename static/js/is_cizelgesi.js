// Global değişken tanımlaması
let isListesi = [];

// Global fonksiyonlar
window.showGenetikSonuclari = async function() {
    try {
        const response = await fetch('/api/genetik-sonuclari');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        console.log('Genetik sonuçları:', data);
        
        const genetikDiv = document.getElementById('genetikSonuclar');
        const genetikTablo = document.getElementById('genetikTablo');
        
        if (!genetikDiv || !genetikTablo) {
            console.error('Genetik sonuçları için gerekli HTML elementleri bulunamadı');
            return;
        }

        // Sonuçları göster
        genetikDiv.style.display = 'block';
        genetikTablo.innerHTML = '';

        // Her tasarım kodu için sonuçları tabloya ekle
        for (const [tasarimKodu, sonuc] of Object.entries(data)) {
            const row = document.createElement('tr');
            
            // Personel durumu kontrolü
            const personelDurumu = sonuc.eksik_personel && Object.values(sonuc.eksik_personel).some(sayi => sayi > 0)
                ? `<span class="badge bg-warning">Eksik Personel</span>`
                : `<span class="badge bg-success">Tam Kadro</span>`;

            row.innerHTML = `
                <td>${tasarimKodu}</td>
                <td>
                    ${sonuc.atanan_calisanlar ? `
                        <div><strong>Ustabaşı:</strong> ${sonuc.atanan_calisanlar.ustabasi?.join(', ') || '-'}</div>
                        <div><strong>Kalifiye:</strong> ${sonuc.atanan_calisanlar.kalifiyeli?.join(', ') || '-'}</div>
                        <div><strong>Çırak:</strong> ${sonuc.atanan_calisanlar.cirak?.join(', ') || '-'}</div>
                    ` : 'Personel ataması yapılmadı'}
                </td>
                <td>
                    ${personelDurumu}
                    <button class="btn btn-sm btn-info ms-2" onclick="showGenetikDetay('${tasarimKodu}', ${JSON.stringify(sonuc).replace(/"/g, '&quot;')})">
                        Detay
                    </button>
                </td>
            `;
            
            genetikTablo.appendChild(row);
        }
    } catch (error) {
        console.error('Genetik sonuçları yükleme hatası:', error);
        const genetikDiv = document.getElementById('genetikSonuclar');
        if (genetikDiv) {
            genetikDiv.innerHTML = `
                <div class="alert alert-danger">
                    Genetik sonuçları yüklenirken bir hata oluştu: ${error.message}
                </div>
            `;
        }
    }
};

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
(function() {
    // İş listesi verilerini JSON olarak al
    let isListesi;

    // Sayfa yüklendiğinde çalışacak kodlar
    document.addEventListener('DOMContentLoaded', function() {
        // İş listesini yükle
        const isListesiData = document.getElementById('isListesiData');
        if (isListesiData && isListesiData.value) {
            try {
                window.isListesi = JSON.parse(isListesiData.value);
                isListesi = window.isListesi; // Global değişkeni güncelle
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
        // Geciken iş sayısını hesapla
        const bugun = new Date();
        const gecikenIs = isListesi.filter(is => {
            if (is.durum !== 'tamamlandi') {
                const teslimatTarihi = new Date(is.teslimat_tarihi);
                return teslimatTarihi < bugun;
            }
            return false;
        }).length;
        
        document.getElementById('gecikenIsSayisi').textContent = gecikenIs;
        
        // İşleri önceliğe göre sırala
        const tbody = document.querySelector('.table tbody');
        if (tbody) {
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            rows.sort((a, b) => {
                const oncelikBadgeA = a.querySelector('td .badge.oncelik-badge');
                const oncelikBadgeB = b.querySelector('td .badge.oncelik-badge');
                
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

        // Son atama detaylarını güncelle
        showLastAssignmentDetails();
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

    function updateIsDurumu(kod, yeniDurum) {
        const row = document.querySelector(`tr[data-tasarim-kodu="${kod}"]`);
        if(!row) return;
        const badge = row.querySelector('.badge');

        if (badge) {
            let yeniText, yeniClass;
            
            switch(yeniDurum) {
                case "devam_ediyor":
                    yeniText = "Devam Ediyor";
                    yeniClass = "bg-warning";
                    break;
                case "beklemede":
                    yeniText = "Beklemede";
                    yeniClass = "bg-secondary";
                    break;
                case "tamamlandi":
                    yeniText = "Tamamlandı";
                    yeniClass = "bg-success";
                    break;
                default:
                    return;
            }

            badge.textContent = yeniText;
            badge.className = 'badge ' + yeniClass;

            // Durumu veritabanında güncelle
            updateIsStatus(kod, yeniDurum, yeniDurum === "tamamlandi" ? 100 : 
                                         yeniDurum === "devam_ediyor" ? 
                                         parseInt(row.querySelector('.progress-bar').style.width) || 0 : 0);
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
})();

// İş güncelleme fonksiyonu
function isGuncelle(tasarimKodu) {
    var modal = new bootstrap.Modal(document.getElementById('isGuncellemeModal'));
    
    var isRow = $(`tr[data-tasarim-kodu="${tasarimKodu}"]`);
    var durum = isRow.find('.badge.durum-badge').text().trim().toLowerCase().replace(/\s+/g, '_');
    var oncelik = isRow.find('.badge.oncelik-badge').text().trim().toLowerCase();
    
    $('#isGuncellemeForm input[name="tasarim_kodu"]').val(tasarimKodu);
    $('#isGuncellemeForm select[name="durum"]').val(durum);
    $('#isGuncellemeForm select[name="oncelik"]').val(oncelik);
    
    modal.show();
}

$('#isGuncellemeKaydet').click(function() {
    var formData = {};
    $('#isGuncellemeForm').serializeArray().forEach(function(item) {
        formData[item.name] = item.value;
    });
    
    $.ajax({
        url: '/api/is-guncelle',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                var isRow = $(`tr[data-tasarim-kodu="${formData.tasarim_kodu}"]`);
                
                isRow.find('.badge.durum-badge')
                    .text(formData.durum.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()))
                    .removeClass('bg-warning bg-secondary')
                    .addClass(formData.durum === 'devam_ediyor' ? 'bg-warning' : 'bg-secondary');
                
                isRow.find('.badge.oncelik-badge')
                    .text(formData.oncelik.charAt(0).toUpperCase() + formData.oncelik.slice(1))
                    .removeClass('bg-danger bg-info')
                    .addClass(formData.oncelik === 'kritik' ? 'bg-danger' : 'bg-info');
                
                $('#isGuncellemeModal').modal('hide');
                
                // Tabloyu yeniden sırala
                initDashboard();
                
                alert('İş başarıyla güncellendi');
            } else {
                alert('Hata oluştu: ' + response.message);
            }
        },
        error: function(xhr, status, error) {
            alert('Hata oluştu: ' + error);
        }
    });
});

// İş silme fonksiyonu
function isSil(isId) {
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

// Kalan süreyi güncelle
function updateKalanSure(kod, val) {
    try {
        const sure = parseInt(val);
        if (!isNaN(sure)) {
            fetch('/api/update-kalan-sure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tasarim_kodu: kod,
                    kalan_sure: sure
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Başarılı güncelleme
                    document.querySelectorAll(`.kalanSureText[data-kod="${kod}"]`)
                        .forEach(el => el.textContent = sure);
                }
            })
            .catch(error => console.error('Hata:', error));
        }
    } catch (error) {
        console.error('Süre güncelleme hatası:', error);
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
    
    // Öncelik değerini doğrudan seçili option'dan al
    const oncelikSelect = form.querySelector('select[name="oncelik"]');
    const secilenOncelik = oncelikSelect.options[oncelikSelect.selectedIndex].value;
    
    const formData = {
        kod: $('#tasarimKoduSelect').val(),
        proje_adi: $('input[name="proje_adi"]').val(),
        teslimat_tarihi: $('input[name="teslimat_tarihi"]').val(),
        durum: $('select[name="durum"]').val(),
        oncelik: secilenOncelik
    };
    
    console.log('Gönderilen form verisi:', formData); // Debug için log ekle
    
    // Yükleme göstergesini göster
    $('#loadingSpinner').show();
    
    // API isteği gönder
    $.ajax({
        url: '/api/is-kaydet',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        success: function(response) {
            if (response.success) {
                // Başarılı mesajı göster
                showAlert('success', response.message);
                
                // Modalı kapat
                $('#yeniIsModal').modal('hide');
                
                // Formu temizle
                $('#yeniIsForm')[0].reset();
                
                // İş listesini güncelle - Optimizasyon tamamlanana kadar bekle
                setTimeout(function() {
                    // Sayfayı yenile
                    window.location.reload();
                }, 1000);
            } else {
                showAlert('error', response.message || 'Bir hata oluştu');
                $('#loadingSpinner').hide();
            }
        },
        error: function(xhr, status, error) {
            console.error('Hata:', error);
            showAlert('error', 'İş kaydedilirken bir hata oluştu');
            $('#loadingSpinner').hide();
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

// Monte Carlo simülasyonu başlatma
$(document).ready(function() {
    $('#monteCarloBaslat').click(function() {
        // Yükleme göstergesini göster
        $('#monteCarloLoading').show();
        $('#monteCarloSonuc').hide();
        
        // Monte Carlo simülasyonunu başlat
        $.ajax({
            url: '/api/monte-carlo-simulasyonu',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                n_scenarios: 50,
                absence_prob: 0.05,
                performance_std: 0.1
            }),
            success: function(response) {
                // Yükleme göstergesini gizle
                $('#monteCarloLoading').hide();
                
                // Hata kontrolü
                if (response.error) {
                    alert('Monte Carlo simülasyonu hatası: ' + response.error);
                    return;
                }
                
                // Temel metrikleri güncelle
                $('#mcAvg').text(response.avg_fitness ? response.avg_fitness.toFixed(2) : '-');
                $('#mcBest').text(response.max_fitness ? response.max_fitness.toFixed(2) : '-');
                $('#mcWorst').text(response.min_fitness ? response.min_fitness.toFixed(2) : '-');
                $('#mcStd').text(response.std_fitness ? response.std_fitness.toFixed(2) : '-');
                
                // Personel ihtiyacı dağılımını göster
                if (response.personel_ihtiyaci_dagilimi) {
                    let tableHTML = `
                        <div class="mt-4">
                            <h5>Personel İhtiyacı Dağılımı</h5>
                            <div class="table-responsive">
                                <table class="table table-striped table-bordered">
                                    <thead>
                                        <tr>
                                            <th>Tasarım Kodu</th>
                                            <th>Ustabaşı</th>
                                            <th>Kalifiye</th>
                                            <th>Çırak</th>
                                            <th>Toplam</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;
                    
                    let toplamUstabasi = 0;
                    let toplamKalifiyeli = 0;
                    let toplamCirak = 0;
                    
                    Object.entries(response.personel_ihtiyaci_dagilimi).forEach(([kod, ihtiyac]) => {
                        const ustabasi = ihtiyac.ustabasi || 0;
                        const kalifiyeli = ihtiyac.kalifiyeli || 0;
                        const cirak = ihtiyac.cirak || 0;
                        const toplam = ustabasi + kalifiyeli + cirak;
                        
                        toplamUstabasi += ustabasi;
                        toplamKalifiyeli += kalifiyeli;
                        toplamCirak += cirak;
                        
                        tableHTML += `
                            <tr>
                                <td><strong>${kod}</strong></td>
                                <td>${ustabasi > 0 ? `<span class="badge bg-primary">${ustabasi}</span>` : '0'}</td>
                                <td>${kalifiyeli > 0 ? `<span class="badge bg-info">${kalifiyeli}</span>` : '0'}</td>
                                <td>${cirak > 0 ? `<span class="badge bg-secondary">${cirak}</span>` : '0'}</td>
                                <td><strong>${toplam}</strong></td>
                            </tr>
                        `;
                    });
                    
                    // Toplam satırı ekle
                    const toplamPersonel = toplamUstabasi + toplamKalifiyeli + toplamCirak;
                    tableHTML += `
                        <tr class="table-dark">
                            <td><strong>TOPLAM</strong></td>
                            <td><strong>${toplamUstabasi}</strong></td>
                            <td><strong>${toplamKalifiyeli}</strong></td>
                            <td><strong>${toplamCirak}</strong></td>
                            <td><strong>${toplamPersonel}</strong></td>
                        </tr>
                    `;
                    
                    tableHTML += `
                                </tbody>
                            </table>
                        </div>
                    `;
                    
                    // Risk değerlendirmesi
                    let riskHTML = '';
                    if (response.scenarios && response.scenarios.length > 0) {
                        // Düşük uygunluk skoruna sahip senaryoları bul
                        const riskliSenaryolar = response.scenarios.filter(s => s.fitness < response.avg_fitness * 0.8);
                        
                        if (riskliSenaryolar.length > 0) {
                            riskHTML = `
                                <div class="alert alert-danger mt-4">
                                    <h5><i class="bi bi-exclamation-triangle"></i> Risk Değerlendirmesi</h5>
                                    <p>Simülasyonda ${riskliSenaryolar.length} adet düşük performanslı senaryo tespit edildi.</p>
                                    <p>Bu senaryolarda personel devamsızlığı veya performans düşüklüğü nedeniyle iş akışında aksamalar yaşanabilir.</p>
                                </div>
                            `;
                        } else {
                            riskHTML = `
                                <div class="alert alert-success mt-4">
                                    <h5><i class="bi bi-check-circle"></i> Risk Değerlendirmesi</h5>
                                    <p>Simülasyonda önemli bir risk faktörü tespit edilmedi. İş akışı normal şartlarda sorunsuz ilerleyecektir.</p>
                                </div>
                            `;
                        }
                    }
                    
                    // Optimizasyon önerileri
                    let onerileriHTML = '';
                    if (toplamPersonel > 0) {
                        onerileriHTML = `
                            <div class="alert alert-info mt-4">
                                <h5><i class="bi bi-lightbulb"></i> Optimizasyon Önerileri</h5>
                                <p>Toplam personel ihtiyacı: <strong>${toplamPersonel}</strong> kişi</p>
                                <ul>
                                    <li>Ustabaşı: ${toplamUstabasi} kişi</li>
                                    <li>Kalifiye: ${toplamKalifiyeli} kişi</li>
                                    <li>Çırak: ${toplamCirak} kişi</li>
                                </ul>
                                <p>Mevcut personel sayısı ve dağılımı bu ihtiyacı karşılamıyorsa, ek personel alımı veya mevcut personelin eğitimi düşünülebilir.</p>
                            </div>
                        `;
                    }
                    
                    // Sonuçları göster
                    $('#advancedAnalysis').html(tableHTML);
                    $('#riskAssessment').html(riskHTML);
                    $('#optimizationSuggestions').html(onerileriHTML);
                }
                
                // Sonuç bölümünü göster
                $('#monteCarloSonuc').show();
            },
            error: function(xhr, status, error) {
                $('#monteCarloLoading').hide();
                alert('Monte Carlo simülasyonu başlatılırken hata oluştu: ' + error);
            }
        });
    });
});

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