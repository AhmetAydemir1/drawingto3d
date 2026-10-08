# G12.5 — raster extrude recovery (PLAN-25 §61–§64) — ara durum (WIP)

Bu dizin G12.5'in bu ana kadarki kanıtıdır. Faz **kapanmadı**: cephe dış hattı rasterda hâlâ
kapanmıyor (yay-yürüyüş yönü hatası; aşağıda) ve §65 P5 kapısı (G11'de yanlış/bloklu bir
`extrude_profile` vakanın STEP üretip verdict PASS olması) henüz koşulmadı. Bu commit bir
ilerleme kaydıdır; PASS iddiası içermez.

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
flange: —→44 (survey yalnız dört vakayı kapsadı). Kapanma kapsamı genişledi ama **en büyük
halka 5/5 vakada kapalı değil** (örneklenen 12 profil içinde kapalı sayısı: 6/5/0/7/2). 51'de
en büyük tel `outline_23` (252 nokta): 278,77 px'lik sahte ek g445→g68 — yay **ayna taraftan**
yürünmüş (hayalet uç [2260,216]); bu bir tolerans sorunu değil, yay-yürüyüş yönü mantığı —
sıradaki düzeltme hedefi. Menü kalabalığı endişesi sayı olarak inmedi
(48/64/31/33/44); sahte birleşmeler yok edildi, ana hat kapanması açık.

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
- `pytest-relevant.log` — ilgili süit: **730 passed / 20:48 / EXIT=0** (730 toplandı — raster,
  observe, proposal, chain + contour denetimleri + g12/g11/guided/callout aileleri).
- `pytest-broad.log` — geniş regresyon (`pytest -q tests -k "not semread"`): **1593 passed, 339 deselected / 31:16 / EXIT=0**
- `tests/test_g12_raster_profile.py` (3/3, RED→GREEN): (1) köşelerinde 30 px gerçek aralık olan
  kontur kapanır; (2) ~141 px teğet sıçramasıyla "kapanan" şekil kapalı sayılmaz; (3) sentetik
  aralıklı pafta 1/2/3/5/30 px'te kapalı kontur sunar (ürün yolu: observe → drawing_options).
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
1. **Yay-yürüyüş yönü**: `outline_23`'ün 278,77 px sahte eki (g445→g68) — yayın ayna taraftan
   yürünmesi; hayalet uç [2260,216]. Cephe dış hattının kapanması buna bağlı.
2. **§65 P5 kapısı**: kaynak-sınıflanmış, G11'de yanlış/bloklu bir `extrude_profile` vaka
   üretimden geçip (STEP + reopen + `shape_ok` + `detail_ok` + verdict PASS) olmalı.
3. Menü kalabalığı: kapanma düzeltmesinden sonra yeniden ölçülecek (sayı 45–64 bandında).
