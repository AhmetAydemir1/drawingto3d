# §65 P5 — hedef vaka analizi (exercise-13)

**Durum:** analiz tamamlandı; uygulama (seviye kararları + derleme) sıradaki iş.
**Tarih:** 2026-10-08. HEAD: `c7033de` (G12.5 devir). Kanıt dosyaları: `p5-evidence/`.

## Sözleşme (§65, birebir)

> At least one source-classified `extrude_profile` case that was wrong/blocked in G11 must become:
> STEP produced / STEP reopen / shape_ok / detail_ok / verdict PASS — Only then P5 PASS.

`evaluate_case` ölçütü (`eval/metrics.py`, dondurulmuş): solids=1 + valid + vector (max(1 mm, %2))
+ volume (%25) + cylinders (yalnız **eksik** yarıçap başarısız eder; ±0.5 mm). Bbox sıralı
karşılaştırılır; yarıçap kümesi eksen-bağımsızdır.

## Uygun adaylar (§61: extrude_profile + G11'de yanlış/bloke)

| vaka | G11 blocker | ölçülen yapı (referans STEP, .venv-cad) |
|---|---|---|
| exercise-13-raster | CAD_UNSUPPORTED + EVALUATOR | bbox [290,150,120], vol 2070.268, silindirler {10,12.5,25,30,50} |
| exercise-51-raster | CAD_WRONG (disk) | bbox [245,60,100], vol 471.938 |
| my-part-raster | EVALUATOR + CONSTRAINT | bbox [134,80,50], vol 160.575 |
| drawing-2-vector | CAD_WRONG (seviyeler) | my-part ile aynı parça (vektör) |
| plastic-enclosure-vector | CAD_WRONG (kontur + basamak) | bbox [120.873,25,60.873], vol 23.520, 113 yüz |

## Referans ölçümleri (özet)

- **exercise-13** (z=derinlik): taban plakası z ±50 (100, R25 köşe), göbek Ø100/Ø60 z ±60
  (her yana **10 taşma**), plaka Ø25'ler (y ekseni; x=30/260), payanda Ø25'leri (z ekseni; (90,58)
  ve (90,100) — 42.00 aralık), payanda bantları z ±(26..50) ve ±(13..24) (kademeli), R30 payanda
  tepesi, R10/R30 yayları, R50 göbek dışı. Ön görünüş = master iz (taban + payanda + göbek).
- **exercise-51**: gövde (y 30 kalınlık) + göbek Ø100/Ø50 ×60 + arka iki pim (R15/Ø15, y −30..−20)
  + uç gözü (R15/Ø18, y ±15) + **z-eksenli R16/Ø12 çıkıntı** (dikey detay, (−64,14), 15 boy) +
  Ø50/Ø18/Ø15/Ø12 delikler. Tek-normal DEĞİL (çıkıntı dik).
- **my-part/drawing-2** (rocker): iki Ø40 göbek (z ekseni; boşluklar Ø20/Ø25) + y-ekseni Ø50/Ø30
  silindirleri + web. İki normlu (z göbekler + y silindirler).
- **plastic-enclosure**: 120×60 plağa L basamak + yarıklar; 113 yüz, taslak açılı (0.873 taşma);
  silindirler {1.5,5,6,8}; okuma en parçalı olan.

## Karar: hedef = **exercise-13-raster**

Gerekçe:
1. Yapısı öbür adaylardan **belirgin biçimde sade**: taban + **tek** yükseltilmiş göbek + 5 delik.
2. G11'de **tamamen bloke** (STEP hiç üretilemedi) → P5 "blocked → PASS" hikâyesi en temiz burada.
3. §61 gerekçesi zaten bu okuma: "taban konturu + göbek dairesi aynı (cephe) görünüşte; yükseklikler
   basılı" — G12.5 raster toparlamasının tam hedefi.
4. Gereken op'lar **mevcut GeneralPlan sözlüğünde**: Extrude + Fuse + Cut (general.py;
   `compile_general` beş op'u da icra ediyor — `geo.fuse` dahil).

## Üretim reçetesi (mevcut op'larla; ürün çerçevesi: profil XY, ekstrüzyon Z)

Değerler üretimde çizimden bağlanır (aşağıdakiler ölçülen hedef değerler):

```text
base_extrusion : ön iz (taban + payanda + göbek kabaca)      distance = 100   (z ±50)
boss_level     : Ø100 dairesi, offset = -10, distance = 120  → fuse(base)      (z ±60)
payanda kesimi : payanda izi ±(25..50) dışındaki bantlarda CUT (z ±(0..25) çekirdek + kademe)
bore           : Ø60, z'den geçen (offset -10, distance 140) CUT
payanda Ø25×2  : (90,58)/(90,100), z ekseni, CUT
plaka Ø25×2    : (30,z=0)/(260,z=0), **y ekseni** → XZ düzlemli daire taslağı + CUT (eş düzlemli kesim)
fuse           : base + boss_level
```

(§35 "tek profil + sabit kalınlık" sözleşmesi taban ekstrüzyonu için geçerli; seviye/fuse adımı
planın 2276. satırındaki "mevcut generic CAD operations" ifadesinin kapsamında.)

## Açık boşluklar (P5'i kapatmak için)

