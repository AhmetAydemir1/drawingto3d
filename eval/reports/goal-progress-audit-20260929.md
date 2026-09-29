# Goal sonrası ilerleme denetimi — 2026-09-29

## Karar

**Yön doğru; ilerleme var. Ancak P01/P02'nin tamamlandı durumu erken ve P03'te yalnız görünüş ekseni kalmış değil.** İlk iş yeni özellik eklemek değil, ölçü bağlama arayüzünü tekrar kullanılabilir yapmak; ardından geçiş, referans ve geometri doğruluğu açıklarını kapatmak.

Bu denetimde üretim kaynakları/testleri değiştirilmedi. Mevcut testler çalıştırıldı; bağımsız küçük girdiler ve yeni devam planı kaydedildi.

## Doğrulanan ilerleme

- `make_plan` temel geometriyi iç içe kopyalıyor. Yeni oturumda ölçü ekleme/kaldırma, geri alma ve yeniden açma testi geçti.
- Maksimum kontur açıklığı artık son birleşimde sıfırlanmıyor.
- X/Y, ± yön ve ayrı karar kimliği eklendi; yeni kenar-uç kimlikleri var.
- Eski oturum geçişi ve bağ geçerliliği için başlangıç kodu/testleri yazılmış. Aşağıdaki sınırlar kapanmadığı için bütün aşama tamamlanmış sayılmaz.

## Bu tur çalıştırılan doğrulama

11 dosyalık odak seti: `test_guided`, `test_user_dimensions`, `test_sketch_constraints`, `test_guided_geometry_state`, `test_guided_geometry_migration`, `test_measure_meaning`, `test_stable_identities`, `test_contour_audit`, `test_contour_fix`, `test_contour_audit_matrix`, `test_contour_audit_p02_repeats`.

- İlk koşu: **90 passed, 1 failed / 57,96 s**, exit 1. Tek hata HTTP sunucusunun sandbox içinde port açamaması: `PermissionError`.
- Aynı HTTP testi izinli localhost koşusunda: **1 passed / 0,86 s**, exit 0.
- Seçilen 91 test iki koşuda geçti. Tam takım yeniden çalıştırılmadı.
- Testler yeşil olmasına rağmen aşağıdaki yeni kusur örnekleri yanlış davranış verdi. Eksik kabul testleri plana eklendi.
- Loglar ve kaynak SHA256 kayıtları [kalıcı kanıt klasöründe](../audits/20260929-goal/). Geçici çalışma klasörü: `out/goal-audit-20260929-ycgu28h8/`.

## Açık kusurlar

| Kimlik | Kanıt | Sonuç / öncelik |
|---|---|---|
| F01 | `static/guided.html:13` yanlış `<button <div ...>` yapısı; HTML parser `bind-start=None` veriyor. `guided.js:157` bu elemana onclick atıyor. | Arayüz başlangıcını bozan yeni regresyon; A0 ilk iş |
| F02 | `guided.py:452`: bağ varken profil kaldırılınca `None.get` | Kaydetme/açma yolu soru yerine hata verebiliyor; A0 |
| F03 | `guided.py:910–919`: kenar ID'si ve ölçü ID'si değişince `_same_geometry=True` | Geçiş doğrulaması profil/daire adlarıyla sınırlı; ölçülerde yanlış `span_id` alanı okunuyor |
| F04 | `guided.py:1133–1158`: geçiş stale iken `public` eski STEP URL'si ve complete döndürüyor | Geçiş sonrası çıktı güncelliği iki uçta da denetlenmeli; eski dosya korunmalı |
| F05 | `guided.py:454–457,652–663`: eski indeks bağı başka profile geçince unresolved boş | Gerçek kalıcı dönüşüm yok; indeks mevcut listedeki farklı kenara kayabiliyor |
| F06 | Yeni edge ID'lerini paylaşan farklı profil veya bağlı kenarı drop etme kararı unresolved üretmiyor | Referans profil/sürüm/düzenlenmiş topoloji kapsamı eksik |
| F07 | Kanonik `a/b` aynı yarımı gösterirken ikinci yayın saklanan start/end'i karşı yarım verilince audit ok | Audit açıyı start'tan türetiyor; CAD ile aynı yayı kontrol etmiyor |
| F08 | R100/R99 geçerli yarım halka overlap diye reddediliyor | %2 yarıçap toleransı farklı çemberleri aynı destek sayıyor |
| F09 | R1000 yarım yay + y=999 yatay segmentinde x=±sqrt(1999) kesişimleri kaçıyor | 32 örnek üretim kapısı için güvenilir kesişim testi değil |
| F10 | Komşu olmayan (50,0) teması Y yansımasının birinde geçiyor, diğerinde reddediliyor | Uç teması/çapraz çarpım sıfır durumu tutarsız |
| F11 | Aynı 0,8 px çizginin ileri/geri tekrarı ok veriyor | Sabit 1 px örtüşme eşiği sıfır alanlı konturu kaçırıyor |
| F12 | 100 mm kareye yalnız iki merkez arasında 30 mm X bağı eklenince dış genişlik 50 mm | Kalibrasyon yerel kısıtla yeniden ölçekleniyor |
| F13 | X=50/Y=30 köşe ölçüleri ortak ölçekte 42,5/42,5 bulunup reddediliyor | Eski ortak ölçek kapısı geçerli bağımsız kısıtları engelliyor |
| F14 | Geçerli yay+3 çizgi profilinde yay köşe ölçüsü unsupported, fakat make_plan kabul | Desteklenmeyen kullanıcı ölçüsü sessizce atlanabiliyor |

