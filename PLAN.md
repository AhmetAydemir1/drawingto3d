# drawingto3d — Hermes: G3 kayıt sınırlarını düzelt ve kabulü tamamla

**Tarih:** 2026-10-06\
**İncelenen HEAD:** `2cdb4d0424b17e4299d625066c24e6a0eab4de6d` (`2cdb4d0`)\
**Ana ürün yönü:** [PLAN-20](docs/PLAN-20.md) · **Önceki G3 uygulama planı:** [PLAN-22](docs/PLAN-22.md)\
**Bu görev:** G3R-01 → G3R-02 → G3R-03 → G3R-04 → doğrulama ve teslim.\
**G4 ve sonrası:** Bu görev kapsamında uygulanmayacak.

Bu dosya, kullanıcının “yapılanları kontrol et ve plan.md hazırla” isteği için hazırlanmıştır. İnceleme sırasında ürün kodu değiştirilmedi. Buradaki uygulama talimatları, kullanıcı bu planı Hermes'e **“uygula”** diye verdiğinde yürütülecek görevdir. Dört düzeltme arasında tekrar faz onayı isteme; hepsi aynı işin kapsamıdır. Kabul kapısı geçmeden parser geliştirmesine başlama.

Önceki kök planın baytları [arşivde](docs/PLAN_ROOT_BEFORE_G3_ACCEPTANCE_REVIEW_20261006.md) korunmuştur; SHA-256: `5743bb06f40ab04761d8d8f14492fee9994774d06779c4f46d53a1d6bffa7fb1`. Bu içerik `docs/PLAN-22.md` ile aynıdır. Bu diskte `plan.md` ve `PLAN.md` aynı dosyaya gider; mevcut Git adı korunmuştur.

## 1. Hermes'e verilecek mesaj

> Kök PLAN.md'yi uygula. G3 arayüzü ve kısa uç düzeltmesi mevcut; bunları baştan yazma. Önce yeni review scriptindeki yedi ihlali ve gerçek HTTP tekrarındaki /save bypass'ını doğrula. G3R-01–04'ü sırayla düzelt: bütün kayıt yollarında aynı kullanıcı kararı kuralları, yeni hedef onayında gerçek freshness kontrolü, v1→v2 şema damgası ve detection diagnostics'in public/UI'a taşınması. Her işte önce anlamlı kırmızı regresyon, sonra dar düzeltme ve yeşil test yap. Eksik alanı koruma, açık boş liste, eski kararları aynen taşıma, undo, no-op ve build stale davranışlarını bozma. İlgili HTTP ve tarayıcı kabulünü tamamla. G4/parser/target önericisi/CAD compile/model çağrısı yok. İlerleme kaydını güncelle; dört düzeltmenin kabul tablosuyla teslim et.

**Okuma sırası:** §2 inceleme → §3 çalışma sınırları → §4–7 düzeltmeler → §8–10 test ve teslim. Eski numaralı planlardaki tamamlanmış fazları yeniden açma.

## 2. Bağımsız inceleme: ne tamam, ne eksik?

### 2.1 Doğrulanan ilerleme

- G3 için `ManualCalloutDecision`, `CalloutReviewDecision`, `effective_callouts()`, dört store komutu ve `/api/guided/callout` var.
- UI'da overlay, seçim/crop, kullanıcı metni, makine ipucunu bilinçli alma, ignore/restore, manuel alan, bölge düzenleme ve kaydedilmemiş metin taslağı var.
- Bölge düzenleme komutu eski transcription snapshot'ını koruyor; public state `stale/region_changed` gösteriyor.
- Kısa kenar düzeltmesi doğru: fiziksel nokta eşitliği 0.5 px; kontur onarım bütçesi 20 px ayrı kalmış. Bağımsız scriptte 5/10/20/21 px uçlar kabul, aynı köşenin alias'ları ret: **5/5**.
- Önceki çıkarılmış kenar / yeniden onay günlüğü bulguları kapalı: bağımsız tekrar **2/2**.
- Gerçek parser, parse onayı, target önericisi ve callout→CAD compile hâlâ yok. Testte hazırlanmış parse verisi çalışan parser kanıtı değildir.