1. **Okuma — ön iz kapanmıyor (ham durum):** 47 profil; en büyük ön-görünüş adayı `outline_1`
   (2 çizgi + 11 yay, alan 150657 px², join_max 38.2). §63 denetiminde `closed:false` **ham** durumdur:
   denetimin kapanış ölçütü 0.5 px (`contour_audit.TOLERANCE_PX`), ürün yolu ise `correct_profile`
   ile join'leri ≤40 px (`RASTER_JOIN_TOLERANCE_PX`) toleransla kapatır. Asıl ölçüt: `make_plan`'in
   düzeltme **sonrası** denetimi (guided.py:1231) + ürün akışının kendi readiness/build sonucu.
   Bu turda `g125_ex13_flow` probe'u (create → önerileri onayla → build) koşuldu; sonucu aşağıdaki
   **Ek** bölümünde. Kalan sınıf: düzeltme sonrası
   self-intersection (kendine değen profil).
2. **Okuma — daireler eksik + bir sahte:** okuma 4 daire buldu: g249/g250 (üst görünüş Ø25'ler,
   gerçek), g252 (ön görünüş alt Ø25, gerçek), **g251 = SAHTE** — "Ø60.00" etiketindeki "60"
   glyph'inin halkası (r=17.9 px, metin üstünde; `p5-evidence/ex13-circles-marked.png`).
   Not: `raster.py:196–220` `_verified_circles` zaten bir **glyph kapısı** taşıyor ("a circle living
   inside a word box is a glyph", satır 210) — g251 bu kapıdan geçmiş; önce geçiş nedenini ölç
   (kutu dışına taşan halka? kutu henüz yokken mi doğrulandı?), sonra §64 uyarınca örnek-bağımsız
   genel kural ekle.
   Eksikler: göbek R50 (Ø100) ve bore Ø60 (her ikisi de yay/dimension çizgileriyle bölünmüş),
   üst Ø25 (R30 yayına karışmış).
3. **Karar modeli — "seviye/yükseltilmiş özellik" yok:** `Decisions` (guided.py:155) yalnız
   calibration/profile/thickness/holes/bindings/... içeriyor; yükseltilmiş silindirik seviye
   (göbek) ve eş düzlemli (XZ) kesim kararı yok. `compile_extrude_plan` tek ekstrüzyon + delik.
4. **Kabul koşumu yok:** P5 için source-only produce → evaluator PASS koşumu (mevcut kabul
   betikleri deseni: `20261007-g12r-strategy-plate/g12r_strategy_plate_acceptance.py`).

## Sonraki adımlar (sıralı)

1. Ön iz kapanışı: `outline_1` üzerinde kalan self-intersection sınıfını ölç (hangi primitif
   çifti, ne kadar) — §63 denetimini vaka-özel noktaya indir; çözüm genel olmalı (§64: örnek-adlı
   tolerans yasak).
2. Daire tespiti: metin-glyph sahtesini ele (g251) + bölünmüş daireleri (R50/Ø60/üst Ø25) kurtar
   (mevcut arc-fit mi, yeni mı). Çözüm genel: "metin kutusu içine düşen daire" gibi kural
   örnek-bağımsız olmalı.
3. `Decisions` + `compile_extrude_plan` genişletmesi: yükseltilmiş seviye (daire → basılı yükseklik)
   + XZ kesim; TDD (RED → GREEN), mevcut op sözlüğüyle.
4. ex13 source-only üretim + evaluator PASS kabulü; `pytest-relevant`/`pytest-broad` güncelle;
   README/g12_progress hizala; commit.

## Bu turda değişmeyenler

- `eval/metrics.py`, dondurulmuş manifest ve tarihsel G9/G11 kanıtları: **değişmedi**.
- Kod değişikliği **yok** — bu dosya + `p5-evidence/` yalnız ölçüm/analiz kaydıdır.

## Ek — ürün akışı probe'u (`g125_ex13_flow`, bu tur, ham günlük `p5-evidence/`)

Taze oturumla ex13 akışı koşuldu (create → accept-all → build; betik: `g125_ex13_flow.py`):

- `create` (PNG oturumu): **1249,6 s** — pafta okuması + aday tespiti + segmentasyon ağır.
- `archetype: unknown` — ürünün kendi cümlesi: *"ne kapalı parça konturu ne de eş merkezli
  çap yığını okunabildi"*.
- **`proposals: 0`** — okuma hiçbir şey öneremiyor; `accept` bu yüzden reddedildi
  ("bu çizim için onaylanacak öneri yok").
- `readiness`: `ready:false` — 3 × `missing_transcription` (callout kararları; kullanıcı işi).
- `build`: readiness kapısında reddedildi — strateji/profil aşamasına hiç gelinmedi.
- Okuma kaydı: "Okuma 8 basılı ölçüyü geometriye bağladı."

**Yorum:** P5'in önündeki gerçek sıra: (1) ön iz **kapalı parça konturu** olarak okunmalı —
archetype + öneriler (profil/kalibrasyon/kalınlık) ancak ondan sonra doğuyor; bu, yukarıdaki
boşluk #1'i ürünün kendi cümlesiyle doğruluyor. (2) Callout çözümleri kullanıcı işidir (G11
akışında da 32 aday `not_model_input` işaretlenmişti) — blocker değil. (3) Build yolu: strateji
(`extrude_profile`) + seviye kararları + derleme.