Satır numaraları denetlenen kaynak anına aittir; sonraki değişiklikte fonksiyon adını esas alın.

### Testlerin eksik bıraktıkları

- Geçiş testi tüm profilin kaldırılmasını sınamış; aynı profil ID'si altında kenar/ölçü kimliği değişimini sınamamış.
- Profil değişimi testi farklı `z0/z1` ID'lerini kullanmış; aynı ID'leri paylaşan profilleri sınamamış.
- Eski indeks testi başlangıçtaki listeyi kullanmış; profil değişimi/kenar silme/undo geçmişini sınamamış.
- Yarım yay testi kanonik başlangıç açısını yanlış bırakmış; CAD ile ortak tanım doğrulanmamış.
- JS sözdizimi ve dosyanın HTTP ile sunulması, HTML'de gereken düğmenin gerçekten var olduğunu doğrulamamış.
- Test sayısının artması bütün ürün akışının doğru olduğuna kanıt değildir.

### Kanıtın sınırı

HTML sonucu kaynak ve Python HTML ayrıştırıcısıyla doğrulandı; bu tur canlı tarayıcı kabulü yapılmadı. Bağımsız ölçek/unsupported örnekleri `make_plan`/karar yolunu sınadı; bu girdilerden yeni STEP üretildiği iddia edilmiyor. Geçiş probu sahte okuyucu girdisini kullanarak store davranışını izole ediyor; kullanıcı oturumları değiştirilmedi.

P04'te ayrıca kaynak ifadeleri, sabit datum, yatay/dikey ilişkiler, önizleme ile CAD'in aynı son geometriyi kullanması ve çözüm sonrası denetim açık. Bunları yeni testler geçmeden tamamlandı saymayın.

## Güncel yönlendirme

1. **A0:** HTML/DOM ve boş profil hata akışı.
2. **P01-a/b:** Eski oturum yedeği, gerçek kimlik eşleşmesi, eski çıktının güncelliği.
3. **P02-a/b/c:** Kanonik yay tanımı, doğru örtüşme ve kesişim.
4. **P03-a/b/c:** Kalıcı eski referans geçişi, profil/sürüm kapsamı, açık kullanıcı çerçevesi.
5. **P04-a…f:** Sabit kalibrasyon, ret durumları, tek hazırlama sonucu, kaynak ifadeleri, son denetim, bağımsız CAD doğrulaması.
6. Sonra P05–P08; genel kapsam ve model işleri P09–P12.

Ayrıntılı adımlar ve tamamlanma koşulları [PLAN.md](../../PLAN.md) içinde. [Önceki uygulama günlüğü](../../docs/IMPLEMENTATION_HISTORY_BEFORE_REAUDIT_20260929.md) yalnız tarihçedir.

## Belge doğrulaması

Dosya bağlantıları, Markdown blokları ve üç devir başlığının eşleşmesi kontrol edildi; dokümanlarda whitespace denetimi geçti. Denetim başındaki SHA256 kayıtlarıyla kaynak/test dosyalarının değişmediği doğrulandı. P01/P03'ün sonraki entegrasyona bağlı kabul maddeleri plana açıkça yazıldı; aşamalar birbirini döngüsel beklemeyecek.