**Karar:** G3 uygulaması önemli ölçüde mevcut; aşağıdaki kayıt sözleşmesi açıkları yüzünden bağımsız kabul tamamlanmış sayılmaz. G3'ü silip yeniden yazma. G4'ten önce bu dar düzeltmeleri bitir.

### 2.2 Bu incelemede gerçekten çalıştırılanlar

| Kontrol | Gerçek sonuç |
|---|---|
| Beş dosya: callout review/models/store, contour fix, guided HTML | **141 passed / 1.58 s / exit 0** |
| Kalan 13 ilgili test dosyası | **143 passed, 1 failed / 126.17 s / exit 1**; tek failure sandbox'ın localhost bind engeli |
| Aynı HTTP testi localhost izniyle tekrar | **1 passed / 0.80 s / exit 0** |
| Seçili kümenin toplamı | **285 farklı test doğrulandı**; üç koşunun birleşimi, tek koşu değildir |
| Önceki G1 review scripti | **2/2, exit 0** |
| Önceki kısa kenar review scripti | **5/5, exit 0** |
| Yeni bağımsız store/public kontrolleri | **7 ihlal, exit 1**; §4–7'de dört iş olarak gruplanmıştır |
| Yeni gerçek HTTP tekrarı | **exit 1**: `/callout` doğru 400; aynı yasak metin `/save` üzerinden 200 |

Kanıt dizini: [eval/audits/20261006-guided-g3-independent-review](eval/audits/20261006-guided-g3-independent-review).

