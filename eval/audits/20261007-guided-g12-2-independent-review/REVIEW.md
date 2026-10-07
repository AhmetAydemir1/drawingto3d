# G12.1–G12.2 bağımsız inceleme

İncelenen HEAD: `f8d32f4a9f5363a7dc3f120f64df570be730abb0`.
Karşılaştırma: `cc36f8d..f8d32f4`. Ürün değişikliği son olarak `4592275`; kabul kanıtları `190a065`.

**Sonuç: G12.2 tam kabul için hazır değil. Beş düzeltilebilir bulgu var.** Ürün/test/plan dosyaları değiştirilmedi; bu dizinde bağımsız kanıtlar oluşturuldu. G12.3 uygulanmadı.

## G12R-01 · P1 — Strateji seçildikten sonra normal tarayıcı kayıtları reddediliyor

Yer: `src/drawingto3d/guided.py:1846–1874` (`_strategy_fingerprint`, `_refuse_forged_strategy`).

Strateji eşitliği `BuildStrategyDecision.model_dump_json()` dizgisi üzerinden karşılaştırılıyor. `evidence: list[dict]` içindeki sayılar tiplendirilmediğinden sunucunun `10.0` kalınlık kanıtı tarayıcının JSON turunda `10` olur; aynı karar farklı dizgi sayılır. Sahte strateji koruması normal kaydı reddeder.

Bağımsız gerçek tarayıcı tekrarı:

1. Geçici oturumda kalınlık 10; oluşturma biçimi seçilmemiş: build kapalı.
2. “Sabit kalınlıklı profili uzat” seçildi ve kaydedildi: build açıldı.
3. Kalınlık 20 yapılıp “Kalınlığı kaydet” tıklandı.
4. Sunucu `oluşturma biçimi yalnız set_build_strategy komutuyla yazılır; istemci strategy_key/geometry_version uyduramaz` hatası verdi. Değişiklik kaydolmadı.

Store tekrarı da bunu doğruluyor: strateji nesneleri Python yapısal eşitliğiyle **eşit**, yalnız kanıt sayısı `10.0 → 10`; `save` reddediliyor ve kalınlık 10 kalıyor. Aynı tam karar yükünü gönderen profil/kalibrasyon/delik gibi normal kayıt yolları da bu karşılaştırmadan geçiyor.

Düzeltme: sahte/değiştirilmiş strateji reddini koruyarak anlamsal JSON eşitliği kullan; integral float/int ve nesne anahtar sırası aynı kararı farklı yapmamalı. Gerçek tarayıcıda strateji onayından **sonra** normal kayıt, profil değişince stale ve yeniden onay akışlarını doğrula.

Kanıt: `probes.json` → `browser_json_roundtrip_rejected`; `ui-save-refused-dom.txt`, `ui-save-refused.png`.

## G12R-02 · P1 — Redundant onayı metin/bölge/dayanak değişince hâlâ kapsamı kapatıyor

Yer: `src/drawingto3d/callout_readiness.py:117–141`; `DECISION_REFS` (53–63).

`redundant` dalı, kendi callout'unun stale kontrolünden önce sonuçlanıyor. `decision:thickness` gibi dayanaklarda yalnız alanın varlığı denetleniyor; onaylanan değer veya sürüm pinlenmiyor.

Üç ayrı değişiklikle gerçek Store üzerinden tekrarlandı:

- `10.00` callout'u `decision:thickness` ile temsil ediliyor diye onayla; kalınlığı 10 → 20 değiştir. `ready=true`, `coverage_complete=true`; GeneralPlan kalınlığı 20.
- Callout metnini `30.00` yap. Eski redundant onayı sürüyor; yeni kapsam onayı olmadan hâlâ hazır.
- Bölgeyi başka yere taşı. Public transcription/parse `stale / region_changed` olduğu halde coverage `redundant`, readiness yine `true`.

Gerçek tarayıcıda metin değişimi de tekrarlandı: `30.00` kaydedildiğinde satır “Zaten temsil ediliyor”, kontrol listesi “Tüm gerekli bilgiler tamamlandı” ve build düğmesi açık kaldı. Bu UI tekrarında kalınlık 10 kaldı; önceki kalınlık değişimi R-01 nedeniyle reddedilmişti.

