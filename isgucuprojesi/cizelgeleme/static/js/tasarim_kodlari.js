$(document).ready(function() {
    const csrftoken = document.querySelector('[name=csrf-token]').content;

    $('#tasarimKoduKaydet').click(function() {
        var formData = {};
        $('#yeniTasarimKoduForm').serializeArray().forEach(function(item) {
            formData[item.name] = item.value;
        });

        formData.personel_ihtiyaci = {
            ustabasi: parseInt(formData.ustabasi) || 0,
            kalifiyeli: parseInt(formData.kalifiyeli) || 0,
            cirak: parseInt(formData.cirak) || 0
        };

        delete formData.ustabasi;
        delete formData.kalifiyeli;
        delete formData.cirak;

        $.ajax({
            url: '/api/tasarim-kodu-ekle',
            method: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': csrftoken },
            data: JSON.stringify(formData),
            success: function(response) {
                if (response.success) {
                    location.reload();
                }
            }
        });
    });
});

function tasarimKoduSil(kod) {
    const csrftoken = document.querySelector('[name=csrf-token]').content;

    if (confirm(kod + ' kodlu tasarımı silmek istediğinize emin misiniz?')) {
        $.ajax({
            url: '/api/tasarim-kodu-sil',
            method: 'POST',
            contentType: 'application/json',
            headers: { 'X-CSRFToken': csrftoken },
            data: JSON.stringify({ kod: kod }),
            success: function(response) {
                if (response.success) {
                    location.reload();
                } else {
                    alert('Hata: ' + response.message);
                }
            }
        });
    }
}


// Arama kutusu ile filtreleme
$(document).ready(function () {
    $("#tasarimKoduArama").on("keyup", function () {
        var value = $(this).val().toLowerCase();

        $(".tasarim-kart").each(function () {
            var tasarimKodu = $(this).find(".tasarim-kodu").text().toLowerCase();
            var urunAdi = $(this).find(".urun-adi").text().toLowerCase();

            if (tasarimKodu.includes(value) || urunAdi.includes(value)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });

        checkNoResults();
    });

    function checkNoResults() {
        if ($(".tasarim-kart:visible").length === 0) {
            if ($("#noResults").length === 0) {
                $(".row").append('<div id="noResults" class="col-12 text-center mt-4"><h4>Sonuç bulunamadı</h4></div>');
            }
        } else {
            $("#noResults").remove();
        }
    }

    $("#temizleArama").on("click", function () {
        $("#tasarimKoduArama").val("").trigger("keyup");
    });
});