- [Tam komutlar ve koşu metadata'sı](eval/audits/20261006-guided-g3-independent-review/review-metadata.json)
- [Odak testleri](eval/audits/20261006-guided-g3-independent-review/focused.log), [regresyonlar](eval/audits/20261006-guided-g3-independent-review/regression.log), [HTTP tekrar](eval/audits/20261006-guided-g3-independent-review/http-recheck.log)
- [Yedi ihlalin çıktısı](eval/audits/20261006-guided-g3-independent-review/probe-results-before.json), [HTTP bypass kanıtı](eval/audits/20261006-guided-g3-independent-review/http-probe-before.json)
- [Kısa kenar tekrarları](eval/audits/20261006-guided-g3-independent-review/endpoint-recheck.json), [önceki bulgular](eval/audits/20261006-guided-g3-independent-review/previous-findings-recheck.json)

Hermes'in [G3 browser logu](eval/audits/20261006-guided-g3-review/browser-acceptance.log) **28/28 PASS** bildiriyor. Kabul scripti, log/step kaydı ve ekran görüntüsü incelendi; **bu bağımsız turda tarayıcı senaryoları yeniden yürütülmedi**. Bu sonucu kendi yeni tarayıcı koşun gibi raporlama.

Tam test takımı yeniden çalıştırılmadı. Bilinen `tests/test_planner.py::test_settings_record_is_the_run_record_fields` failure'ı önceki incelemede doğrulandı: beklenen anahtar kümesinde `repeat_penalty` ve `repeat_last_n` yok. [Önceki kanıt](eval/audits/20261006-guided-g2-review/known-planner-failure.log) korunuyor. “Tüm testler yeşil” deme; bu hatayı kapatmak için ilgisiz ayar/test değiştirme.

## 3. Çalışma ve yetki sınırları

1. `git status --short`, HEAD ve varsa yeni diff'i oku; geçerli `AGENTS.md` talimatlarını kontrol et. `2cdb4d0` üstüne yeni iş geldiyse eski satır numaraları yerine fonksiyon adlarıyla ilerle.
2. `PLAN-17-HERMES.md`, numaralı planlar ve geçmiş kanıtlar korunacak. `*-before` çıktısını sonraki koşuyla ezme; `*-after` kullan. Yeni numaralı kopya gerekiyorsa önce boş numarayı kontrol et; `PLAN-22`'yi ezme.
3. `docs/GUIDED_PROGRESS.md` içine bu dört iş için yeni tablo ekle: `BEKLİYOR / DEVAM / GEÇTİ / ENGELLİ`. Yeniden başlayınca önce bu tabloyu ve diff'i oku; biten işi tekrarlama.
4. Tek küçük iş döngüsü: hatayı tekrar et → regresyon → dar düzeltme → ilgili test → komut/exit code/log/sonraki adımı kaydet.
5. Üç başarısız denemeden sonra kör değişiklik yapma. Küçük tekrar ve hipotez kaydet; bağımsız kapsam içi işe devam edebilirsin. Engeli başarı diye işaretleme.
6. Yeni framework, ikinci store/undo sistemi, CAD motoru, OCR servisi, model çağrısı veya SEMREAD çalışması yok. Araştırma `PARKED`, dev bütçesi 4/12 olarak kalır.
7. Mevcut `.venv/bin/python` kullan. Yardımcı araç için proje ortamını yeniden çözümleme/senkronlama; `uv run` ile bağımlılıkları istemeden kaldırma. Ortam hatasında önce gerçek nedeni belirle.
8. Tarayıcı aracı localhost'a izin vermiyorsa aracın güvenlik engelini dolanma veya genel güvenlik ayarını kapatma. İzinli yerel tarayıcı/test yolunu kullan; gereken ortam iznini somut engelle raporla.
9. Testi skip/xfail ederek veya bekleneni bozuk davranışa uydurarak kapı geçme. Test kanıtını uydurma; store testi, gerçek HTTP testi ve tarayıcı testi ayrı şeylerdir.
10. Yalnız ilgili değişiklikleri açık dosya adlarıyla stage et. Push/merge/deploy teslim koşulu değil. Kaynak çizim dışındaki gold/reference STEP bilgisi producer'a giremez.

## 4. G3R-01 — Eski `/save` yeni kuralları atlamasın

**Yer:** `guided.py`: `save`, `edit_callout`, `_prepare_callouts`, `_validate_callouts`; `app.py` dispatch.

### Kanıt

Mevcut komut doğrulamaları `_apply_callout_command` içinde. Eski `save` ise yeni `manual_callouts` / `callout_reviews` alanlarını Pydantic şekil kontrolünden sonra bağlamlarını doğrulamadan kalıcılaştırıyor. Bağımsız tekrarlar şunları kabul ettirdi:

- İstemcinin seçtiği `manual:000…`, başka source digest'i, `page_index=7`, `revision=999`.
- `unknown-callout` için review/ignore kararı ve istemci revision'ı.
- Ignored callout'a yeni transcription; `/callout` ret verirken `/save` metni `current` olarak kaydediyor.
- Yeni transcription için gerçek etkin bölgeden farklı `source_region` snapshot'ı.

Bu yerel uygulamada kayıt bütünlüğü sorunudur. UI'nın şu an yalnız doğru komutu çağırması API sözleşmesini düzeltmez.

### Yapılacak iş

**Dışarıdan gelen tam karar kaydı ile sunucunun ürettiği G3 komutunu ayır; ortak atomic commit/history yolunu koru.** Somut uygulanabilir yol:

1. Ortak doğrulama/commit bölümünü gerekiyorsa private store yardımcısına çıkar. Public `save` ve `edit_callout` aynı tek kalıcılık yoluna ulaşsın.
2. Yeni manual kimlik, kaynak, page ve revision yalnız `add_region` tarafından sunucuda üretilsin. Public `/save` üzerinden manual kayıt ekleme veya var olanın kimlik/kaynak/page/region/revision'ını değiştirme reddedilsin; kullanıcı region düzenlemesini `edit_region` yapar.
3. Yeni/değişmiş G3 review kararları ilgili komut yolundan geçsin. Public `/save` mevcut `manual_callouts` / `callout_reviews` satırlarını aynen taşıyabilsin. Eksik anahtar mevcut veriyi korusun; açık `[]` mevcut açık kaldırma sözleşmesini korusun.
4. Bu ayrım için HTTP payload'ından alınan `trusted`, `internal`, `skip_validation` gibi bayrak ekleme. İçeride hazırlanan karar da ilişki ve model doğrulamasından geçsin.
5. Public `/save` ile yeni/değişmiş transcription desteklenmeye devam edecekse aynı kaynak/callout/ignored ve source-region kurallarını uygula. Yanlış snapshot'ı reddet veya yalnız açık yeni metin eyleminde sunucuda türet. **Taşınan eski transcription'ı yeniden damgalama.**
6. Etkin callout görünümünü işlemin bırakacağı kararlara göre hesapla; sadece önceki record'a bakma. Yeni/değişmiş review referansı bu oturuma ait, mevcut ve desteklenen page'de olmalı.
7. Kullanıcı olaylarını ortak karar farkından veya doğrulanmış komuttan üret; aynı eylemi iki kez loglama. Açık list temizleme de gerçek kaldırma/restore olarak kayda geçsin. Public istemci log olaylarını belirleyemesin.
8. Reddedilen işlem dosyayı, revision/history/log/build'i değiştirmesin. İlgisiz kalınlık/profil kaydı, aynen taşınan eski/stale kararlar yüzünden reddedilmesin.

**Önemli ayrım:** Yeni karar doğrulanır; eski kararın aynen taşınması yeni onay değildir. Önceden kalmış yabancı/orphan/stale veriyi bu düzeltme içinde sessizce düzeltme veya silme. Undo güvenilir history snapshot'ını geri yükler; istemcinin keyfi snapshot yüklemesi değildir.

### Kabul

- Yukarıdaki dört probe geçer; gerçek HTTP'de ignored transcription hem `/callout` hem `/save` için 400 ve kayıtta bayt değişimi yoktur.
- `add_region → transcribe → edit_region → yeniden metin kaydet → ignore → restore → undo` hâlâ çalışır.
- Eksik G3 anahtarları korur; açık `[]` temizler; unrelated full-save mevcut G3 satırlarını/revision'larını aynen taşır.
- Her gerçek eylem bir history adımı/global revision; aynı karar no-op. Başarısız request hiçbir audit olayı yazmaz.
- Undo önceki manual/review/metin snapshot'ını döndürür; temel detector adaylarını değiştirmez ve eski STEP'i current yapmaz.

## 5. G3R-02 — Yeni hedef onayında freshness gerçekten zorunlu olsun

**Yer:** `_validate_callouts` ve `callout_models` freshness yardımcıları.

### Kanıt

`k1` metni revision 1 ve test fixture parse'ı mevcutken bölge komutla taşındı. Public state hem transcription hem parse için `stale/region_changed` dedi. Buna rağmen eski transcription/parse bağıyla yeni circle hedefi kaydedilebildi; `status=confirmed` ve kullanıcı onay olayı oluştu.

Public freshness hedefi sonrasında stale gösterebilir; bulgu **stale veriye dayanarak yeni onayın kalıcı kabul edilmesi**dir. Buradan yanlış STEP üretildiği iddia edilmiyor; compiler henüz yok.

### Yapılacak iş

1. Yeni veya `reconfirm=true` hedef için, kaydın bırakacağı **etkin kararlar** üzerinden transcription ve parse freshness'ini hesapla.
2. Kaynak doğrulanamıyorsa, callout ignored ise, transcription current değilse veya parse current değilse yeni onayı reddet. Parse ayrıca `status=parsed` olmalı; `current` freshness tek başına sözdizimsel başarı demek değildir.
3. Revision/parser-version bağı, parse conflict, geometri kimliği, benzersiz hedef/adet ve etkin kontur kontrolleri korunacak. Aynı freshness kuralını farklı kodlarda tutarsız tekrar etme; saf yardımcıları paylaşabilirsin.
4. Eski hedef aynen taşınıyorsa kabul et ve tarihsel bağını koru. İlgisiz bir karar kaydı eski stale target'ı yeniden onaylamasın veya yüzünden bloke olmasın.
5. Bölge değişimi metin snapshot'ını veya parser fixture'ını otomatik current hale getirmesin. Yeni bölgeyi kullanıcı açıkça yeniden okutup kaydetmeden onaya izin verme.

### Kabul

- Yeni probe'daki stale-region hedefi reddedilir; dosya/log/history aynı kalır.
- Yeni onay ve `reconfirm=true` için: region_changed, source_unavailable, ignored, transcription_missing/changed, parser_version_changed, parse_conflict → ret.
- Aynı işlemde region/ignore değişimi ile hedef onayını birleştirmeye çalışmak da bu kontrolü atlayamaz. R-01 ilgili dış mutasyonu daha önce reddediyorsa bu da geçerli rettir; ortak commit yolu kendi son durumunu yine denetler.
- Aynen taşınan stale target + ilgisiz kalınlık/profil değişimi çalışır; hedef kaydı bayt düzeyinde aynı kalır.
- Pozitif kontrol: metni yeni etkin bölgede açıkça tekrar kaydet, güncel revision'a bağlı parse fixture'ı hazırla, yeni hedefi onayla → current, tek gerçek confirm olayı.
- Önceki 2/2 ve 5/5 review scriptleri geçmeye devam eder. Bu iş için gerçek parser yazma.

## 6. G3R-03 — Eski oturumun ilk gerçek yazımında şema damgasını yükselt

**Yer:** `_stamp_callout_version`, save/accept/undo'nun kalıcı yazım sınırı.

### Kanıt

`CALLOUT_SCHEMA_VERSION=2` olmasına rağmen `_stamp_callout_version`, kayıt zaten bir sürüm taşıyorsa hemen dönüyor. `callout_schema_version=1` oturumuna `add_region` ile G3 manual karar yazıldığında sürüm hâlâ 1 kalıyor.

### Yapılacak iş ve kabul

- Desteklenen eski/no-version kayıt, G3 şemasıyla **gerçekten diske yazılırken** geçerli callout sürümüne geçsin.
- Sadece load/public veya no-op save disk rewrite, history, log ya da revision artışı yapmasın. Şema damgası ayrı kullanıcı eylemi değildir.
- v1 oturum: load/public → baytlar aynı; gerçek add/edit/save → sürüm 2. Güncel v2 kayıt v2 kalır.
- Undo karar snapshot'ını geri getirir; oturumun şema sürümünü eski history'den geriye düşürmez. Eski history'de yeni alanların bulunmaması yüklemeyi bozmaz.
- Geometry/detector/parser sürümleri değişmez. Gelecekteki bilinmeyen büyük şemayı sessizce 2'ye düşürme.
- Yeni version bump 3 gerekmez: amaç mevcut v2 sözleşmesini doğru damgalamaktır.

## 7. G3R-04 — Detection sonucu ve nedenleri public/UI'da kaybolmasın

**Yer:** `GuidedStore.public`, `guided.js` içindeki `renderCallouts`; gerekirse `guided.html`.

### Kanıt

`create()` detection metadata/diagnostics'i kaydediyor; `public()` bu alanı döndürmüyor. İlerleme dosyasında döndüğü yazılmış olsa da gerçek çıktı eksik. UI da her boş listeyi “metinsiz çizim normal bir sonuçtur” diye açıklıyor; `source_digest_mismatch` / `invalid_frame` gibi sebepler böyle anlaşılamaz.

### Yapılacak iş ve kabul

- `callout_detection` metadata'sını public yanıtta sun. Eski kayıt için açık boş/yok davranışı tanımla; çalışmamış detector için sahte başarı/diagnostic üretme.
- `no_text_observations` normal boş sonucu ile invalid frame, unsupported page, source mismatch gibi aday üretilememesini ayır. UI kullanıcıya kısa, anlaşılır neden göstersin; bütün iç alanları teknik dump olarak göstermesi gerekmez.
- Metadata bulunmayan eski oturumda sadece “Aday bulunmuyor; eski kayıtta tespit bilgisi yok” gibi dürüst açıklama kullan. Metinsiz olduğu sonucunu çıkarma.
- Var olan adaylar uyarıyla birlikte gösterilebilsin. Diagnostic göstermek manual/transcription/parse/target kararı, revision veya log üretmesin.
- Normal boş çizimde manuel alan çizimi çalışmaya devam etsin. Kaynak/geometry stale için mevcut güvenlik kapılarını gevşetme.
- Testler: normal aday, no_text_observations, source_digest_mismatch ve metadata'sız eski oturum. Public metadata round-trip ve UI metni doğrulansın.

## 8. Uygulama sırası ve küçük geçiş kapıları

| Sıra | İş | Tamamlanmadan sonraki bağımlı işe geçme |
|---|---|---|
| 0 | Başlangıç kaydı + mevcut hataları tekrar | HEAD/diff kaydı; yeni scriptin yedi ihlali ve HTTP bypass kanıtı anlaşılmış |
| 1 | G3R-01 | Store/API sınır testleri, legacy taşıma/[]/undo/no-op testleri yeşil |
| 2 | G3R-02 | Stale yeni hedef/reconfirm ret; pozitif güncel onay; eski iki review scripti yeşil |
| 3 | G3R-03 | v1/v2, read/no-op, gerçek write ve undo sürüm testleri yeşil |
| 4 | G3R-04 | Public diagnostics ve boş/eski/hatalı detector UI senaryoları yeşil |
| 5 | Birleşik test + tarayıcı + teslim | Aşağıdaki kapıların hepsi gerçek kanıtla kapalı |

Her satır için işin başında en küçük ilgili test kümesini kullan. Son birleşik koşu geçince gerekçe olmadan bütün testleri tekrar tekrar çalıştırma.

## 9. Son doğrulama

### 9.1 Kalıcı regresyonlar ve bağımsız tekrarlar

Mevcut `tests/test_guided_callout_review.py` ve `tests/test_guided_callouts.py` dosyalarını genişlet; API için mevcut ephemeral localhost test desenini kullan. Gerekirse küçük bir HTTP test dosyası ekle. **Sadece `store.edit_callout()` çağırmak HTTP testi değildir.**

```sh
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g3-independent-review/review_probes.py
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g3-independent-review/http_review_probes.py
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g1-review/review_probes.py
PYTHONPATH=src .venv/bin/python eval/audits/20261006-guided-g2-review/review_probes.py
```

Dördünün de exit 0 olması gerekir. Çıktıları yeni `*-after.json` / log yollarında sakla. Probe beklentisini sadece mevcut yanlış kod yeşil görünsün diye değiştirme. Yeni fixture yapısı gerekiyorsa aynı invariant'ı ve önceki kanıtı koruyarak gerekçeyi kaydet.

Birleşik mevcut küme (yeni test dosyası eklediysen ayrıca komuta kat):

```sh
.venv/bin/python -m pytest -q \
  tests/test_guided_callout_review.py tests/test_callout_candidates.py \
  tests/test_guided_callout_candidates.py tests/test_callout_models.py \
  tests/test_guided_callouts.py tests/test_guided.py \
  tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py \
  tests/test_guided_proposals.py tests/test_binding_end_meaning.py \
  tests/test_guided_html.py tests/test_view_decision.py tests/test_view_core.py \
  tests/test_sheet_frame.py tests/test_stable_identities.py tests/test_contour_fix.py \
  tests/test_measure_meaning.py tests/test_user_dimensions.py
```

Baseline 285'tir; eklenen gerçek regresyonlar toplamı artıracaktır. Toplamı önceden uydurma. Loga gerçek komut/exit code/sayı/süre yaz. Localhost izin engeli varsa bunu ürün hatasından ayır ve izinli yerel ortamda ilgili HTTP testini yeniden doğrula. `git diff --check` temiz olmalı.

### 9.2 Gerçek tarayıcı kabulü

Gerçek `/guided` sayfasında ve test için ayrılmış oturumlarda:

1. Mevcut PDF aç → aday seç/crop → metin kaydet → reload → aynı metin. Seçim ve taslak koruması çalışır.
2. Manuel alan ekle → metin yaz → alanı değiştir → “Alan değişti” → aynı metni açıkça yeniden kaydet → güncel metin; parser çalıştı iddiası yok.
3. Ignore → yok sayılanları göster → restore → undo. Eski full-save kullanan kalınlık/profil işlemleri callout kararlarını bozmaz.
4. Kaydedilmemiş taslak + revision conflict → hata görünür, metin durur, güncel state sonrası tekrar kayıt çalışır.
5. Normal boş detection, hata nedeniyle boş detection ve metadata'sız eski kayıt doğru açıklanır. Bu özel durumlar açık test fixture'ı olabilir; gerçek detector bu sonucu üretti diye sunma.
6. Dar/geniş görünümde seçim/crop ve bir eski guided kontrolü smoke testinden geçer. Yeni UI metinlerinde HTML çalıştırma yok.

HTTP ret kanıtını UI senaryosu yerine sayma. Sonuçları gerçekten yürütülen adım sayısıyla, console/network hataları ve screenshot yollarıyla kaydet. G4/G7 yokken callout metninin STEP'e uygulandığını söyleme.

## 10. Teslim ve ilerleme kaydı

`docs/GUIDED_PROGRESS.md` ve `report.md` güncel özetlerinde:

- Şimdiki başlangıç HEAD'i `2cdb4d0`. Eski “G3 commit edilmedi / HEAD ff97295” ifadeleri artık current olmamalı. Geçmiş teslim metnini tarihsel kayıt olarak koru; yeni bölümle düzelt.
- Eski rapordaki 25/25 ile logdaki 28/28 ayrımını düzelt. Yeni koşunun sayısını eskisinin yerine uydurma.
- `public callout_detection` ve “HTTP testleri” iddialarını gerçekten yapılan değişiklik/test adlarıyla eşleştir.
- G3R-01–04 için: değişen davranış, dosyalar, regresyon adı, komut, gerçek exit code ve kanıt yolu.
- Yeni yedi store/public kontrolü, HTTP bypass kontrolü, önceki 2/2 ve 5/5 kontrollerin son durumu.
- Seçili test kümesi sonucu, gerçek tarayıcı sonucu, bilinen ilgisiz planner failure'ı; tam takım koşulmadıysa bunu açıkça yaz.
- Gerçek commit/worktree durumu; commit yoksa “yok”. Commit içindeki rapora imkânsız bir kendi-commit hash'i yazmaya çalışma; test edilen başlangıç/çalışma ağacı ve commit sonrası teslim bilgisi ayrılabilir.
- Model çağrısı 0; G4+ uygulanmadı. Açık engel varsa başarı tablosunda gizleme.

**Bu görevin bitişi:** G3R-01–04, geriye uyumluluk ve kabul kapıları tamam. Sonraki ürün işi G4 deterministik parser + parse onayıdır; bu dosyada uygulanması istenmiyor. G3 teslimindeki hataları kapatmadan “G4'e hazır” yazma.