Düzeltme: kapsam onayını kendi metin/bölge bağlamına ve dayanağın onaylanan değerine/kimliğine bağla. Değişince tekrar onay iste; yalnız varlık kontrolü yeterli değil. Yeni onay, undo/reopen ve başka callout'a dayanan zincirler için regresyon ekle.

Kanıt: `probes.json` ilk üç kayıt; `ui-stale-redundant-dom.txt`, `ui-stale-redundant.png`.

## G12R-03 · P1 — Plate kabul betiği kalan bütün callout'ları otomatik kapatıyor

Yer: `eval/audits/20261007-g12-strategy-plate/g12_strategy_plate_acceptance.py:209–220`, `_reason_for`.

Betik reçetede karara bağlanmamış bütün kimlikleri `remaining` içine alıp hepsine `not_model_input` yazıyor. `_reason_for` tanımadığı metne de varsayılan gerekçe dönüyor. İşlemi tek tek yapmak, “kalanları otomatik kapatma” davranışını ortadan kaldırmıyor.

Betikten **aynı AST bloğu** alınarak sahte Store/karar kaydediciyle çalıştırıldı: reçetede olmayan `NEW REAL DIMENSION 123.45` satırı otomatik `not_model_input` oldu. Gerçek kabul kaydı bu yolla 36 satır kapatıldığını söylüyor. O koşudaki 36 metnin hepsi tanımlı gruplarda; inceleme bunların mutlaka yanlış dışlandığını iddia etmiyor. Bulgu, yeni/beklenmeyen bir gerçek ölçünün de sessizce elenmesi ve bu yolun “örtük kapatma yok” kanıtı sunmasıdır.

Düzeltme: önceden açıkça yazılmış kaynak temelli karar listesi kullan. Listede olmayan satır açık kalsın; beklenmeyen kimlik/metin kabulü durdursun. Mevcut kanıtları koruyup yeni taze Plate + tarayıcı kabulünü ayrı dizine yaz.

Kanıt: `probes.json` → `acceptance_unknown_leftover`; mevcut kabul JSON'unda adım `1b`.

## G12R-04 · P1 — Producer'ın varsayılan sürücüsü referans sınırını ve tur ayrımını atlıyor

Yer: `eval/g12_runner/produce_case.py:37`, sürücü çağrısı 109–123.

`DEFAULT_DRIVER` hâlâ G11 koşucusu. Bu koşucu `G12_PRODUCER_INPUT` ve `G12_ROUND_DIR` kullanmıyor; tam manifesti kendi okuyor, `reference_identifier_evaluator_only` alanına erişiyor ve evaluator'ı kendisi başlatıyor. Kendi `--round` argümanı verilmezse tarihsel G11 `cases/` dizinine yazıyor. Wrapper'ın `--round` argümanı yalnız ortam değişkeni olarak iletiliyor.

Dolayısıyla belgelenen varsayılan `produce_case.py --case … --round … --recipe …` yolu kaynak-only producer sözleşmesini sağlamıyor. V2 reçetesi verilirse eski şemada ayrıca başarısız olur; eski şemaya uygun reçete verilirse G11 yoluna girer. Açıkça `--driver .../g12_runner.py` kullanan yol bu özel varsayılan hatadan etkilenmez.

Düzeltme: varsayılanı yeni kaynak-only sürücü yap veya sürücü seçimini zorunlu kılıp eski G11 sürücüsünü G12 producer yolunda reddet. Varsayılan gerçek komutu test et; producer referans/evaluator okumamalı, yalnız istenen tur dizinine yazmalı. Tarihsel G11 koşucusunu değiştirme.

Kanıt: `probes.json` → `producer_default` ve statik çağrı zinciri. Riskli eski koşucu çalıştırılmadı; eski sonuçlar üzerine yazılmadı.

## G12R-05 · P2 — V2 reçete uygulanmayan dolu karar alanlarını sessizce kabul ediyor

Yer: `eval/g12_runner/recipe_v2.py:96–111`; `g12_runner.py:92,130–147`.

