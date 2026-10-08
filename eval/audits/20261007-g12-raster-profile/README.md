# G12.5 — raster extrude recovery (PLAN-25 §61–§64) — ara durum (WIP)

Bu dizin G12.5'in bu ana kadarki kanıtıdır. Faz **kapanmadı**: §65 P5 kapısı henüz koşulmadı.
Bu commit bir ilerleme kaydıdır; PASS iddiası içermez. §65 için hedef vaka analizi eklendi
(`p5-analysis.md` + `p5-evidence/`): hedef **exercise-13-raster**; yapı referanstan ölçüldü
(taban + tek yükseltilmiş göbek + 5 delik); gereken op'lar mevcut GeneralPlan sözlüğünde
(extrude/fuse/cut); kalan boşluklar ön iz kapanış sınıfı + daire tespiti + seviye karar/derleme
katmanıdır.

## Ne değişti (§64 — ölçüme dayalı; örnek-başına tolerans ayarı YOK)
- `RASTER_JOIN_TOLERANCE_PX` **20 → 40**: zincir izinde (Exercise_51) paftanın kendi ekleri
  1,6–37 px; 20 px zarfı cephe konturunu parçalı bırakıyordu (~40 px ≈ bu paftalarda ~2,5 mm).
- Yeni `CORNER_JOIN_REACH_PX = 48`: köşe/yay kuralları yalnız paylaşılan mürekkep eriminde
  (satır taşması ~30 px + yay kırpması ~10 px ölçeği) çalışır; kapı hem `gap` hem `meet`
  mesafesine uygulanır ve kapanış varyantlarını da bağlar. 100+ px uzaktaki parça artık
  "köşe" sayılmaz.
- `guided._trace`: `mid_join_px = RASTER_JOIN_TOLERANCE_PX` — zincir (proposal) ve iz (guided)
  aynı zarfta anlaşır. Önceden iz, zincirin 28,6 px'te kapattığı sentetik teli 20 px'lik
  yarı-çapla geri atıyordu (iki aşama farklı zarflardaydı).
- Elenen hipotez (kayıt): "kalınlık ayrımı" — ölçüm tüm çizgilerin 2–2,8 px olduğunu gösterdi;
  kod değişikliğine dönüşmedi.

## Ölçüm — Exercise_51 zincir izi (`chain-trace-before.log` → `chain-trace-after.log`)
İz, geçici yerel enstrümantasyonla alındı (D2D_TRACE_LOOPS); ürün kodunda 0 referans kaldı.

| ölçü | önce | sonra |
|---|---|---|
| alınan adım | 962 | 922 |
| >100 px sıçramayla alınan adım | **222** (en büyük 1965,7 px) | **0** (en büyük 53,8 px) |
| ≥48 px adım | 318 | 20 (hepsi ≤ 53,8 = erim 48 + ceza 8) |
| ölü uç | 223 | 211 |
| kapanan döngü | 56 | 58 |

