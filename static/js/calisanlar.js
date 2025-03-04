// Çalışanlar sayfası için arama işlevselliği
$(document).ready(function() {
    // Arama kutusuna her karakter girildiğinde filtreleme yap
    $("#calisanArama").on("keyup", function() {
        var value = $(this).val().toLowerCase();
        
        // Tüm çalışan kartlarını kontrol et
        $(".calisan-kart").each(function() {
            var calisanAdi = $(this).find(".calisan-adi").text().toLowerCase();
            
            // Çalışan adı arama değerini içeriyorsa göster, içermiyorsa gizle
            if (calisanAdi.indexOf(value) > -1) {
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
        if ($(".calisan-kart:visible").length === 0) {
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
        $("#calisanArama").val("").trigger("keyup");
    });
}); 