Şema dolu `profile_actions`, `view_decisions`, `strategy_decision`, `dimension_bindings`, `feature_links` kabul ediyor. `planned_actions()` ve `run_recipe()` yalnız `callout_actions` işliyor. Örneğin `profile_actions=[{"profile_id":"outline_1"}]` ve `strategy_decision={"kind":"extrude_profile"}` doğrulanıyor ama **sıfır istek** üretiyor. Taze oturumda bu kararlar uygulanmaz; reçetenin istenen yolu denenmeden eksik karar blokajı kaydedilir.

Düzeltme: henüz desteklenmeyen dolu alanları oturum açılmadan açık hatayla reddet veya uçtan uca uygula. Boş/null gelecek-faz alanları kalabilir. Strateji alanı uygulanacaksa mevcut `/api/guided/strategy` sözleşmesini kullan. Bu aşamada gelecek CAD kabiliyetlerini eklemek gerekmez.

Kanıt: `probes.json` → `unapplied_recipe_fields`. Bu kayıt ayrıca `notes` içindeki `.STEP` yolunun şemadan geçtiğini gösteriyor; referans içerik denetimi de sertleştirilmeli, fakat bu ayrı bir numaralı kabul bulgusu olarak sayılmadı.

## Bağımsız doğrulama ve sınırlar

- Güncel HEAD test komutu:
  `.venv/bin/python -m pytest -q tests/test_build_strategy.py tests/test_callout*.py tests/test_guided*.py tests/test_g11*.py tests/test_g12*.py`
  → **589 passed / 161.99 s / exit 0** (`regression.log`). Yerel HTTP gerektiren testlere sandbox dışı çalıştırma izni verildi. Bu testler yukarıdaki köşe durumlarını kapsamıyor.
- Kayıtlı G12.2 Plate STEP'i donmuş `plate_regression.py` ile tekrar açılıp ölçüldü → **9/9 PASS / exit 0** (`plate-verdict.json`, `plate-evaluate.log`). 120.011 × 80.002 × 15; dört delik ve bir cep doğrulandı. Bu, dosyanın geometrisinin doğruluğudur; R-03'teki kabul yönteminin doğruluğu değildir.
- Gerçek in-app browser, güncel ürün JS/HTML + geçici gerçek `app.Handler/GuidedStore`: stratejisiz build kapalı, açık stratejiyle açılıyor; R-01 ve metin değişimiyle R-02 tekrarlandı. `ui-results.json` ve DOM/screenshot kanıtları saklandı. Test sekmesi ve sunucu kapatıldı.
- Yeni bulgu tekrarı: `.venv/bin/python eval/audits/20261007-guided-g12-2-independent-review/probes.py`. Script ürün dosyası/gerçek oturum değiştirmez; geçici Store ve saf sınıflandırma bloğu kullanır. Çıkış 0, sorunların gözlenebildiği anlamındadır; ürün kabulü anlamına gelmez.
- `git diff --check` temiz. `cc36f8d..HEAD` içinde frozen manifest, `eval/metrics.py`, tarihsel G9 ve G11 dizinleri değişmemiş.
- 1543 testlik geniş paketin önceki log'u okundu, bağımsız yeniden çalıştırılmadı. On paftanın uzun ingestion koşusu ve taze tam Plate üretimi bu incelemede yeniden yapılmadı.
- G11 ana başarı oranı hâlâ **1/9**. G12.2 için söylenen 10/10, Plate kabul adımlarının sayısı; 10 paftanın doğru STEP ürettiği anlamına gelmiyor.

## Hermes'e sonraki görev

Önce G12R-01–05 düzeltme turu; G12.3'e geçmeden ilgili kabulü yenile. Her bulgu için önce başarısız regresyon, sonra generic düzeltme; G12R-01/02 için gerçek tarayıcı tekrarları, R-03/04/05 için gerçek üretici giriş yolunun sınır ve kayıt testleri. Frozen manifest/evaluator ve eski kanıtlar korunacak. Taze Plate çıktısı, ayrı tur kanıtları ve mevcut ilgili regresyon setiyle teslim et.

![Metin değişmesine rağmen eski kapsam onayı ve hazır durumu](/Users/aydemir/Desktop/drawingto3d/eval/audits/20261007-guided-g12-2-independent-review/ui-stale-redundant.png)