## Menü / kapanma (§63 denetimi, 5 raster vaka)
`raster_contour_audit.py` → `contour-audit.json` (vaka başına en büyük 12 profil; kalan sayısı
`truncated_profiles`): profil sayıları 51: 16→48 · 17: 26→64 · 13: 19→31 · my-part: 24→33 ·
flange: —→44 (survey yalnız dört vakayı kapsadı; sayılar tolerans turu sonrası). **Yay-yürüyüş
düzeltmesinden sonra: 60/77/47/45/65** (aynı denetim, aynı okumalar). Kapanma kapsamı genişledi
ama **en büyük halka 5/5 vakada kapalı değil** (örneklenen 12 profil içinde kapalı sayısı: yay
düzeltmesi öncesi 6/5/0/7/2 → sonrası 2/0/0/2/0 — örneklem nokta sayısına göre seçildiğinden
büyük konturları izler; **tüm wire'lar üzerinde** kapalı sayısı 50 → 74). 51'in en büyük teli
`outline_23` tolerans turunda 278,77 px'lik sahte ek taşıyordu — o ek yay düzeltmesiyle yok
edildi (aşağıda).

## Ek tur (aynı gün) — yay-yürüyüş yönü düzeltmesi
Zincir g445'e **b ucundan** giriyor; iz, "hangi uçtan girildi?" kıstasını 90°'lik bir pencereyle
soruyordu ve 61°'lik yayda **iki uç birden** pencereye düşünce giriş hep "a'dan" sayılıyordu →
süpürme ters çevrilip yay b→b+δ **ayna** yayı olarak çiziliyordu (hayalet uç [2260,216]; sonraki
parçanın başlangıcı 278,77 px sürükleniyordu). Kıstas **en yakın uç** karşılaştırmasına çevrildi
(`to_a ≤ to_b`); sözleşme aynı kalır (§23-C14: işaretli süpürme; süpürmenin işaretini giriş ucu
belirler) — yalnız pencere kaynaklı yanlış sınıflama düzeldi. Yeni test:
`test_an_arc_walked_in_from_its_far_end_keeps_the_ink_not_the_mirror` (RED: 273,7 px ayna
noktası → GREEN).

**A/B ölçümü (aynı gözlem önbellekleri, tüm wire'lar; `arc-direction-before.json` /
`arc-direction-after.json` / `arc-direction-ab.log`):**

| vaka | wire | kapalı | join_max > 100 px |
|---|---|---|---|
| exercise-51 | 44 → 56 | 13 → 18 | 2 → 0 |
| exercise-17 | 61 → 74 | 18 → 22 | 3 → 1 |
| exercise-13 | 27 → 43 | 2 → 4 | 5 → 0 |
| my-part | 27 → 39 | 7 → 9 | 2 → 2 |
| flange | 42 → 63 | 10 → 21 | 5 → 1 |
| **toplam** | 201 → 275 | **50 → 74** | **17 → 4** |

- `outline_23`: join_max **278,77 → 38,23**; nokta kutusu [2350,3 … 3070,1] × [314,6 … 824,5] —
  hayalet uç 51'in menüsünden tamamen düştü.
- 5 küçük kontur "kapalı → dürüst-kapalı-değil" döndü: eski "kapalı" durumları 42–187 px'lik
  zorlama-taşımalarla geliyordu; yeni geometri doğru ve ekler 6–34 px, ama küçük bir örtüşme
  (self-intersection) denetimi kapatıyor — sıradaki iş.
- Kalan self-intersection'ların çoğu, kapsamdaki konturların zincirce uç uca eklenmiş
  parçalarının kesiştiği yerler (ör. g388'in ucu g445'in halkasına ~3,6 px giriyor) — zincir
  kalitesi sınıfı.

### Ek turun ikinci yüzü — flange paftası (`10/Exercise 12`)
İlgili süit bu düzeltmeyle iki kırmızı verdi (flange akışı; `KeyError: 'thickness'` + build hazırlık
kapısı). Kök: düzeltme vektör yay `g151`'in **~186 px hayalet uzantısını** da kaldırdı → paftanın
izlenen `outline_2` profili okumanın kendi ana hattıyla eşleşti (209,32×279,28 ≈ 209,32×278,49) →
`_transform` devreye girdi → `resolve_claim` artık **reading çerçevesini** kullanıyor; o dal yalnız
`distance`/`projected` modu ürettiğinden eksen kararı ("x"/"y") kayboluyor ve `_identity_candidates`
üç Ø20,00 satırını hizasız sanıp kalınlık önerisi düşüyordu. Reading dalı artık eksen kararını da
üretiyor (en küçük hata: distance/x/y) — ama bir kapıyla: eksen modu yalnız satır gerçekten o eksen
boyunca çizikliyse geçerli (karşı bileşen span'ın yarısını aşamaz; çapraz bir satırın span eşleşmesi
tesadüftür) → flange'in üç Ø20,00 satırı yeniden hizalı (kalınlık 20,0) ve `5/Plate With A Pocket`'in
8 mm'lik çapraz derinlik satırı yerinde kalıyor (plate süiti 9 öneri). 10 mm'lik rim satırı da
reading çerçevesinde %0,58'le uyuştuğu için ölçek adayı olarak sunuluyor — accept'in bağladığı
karar yine yüzün kendi **Ø270'i** (`t0`; `flange-flow-before.log` / `flange-flow-after.log`).

## §61/§62 — sınıflandırma
`cluster-classification.json`: manifestin 10 vakası YALNIZ kaynak çizimden sınıflandırıldı
(6 alan: `case_id`, `source_observed_views`, `source_observed_geometry_style`,
`proposed_strategy_class`, `current_blocker`, `basis`; etiketler §62'nin izinli kümesinden).
Referans STEP/değerlendirici verisi kullanılmadı; üretim bu dosyayı okumaz (`src/` içinde
0 referans).

## §63 — kontur denetimi
Her profil için: profile id, view id, primitive ids, closed, self-intersection, join gaps,
movement applied, bbox, area, line count, arc count. `view_id` ve `movement_applied_px` yalnız
çözülmüş oturumda dolar; bu denetim ham okumadır (not JSON'da; G12.3 §46/§48). Denetim bir
tanılama kaydıdır — hiçbir üretim kararı okumaz.

## Kanıt
- `pytest-relevant.log` — ilgili süit: **741 passed / 19:48 / EXIT=0** (raster, observe, proposal,
  chain + contour denetimleri + g12/g11/guided/callout/advise aileleri; yay düzeltmesi + reading
  dalı bu koşunun içinde).
- `pytest-broad.log` — geniş regresyon (`pytest -q tests -k "not semread"`):
  **1596 passed / 339 deselected / 28:59 / EXIT=0**
- `tests/test_g12_raster_profile.py` (4/4, RED→GREEN): (1) köşelerinde 30 px gerçek aralık olan
  kontur kapanır; (2) ~141 px teğet sıçramasıyla "kapanan" şekil kapalı sayılmaz; (3) sentetik
  aralıklı pafta 1/2/3/5/30 px'te kapalı kontur sunar (ürün yolu: observe → drawing_options);
  (4) zincirin `b` ucundan girdiği yayda iz `a` ucunda biter — ayna noktasında değil.
- `tests/test_advise.py` (+2, RED→GREEN): reading dalı eksen kararı —
  `test_a_row_resolved_in_the_readings_frame_keeps_its_axis_decision` (`'distance' == 'y'` → GREEN)
  ve çapraz satır kapısı — `test_a_row_whose_axis_span_is_a_coincidence_is_not_an_axis_row`
  (`'y' == 'projected'` → GREEN).
- `arc-direction-before.json` / `arc-direction-after.json` / `arc-direction-ab.log` — yay-yürüyüş
  yönü düzeltmesinin A/B ölçümü (yukarıdaki tablo).
- `flange-flow-before.log` / `flange-flow-after.log` — `10/Exercise 12` akışının A/B çözüm günlüğü
  (reading çerçevesi + modlar + kalınlık/kalibrasyon önerileri).
- `reference-metrics.log` — referans CAD künyeleri (8 vaka) + G11 üretimlerinin evaluator
  karşılaştırması: 51 → 15×49,978×49,978 (29,4 cm³; ref 60×100×245, 471,9 cm³, %94 fark,
  pass False); flange → 20×30,907×30,907 (15,0 cm³; ref 50×100×100, 202,1 cm³, %93 fark,
  pass False). Bu iki satır §65 P5'in "G11'de yanlış" tabanıdır.
- `reading-survey-before.log` — düzeltme öncesi dört vakanın okuma özeti.

## Dokunulmayan
Dondurulmuş manifest (`eval/guided_10_manifest.json`), `eval/metrics.py` ve tarihsel
G9/G10/G11/G12.0–G12.4 kanıtları değişmedi; ana metrik hâlâ **1/9** (faz kapanmadan ölçüm
tekrarı yok). Bu fazda UI değişmedi (§97/8 gerçek-Chrome kabulü gerekmedi).

## Açık
1. **Eklerdeki küçük örtüşme sınıfı**: 5 kontur, yay düzeltmesi sonrası doğru geometriyle küçük
   self-intersection taşıyor (line-line / arc-arc uç taşması, birkaç px); eski "kapalı" halleri
   42–187 px zorlama-taşımalarla geliyordu (kapanan→bozulan: 13'te 2, flange'te 1, my-part'ta 2).
2. **Zincir kalitesi**: kalan self-intersection'ların çoğu zincirin uç uca eklediği parçaların
   kesişmesi (ör. g388×g445); menü kalabalığı (60/77/47/45/65) bu başlıkla birlikte.
3. **§65 P5 kapısı**: hedef vaka seçildi → **exercise-13-raster** (analiz: `p5-analysis.md` +
   `p5-evidence/`). Gereken üretim reçetesi **mevcut** op'larla yazılabiliyor (base extrude +
   göbek seviyesi fuse + kesimler; `geo.fuse` mevcut); kalan açık işler: (a) ön izde kalan
   self-intersection sınıfı (probe ile doğrulandı: archetype `unknown`, öneri 0; `make_plan`
   denetimi, guided.py:1231), (b) daire
   tespiti — ex13'te g251 glyph sahtesi + eksik Ø60/R50/üst Ø25, (c) `Decisions` +
   `compile_extrude_plan` seviye (yükseltilmiş daire) ve XZ-düzlemli kesim genişletmesi,
   (d) source-only üretim + STEP reopen + `shape_ok` + `detail_ok` + verdict PASS kabulü.
