// Tasarım kodları sayfası için arama işlevselliği
$(document).ready(function() {
    // Arama kutusuna her karakter girildiğinde filtreleme yap
    $("#tasarimKoduArama").on("keyup", function() {
        var value = $(this).val().toLowerCase();
        
        // Tüm tasarım kodu kartlarını kontrol et
        $(".tasarim-kart").each(function() {
            var tasarimKodu = $(this).find(".tasarim-kodu").text().toLowerCase();
            var urunAdi = $(this).find(".urun-adi").text().toLowerCase();
            
            // Tasarım kodu veya ürün adı arama değerini içeriyorsa göster, içermiyorsa gizle
            if (tasarimKodu.indexOf(value) > -1 || urunAdi.indexOf(value) > -1) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
        
        // Hiç sonuç yoksa mesaj göster
        checkNoResults();
    });
    
    // Sonuç olup olmadığını kontrol et
    function checkNoResults() {
        if ($(".tasarim-kart:visible").length === 0) {
            // Hiç sonuç yoksa mesaj göster
            if ($("#noResults").length === 0) {
                $(".row").append('<div id="noResults" class="col-12 text-center mt-4"><h4>Sonuç bulunamadı</h4></div>');
            }
        } else {
            // Sonuç varsa mesajı kaldır
            $("#noResults").remove();
        }
    }
    
    // Arama kutusunu temizle butonu
    $("#temizleArama").on("click", function() {
        $("#tasarimKoduArama").val("").trigger("keyup");
    });
}); 