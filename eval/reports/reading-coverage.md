# Reading coverage: which printed numbers the chain binds, and why the others stay unresolved

One question per file: how many of a sheet's printed numbers the reading chain binds to its own measured
geometry, with each blocker named and measured. Ground truth here is the sheet's own drafting convention
(a dimension is drawn to the number printed on it), never a reference answer.


## 2026-09-27 — row ends re-picked against the sheet's own scale (`bind.py`)

Yorum arayüzü bırakıldı; bu dilim doğrudan **okuma zincirinde** (PLAN §22'nin kayıtlı sıradaki işi).
Ölçüm önce yapıldı: plastik paftada 14 sayının 10'u `unresolved`, ve nedenleri iki ayrı sınıfa düşüyor
(kayıtlı `out/bind` verisi üzerinde ölçüldü):

| sınıf | ölçü | neden |
|---|---|---|
| satır ölçeğe uymuyor | 8 (pdf-2, 6, 8, 9, 10, 11, 12, 13) | çapanın seçtiği satır, basılı değerin pafta ölçeğindeki uzunluğundan %250–1800 sapıyor (ör. 3,00 mm için 70 px seçilmiş, 11,75 px olmalı) |
| uç çifti yok | 2 (pdf-1, pdf-4) | satır doğru, ama bir çapanın aday havuzu boş |

**Tek değişken (`bind.py`):** satır paftanın ölçeğinden %25'ten fazla sapıyorsa, satırın uçları
**çapanın zaten gördüğü noktalar arasından** (kendi konumu, bağlandığı çizgilerin uzak uçları,
hizalandığı adaylar) ölçeğin gerektirdiği uzunluğa en yakın çiftle yeniden seçilir; kabul sınırı %5,
satır zaten uyuyorsa hiç dokunulmaz. Yeni geometri bulunmaz, tolerans gevşetilmez — yalnız *seçim*
değişir ve seçim kendi notunu taşır. Kalibrasyon zaten `scale.audit` ile *konsensüs* olarak
kestiriliyordu; burada onu bir kısıt olarak kullanıyoruz.

**Ölçülen sonuç (aynı çizim, aynı ayarlar; değişiklik `_repick_row_with_calibration` no-op yapılarak
öncesi/sonrası karşılaştırıldı):**

| | öncesi | sonrası |
|---|---|---|
| okumanın bağladığı sayı (anlam katmanı) | **4/14** | **8/14** |
| bağ durumları (bind) | bound 0, partial 4, aligned 9, unbound 1 | bound 1, partial 2, aligned 10, unbound 1 |
| yeniden seçim notu | 0 | 4 (pdf-6, pdf-8, pdf-9, pdf-12) |
| değişmeyen ölçü | — | **10/14** |

- Yeni bağlananlar ve sapmaları: pdf-6 `g95/g94` (9,71 / 10,00), pdf-8 `g68/g268` (3,01 / 3,00),
  pdf-9 `g89/g271` (3,89 / 4,00), pdf-12 `g65/g97` (1,52 / 1,50) — dördü de sözleşmenin sapma
  sınırının içinde ve her biri notunu taşıyor (ör. "satır ölçeğe uymadı (70.0 px, beklenen 11.75 px);
  uçlar çapanın gördüğü noktalardan yeniden seçildi (11.67 px, artık %0.68)").
- **Plaka bayt bayt korundu:** `meaning-3b-05` koşusundaki 8 plaka isteğinin istem özeti bugün de
  birebir aynı (8/8) — satır zaten ölçeğe uyduğu için yeni yol plakada hiç çalışmıyor.
- **Kalan 6:** pdf-1, pdf-4, pdf-5 satırları doğru ama bir çapanın aday havuzu boş (ayrı bir engel,
  sıradaki tek değişken); pdf-10, pdf-11, pdf-13 için çapanın gördüğü noktalar arasında gereken
  uzunlukta çift yok (bu turda bulunamaz).

**Dürüst sınır:** plastik paftada bağımsız etiket yok; "bağlandı" demek "çizili uzunluk basılı değerle
paftanın kendi ölçeğinde uyuşuyor" demek. Bağımsız doğrulama yalnız plakada mümkün ve orada hiçbir şey
değişmedi. Bu yüzden bu dilim *kapsam* kazancı olarak raporlanır, doğruluk kazancı olarak değil.

### How to reproduce the before/after

`bind_page` and `meaning_page` are called twice on the same drawing with
`drawingto3d.bind._repick_row_with_calibration` replaced by a no-op for the second call; the two records
are compared per span (status and resolution). The plate is guarded separately: the eight plate requests
stored in `out/meaning-interpretation/meaning-3b-05/requests/` are re-rendered from today's reading and
their `prompt_sha256` must still match (8/8).

## 2026-09-27 — the ends of the lines a dimension crosses (`meaning.py`), as a fallback only

After the row re-pick, three numbers were still unresolved for a reason that turned out **not** to be the
one on record. The earlier note said "one anchor's candidate pool is empty", but measuring the pools showed
where the emptiness comes from: the geometry that measures these three is the **far end of the lines the
dimension crosses** — the extension lines of the faces being measured — and the meaning layer offered only
what an anchor *reached* (features) or *aligns with*, never what it crosses.

Measured, before writing any code:

| knob tried | effect on pdf-1 / pdf-4 / pdf-5 |
|---|---|
| `CANDIDATE_LIMIT` 6 → 12 → 100 | **nothing** (0 measuring pairs in all three) — the limit was never the blocker |
| add the far ends of `crossing` strokes | 6 / 5 / 2 measuring pairs, all inside tolerance |
| add `stub` and `row` strokes too | more pairs, but 4 of them use **the dimension line's own ink** — a claim pointing at the very line that printed the number, confirming itself |

So the single variable is: offer the far ends of the **crossed** lines, never the row or the stubs. That alone
re-pointed three already-bound numbers on the second sheet when offered in the first pass (`pdf-3`, `pdf-6`,
`pdf-12` changed ids) and — the guard that decided the design — **broke the plate**: 0/8 stored plate requests
still hashed the same. The plate's numbers already measure their value, so a *wider* first pass rewrites
bindings that already stand. Therefore the crossed ends are offered in a **fallback pass, only when the first
pass finds nothing**: a second chance for the unresolved, never a rewrite of what stands.

Result (same drawing, same settings; before/after by calling the layers with and without the fallback):

| | before | after |
|---|---|---|
| bound numbers | 8/14 | **11/14** |
| changed measurements | — | **3/14** (exactly the three that were unresolved) |
| untouched | — | **11/14** |
| plate: bound numbers | 7/7 | 7/7 |
| plate: stored request hashes | 8/8 | **8/8** |

- Newly bound: `pdf-1` `g289/g290` (9,99 / 10,00), `pdf-4` `g255/g254` (120,50 / 120,00),
  `pdf-5` `g294/g295` (60,31 / 60,00). Each carries a note naming the ids it used, e.g. *"Alışılmış
  adaylarla ölçülemedi; çapanın kestiği çizgilerin uzak uçları da hesaba katılınca bağlandı: g289/g290,
  g1/g290."* One end of a fallback pair may still be a reached candidate (the two can name the same point;
  the reached one wins, and the note lists the ids actually used).
- Unresolved: `pdf-10`, `pdf-11`, `pdf-13` — for these no pair at the required length exists among what the
  anchors reached, align with, or cross.
- Still self-consistency, not correctness: the second sheet has no independent label. The plate is the only
  sheet with one, and there nothing moved.

**Consequence for the interface measurement.** The stored interface runs read the *older* reading (second
sheet: 4 bound). Repeating that round now would be a different experiment, so it gets a new label
(`meaning-3b-06`) rather than overwriting `meaning-3b-05`; `--check` on every stored evidence pack still
reports 0 problems.

## 2026-09-27 — a step dimensioned by its own segment (`bind.py`)

The two numbers left after the fallback pass (`pdf-11` 4,00 and `pdf-13` 1,50) were measured again, and the
record was wrong a second time about *why*: their anchors are not on the right row, but the geometry that
measures them is not far away either. `pdf-10`'s row was 69,0 px where 4,80 mm is 18,8 px at the sheet's
3,92 px/mm, and the segment the callout dimensions — `g264`, 18,9 px drawn, i.e. 4,82 mm — was attached to
one anchor the whole time. A pair with one end at each anchor cannot express that (both ends of the segment
belong to the *same* anchor), which is why the earlier cross-anchor re-pick found nothing.

**Single variable:** when the row disagrees with the fitted scale by more than 25% and no cross-anchor pair
lands on the printed length, a **single stroke attached to one anchor** is accepted as the extent if it is
drawn **along the measuring axis** (projection ≥ 99% of its length) **and** to the printed length (within
5%). `row` strokes are excluded — they join the two anchors, so they are the perceived row, not the extent.
The re-pick is also gated to `kind == "linear"` callouts with `anchor_mode == "dimension"`: a radius or
leader callout is not drawn as a row and must never be re-picked against its value.

| | before | after |
|---|---|---|
| bound numbers | 11/14 | **12/14** |
| changed measurements | — | **1/14** (`pdf-10` only) |
| untouched | — | **13/14** |
| plate: bound numbers / stored request hashes | 7/7 / 8/8 | 7/7 / **8/8** |

- `pdf-10` `4.80`: row re-picked 69,0 px → 19,21 px, claim `g272/g276` (4,83 mm drawn), note *"satır ölçeğe
  uymadı (69.0 px, beklenen 18.8 px); çapanın üzerindeki parça çizgisi ölçüldü (19.21 px, artık %2.19)"*.
- A near miss stays a miss: `pdf-11`'s nearest segment is 16,6 px where 15,67 px is needed — 5,9% off, past
  the 5% rule — so the row is left alone, **no re-pick note is written**, and the number stays unresolved.
  (First cut of the rule accepted the *projection* but reported the straight-line length, which wrote a
  "measured" note for `pdf-11` at 5,94%; the accepted measure and the reported one are now the same number.)
- The plate's two disagreeing rows are the Ø6,80 leader (a non-linear callout, now gated out) and `50,00`
  (bound through candidate pairs, not through its row): neither reaches the new branch, and the eight stored
  plate request hashes are unchanged.
- Unresolved and now for a measured reason: `pdf-11`, `pdf-13` — their true geometry sits ~10 px or more
  from both anchors, i.e. outside what the anchors reached. Reaching it would mean detecting geometry the
  reading never touched, which is a different variable and not attempted here.

## 2026-09-27 — the extent drawn on the measuring axis, off both anchors (`bind.py`)

The last two numbers (`pdf-11` 4,00 and `pdf-13` 1,50) were measured a third time, and this time the
geometry was neither far away nor attached: it lies **on the dimension's own axis line**, past the end of
the perceived row, and touches neither anchor. Measured perpendicular distances to the span's own axis:

| span | the extent | perpendicular to the axis | nearest competitor | its distance |
|---|---|---|---|---|
| `pdf-11` 4,00 | `g310`, 15,84 px | **0,0 px** | `g269` (same length) | 47,2 px |
| `pdf-13` 1,50 | `g279`, 5,83 px | **−0,3 px** | `g178` (same length) | 172,8 px |
| `pdf-10` 4,80 (already bound) | `g264`, 18,89 px | **0,0 px** | — | — |

A "nearest geometry to the measurement text" rule would **not** have worked: the correct segment sits 103–108 px
from the text on all three spans, and for `pdf-11` the wrong segment (`g269`, which is `pdf-9`'s own extent) is
*closer* to the text (99,3 px vs 105,9 px). The axis line is the discriminator that separates them exactly.

**Single variable:** after the row test and the two existing re-picks fail, a drawn segment from the reading's
own primitives is accepted as the extent when **both its ends sit on the measuring axis line** (within the
module's existing 4 px feature tolerance — which also makes it parallel to the axis) and its length is within
5% of the printed length; the one nearest the anchors wins. Nothing new is detected (same `observe()` output),
no tolerance is loosened, and the rule is still gated to linear dimension callouts on rows that disagree.

| | before | after |
|---|---|---|
| bound numbers (second sheet) | 12/14 | **14/14** |
| changed measurements | — | **2/14** (`pdf-11`, `pdf-13`) |
| untouched | — | **12/14** |
| plate: bound numbers | 7/7 | 7/7 |
| plate: `bindings.json` dump / stored request hashes | identical / 8/8 | **identical / 8/8** |

- `pdf-11`: row 69,0 px → 15,84 px (*"ölçü ekseni üzerinde çizilmiş parça çizgisi ölçüldü (15.84 px, artık
  %1.11)"*); `pdf-13`: row 79,0 px → 5,83 px (%0,77). On the plate the rule never fires, and the plate's whole
  binding record is byte-identical with the rule on and off — the strongest form of the guard used so far.

### What "14/14" does and does not say (separate measurement)

Every printed number now has a claim whose projection along its axis matches the printed value at the sheet's
scale. That is **coverage**, and it is not the same as a claim that names the extent. Measuring each claim's two
named points for their separation **across** the axis:

| sheet | distance claims | across-axis separation > 20 px |
|---|---|---|
| second sheet | 13 | **8** (up to 750 px) |
| plate | 5 | 1 (275,6 px; the rest are 0,0 px) |

- The two newly bound numbers carry that weakness too: `pdf-11`'s pair is a circle centre 190,6 px across the
  axis (`g59`) with a line end (`g278`), `pdf-13`'s an arc rim 371,8 px across (`g50`) with a line end (`g263`).
  Their projections differ by 4,04 mm and 1,57 mm — the printed values — but they are not the step's faces.
- The weakness is **pre-existing**, not introduced here: the second sheet's `pdf-0` (bound in the first slice)
  names two circle centres 750 px apart across the axis. The plate, which is the only sheet with an independent
  label, has four of five claims exactly on the axis.
- So "bound" is recorded as *"a measured pair at the sheet's own scale"*, never as *"the right geometry named"*.
  Sharpening the claim for a repaired row (prefer the extent's own ends over far-away aligned features) is the
  next single variable, and the table above is the before/after measure for it.

## 2026-09-27 — the claim of a repaired row now names the pair at the extent (`meaning.py`)

Coverage (14/14) was not the same as a claim naming the measured geometry: eight of thirteen claims on the second
sheet named two points whose separation *across* the measuring axis exceeded 20 px (up to 750 px). Before changing
anything, the candidate pools of the seven repaired rows were dumped — every pair that measures the printed value,
with how far its points sit from the anchors:

- every valid pair of every repaired row has its nearest point **≥ 41 px** from the anchors, and for `pdf-8` there
  is **exactly one** valid pair at all (so no ordering can sharpen it);
- for `pdf-13` the same value can be measured by several pairs, one of which (`g310/g263`) sits 47,2 px across the
  axis against the chosen pair's 371,8 px.

**Single variable:** when the row was re-picked against the scale (`SpanBinding.row_repaired`, `Bindings.version`
3), the valid pairs are ordered by **their separation across the measuring axis first** (then the existing rank,
cost and deviation). A pair whose two points lie nearly on the axis is necessarily a *local* pair — the axis
component already equals the printed value, so a small across-axis component means the two points are the printed
length apart in space. Rows that were read as drawn keep the original order exactly.

| | before | after |
|---|---|---|
| second sheet: total across-axis separation of the claims | 2450,2 px | **1262,6 px** |
| median | 118,6 px | **0,1 px** |
| claims above 20 px | 8/13 | **5/13** |
| plate: claims | — | **unchanged, 0/7 different** |

Per repaired row (across-axis px, and the pair's point-to-point distance):

| span | before | after |
|---|---|---|
| `pdf-6` | 6,5 px (38,6 px apart) | **0,0 px** (39,2 px) |
| `pdf-8` | 285,1 px | 285,1 px (forced: the only pair) |
| `pdf-9` | 423,2 px | **55,0 px** |
| `pdf-10` | 238,1 px | **3,3 px** (238,8 → 18,9 px apart) |
| `pdf-11` | 190,6 px | **0,1 px** (191,3 → 15,7 px apart) |
| `pdf-12` | 15,8 px | **0,0 px** |
| `pdf-13` | 371,8 px | **0,0 px** (371,9 → 6,4 px apart) |

- The plate has **no** repaired row, so the change is inert there by construction — verified twice: none of its
  spans is flagged, and all eight stored plate request hashes are still identical.
- The five claims still above 20 px are the three rows that were **read as drawn** (`pdf-0` 750 px, `pdf-3`
  118,6 px, `pdf-7` 50,2 px) plus two repaired rows with nothing to choose (`pdf-8`, `pdf-9` 55 px). Those were
  left alone on purpose: sharpening a row the drawing itself got right is a different change with a different
  risk.

**What this does not say (and a correction to an earlier entry).** An earlier entry in this file said no
id-level reference labels exist. That was wrong for the plate: `eval/relations/plate-pocket-1.json` is a
hand-verified relation label (per printed number: `form`, `resolution` and a prose `measures`, checked against the
STEP; `eval/relations/` is read by the scoring only and never fed to the model). The second sheet has none
(`label_available: false`). Measured against that label, **all seven plate claims agree in form and in kind**:
`d1` two hole centres (circle-centre ×2), `d2` the two corner arcs (arc-rim ×2), `d3` hole centres, `d4` the four
corner holes (diameter), `d5` the pocket circle, `d6` the plate thickness, `d7` the pocket depth (line-end ×2).

The label also settles what the across-axis separation does **not** mean: `d7`'s two points sit 275,6 px across the
axis and the claim is *correct* — a section-view thickness/depth dimension legitimately names two faces far apart
sideways. So "local" is not "correct", and the across-axis number above is a locality measure, not a correctness
one. The slice is scoped to repaired rows for exactly that reason (a row the drawing drew correctly is left
alone), which the label now justifies rather than the guess it started from. On the second sheet there is no label,
so beyond the printed-value match its six sharpened claims are **not verified** — that is what the interface round
(`meaning-3b-06`) is for.

## 2026-09-28 — üçüncü pafta: elle doğrulanmış etiket kuruldu, okuma beş çapı mesafe olarak sunuyor

Üçüncü pafta `examples/pdf with steps/2/Drawing.pdf` ("Exercise 1", ölçek 1:2) + `Part-2.STEP`; etiket
`eval/relations/exercise-1-vector.json` (yalnız değerlendirmede; `cases.json`'da vaka zaten vardı). Etiket elle
kuruldu ve **STEP'e karşı doğrulandı** (kutu 134×80×50 mm, 11 silindir, 16 düzlem yüzey):

- **Beş çap STEP'ten birebir**: Ø20 (sol kulak deliği, r=10,00 @ (-37,00; 66,37)) · Ø25 (sağ kulak deliği,
  r=12,50 @ (57,00; 27,96)) · Ø30 (orta göbek deliği, r=15,00 @ (9,55; 40,00)) · Ø40 (sağ göbek, r=20,00
  @ (61,24; 32,73)) · Ø50 (orta göbek, r=25,00 @ (13,94; 42,00)).
- **Alt görünüşün beş dikeyi parçanın kalınlıkları çıktı** ve STEP'teki z konumlarıyla birebir: 26 (z=±13) ·
  6 (z=±3) · 20 (z=±10) · 40 (z=±20) · 10 (z=±5).
- 80 = parçanın toplam yüksekliği (kutu y=80; y=0 ve y=80 düzlemleri var); 37 ve 57 = ortak datuma (STEP'te
  x=0) göre iki kulak deliğinin merkezleri (x=-37,00 ve x=+57,00 — paftadaki 37+20=57 zinciri aynı datumdan).
- Paftadan okunan, STEP'in kesinleştirmediği üç sayı: 60, 35 ve üst görünüşteki 20 — etikette
  `verified: "drawing"` olarak işaretli (uydurma yok).

**ÖLÇÜLEN ENGEL (okuma zincirinin kendi engeli):** bu paftanın PDF **metin katmanında Ø glifi hiç yok** — 468
karakterin hiçbiri Ø değil, hiçbir karakter 0x2000 üstünde değil (yani çap önekleri vektör çizim). Sonuç:
okuma beş çap çağrısını düz `linear` sayı olarak alıyor ve onları **iki çizgi ucu arasında bir mesafe** gibi
bağlıyor — `pdf-19` (30) · `pdf-20` (25) · `pdf-22` (40) bağlı, `pdf-21` (50) hiç bağlanamıyor. `cases.json`'ın
kendi `diameter_calls` alanı gerçeği zaten yazıyor: `[20, 25, 30, 40, 50]`.

**Etiketle ölçüm (kuru koşu, model çağrısı yok):** 17 sayının **11'i** eşleşiyor (kalan 6'sı çift değerli
olduğu için harness onları bilinçli olarak eşleştirmiyor: dört "20" ve iki "40"). Eşleşen üç çap satırında
karşıtlık tam:

| ölçü | okumanın formu | etiketin beklediği |
|---|---|---|
| `pdf-19` (Ø30) | distance | **diameter** |
| `pdf-20` (Ø25) | distance | **diameter** |
| `pdf-21` (Ø50) | **none** (çözülememiş) | **diameter** |

Yani bu paftada arayüze sorulan soru üç ölçü için yanlış öncülden geliyor: "hangi iki uç arasında?" — gerçek
"sınırlanan geometri hangisi?". Bunu düzeltmenin yeri arayüz değil **okuma**: metinsel olmayan Ø glifini (veya
tek daireye işaret eden lider geometrisini) çaptır diye tanımak. Kapı: değişiklikten sonra bu paftada beş
çağrı `diameter` olmalı, plaka ve plastiğin okuması **bayt bayt** korunmalı.

## 2026-09-28 — altıncı dilim: Ø öneki çizim; okuma beş çapı tür ve bağ olarak kazandı

**Ölçülen kusur.** `examples/pdf with steps/2/Drawing.pdf` metin katmanı 468 karakter taşıyor, hiçbiri Ø
değil: beş çap öneki **vektör çizim**. Bu yüzden çaplar okumaya *uzunluk* olarak giriyordu — `pdf-19` (30)
iki çizgi ucu arasında mesafe diye bağlanmış, `pdf-20` (25) aynı, `pdf-22` (40) mesafe, `pdf-17`/`pdf-21`
(Ø20/Ø50) çözülememiş. `cases.json`'ın kendi `diameter_calls` alanı gerçeği yazıyordu.

**Kural 1 — önek metinde yoksa glifi okunur.** `observe._diameter_prefix_glyph`: rakamların yanına
çizilmiş **küçük daire** (yarıçapı cümlenin yüksekliğinin en çok %60'ı, merkezi kutunun 1,2 × yükseklik
yakınında) varsa cümle `diameter`. Ölçüt pafta ölçeğine değil cümlenin kendi boyuna bağlı.
- Ölçüm: beş glif (Ø6,40 mm, r ≈ 12,2 px) çağrıların **8–21 px** yanında; paftadaki gerçek daire/yayların
  en yakını **138 px** → kural 5 kat payla ayırıyor.
- Kural plakada da ateşledi: plaka `Ø6,80` ve `Ø50,00`'i de çizim olarak basıyor (2 çağrı) — plastikte hiç
  (orada Ø metin katmanında).

**Kural 2 — tür, bağı lider koşuluna bağlamaz.** `meaning._meaning_for` çap eşlemesini yalnız
`anchor_mode == "leader"` iken deniyordu; üçüncü paftanın beş çağrısı lider değil, yani tür doğru olsa bile
bağ kurulamıyordu. Değişiklik: `binding.kind == "diameter"` **ya da** lider → çap eşlemesi.

**Sonuç (dry-13 → dry-14; aynı pafta, iki kural ayrı ayrı):**

| ölçü | iki kuraldan önce | kural 1 sonrası | kural 2 sonrası |
|---|---|---|---|
| pdf-17 (Ø20) | linear, çözülemedi | diameter, çözülemedi | **diameter, g133** |
| pdf-19 (Ø30) | linear, *yanlış* mesafe bağı | diameter, çözülemedi | **diameter, g68** |
| pdf-20 (Ø25) | linear, *yanlış* mesafe bağı | diameter, çözülemedi | **diameter, g122** |
| pdf-21 (Ø50) | linear, çözülemedi | diameter, çözülemedi | **diameter, g65** |
| pdf-22 (Ø40) | linear, mesafe bağı | diameter, mesafe bağı | **diameter, g125+g134** |

- Çözülen ölçü **12 → 16** (17'nin); tek çözülemeyen `pdf-18` (düz "6").
- **Etiketle tür uyumu 1/5 → 5/5**: etiketin `printed` sütunu Ø20/Ø25/Ø30/Ø40/Ø50 için `diameter` diyor.
- Bağlar **değer eşleşmesiyle** kuruldu (%3 bağıl tolerans): 20,56/20 = %2,8 · 30,70/30 = %2,3 ·
  25,70/25 = %2,8 · 51,33/50 = %2,7 · 41,08/40 = %2,7. Kalibrasyon 3,83 px/mm; 1:2 paftanın gerçek ölçeği
  3,937 px/mm (200 dpi ÷ 25,4 ÷ 2) → %2,7 sistemik sapma, çaplar toleransın kenarında.
- `pdf-22` (Ø40) ile `pdf-13` (R20) **aynı iki yayı** (g125/g134) gösteriyor: paftada ikisi de yarıçap ≈ 20,5 mm;
  ayrımı yalnız STEP veriyor (Ø40 = sağ göbek). Belirsizlik olarak kayda geçti, çözülmüş sayılmadı.

**Regresyon kalkanı (ölçüldü, varsayılmadı).**
- Plastik okuması **değişmedi** (kural 1 açık/kapalı: tür, form, çözüm, eşlenen geometri, notlar birebir).
- Plakada yalnız iki cümlenin **türü** düzeldi (`6,80 THRU ALL`, `50,00`: linear → diameter); form, çözüm,
  eşlenen geometri ve notlar **aynı**.
- **İstek özetleri 22/22 saklananla aynı** (koşu 09 paketi; plaka + plastik) — bu ölçüm `--check`'in
  yapmadığı şey: `--check` saklanan cevabı yeniden yargılar, isteği yeniden kurmaz. Kalkan ayrı bir
  betikle hesaplandı (`out/profile-step/prompt-shield.txt`).
- Testler: `tests/test_diameter_glyph.py` (4 test) + `tests/test_bind.py` (3 test) eklendi.

**Dürüst sınır.** Bağlar *değere* göre kuruldu, kimlik doğrulamasıyla değil: etiketin `geometry.circles`
kimlikleri STEP koordinatlarıyla adlandırılmış (bore20/bore25/bore30/boss40/boss50), okumanın kimlikleriyle
(g133/g68/g122/g65/g125/g134) **eşlenmedi**. Bağ puanlaması için o eşlemenin elle doğrulanması gerekir —
bu, sonraki dilimin işi.
- **Testler:** tam takım `round18` = **467 geçti / 243,05 sn** (önceki tur 460; bu dilimde +7 test:
  `tests/test_diameter_glyph.py` 4, `tests/test_bind.py` 3). Ayakta duran denetimler: `check_tables` 20/0,
  `baseline_report --check` ve `profile_step_evidence --check` uyuşuyor.

## 2026-09-28 — bağ puanlaması üçüncü paftada neden kapalı (ölçüldü)

Harness, etiketin konumlarını okumanın mm çerçevesindeki kimliklerle `POSITION_TOLERANCE_MM` (= 2 mm)
içinde eşliyor. Plakada tutuyor: etiket `h1 = [-50,-30]`, ölçülen `g9 = [-50.35,-30.21]` → 0,4 mm, ve
koşu 09 kaydında **8 ölçünün 5'i bağ-puanlanabilir**. Üçüncü paftada **0/17**:

| etiket kimliği | Ø | etiket konumu (STEP) | en yakın ölçülen | uzaklık |
|---|---|---|---|---|
| bore20 | 20,00 | [-37,0, 66,37] | g129 | **34,01 mm** |
| bore25 | 25,00 | [57,0, 27,96] | g125 | **14,91 mm** |
| bore30 | 30,00 | [9,55, 40,0] | g129 | **23,77 mm** |
| boss40 | 40,00 | [61,24, 32,73] | g128 | **12,14 mm** |
| boss50 | 50,00 | [13,94, 42,0] | g129 | **28,14 mm** |

Sebep ölçülmüş: beş çemberin dışındaki bütün etiket kimlikleri yüz/kenar (`top_face`, `datum`,
`left_lug_face_a` …) ve çember konumları **parça çerçevesinde** (STEP koordinatları) yazılmış; okumanın
konumları ise paftanın görünüş çerçevesinde (kontur merkezine göre). İki çerçeve bu paftada 12–34 mm
ayrışıyor. Etiket bunu sessizce "tutuyor" diye geçmiyor: `binding_checkable: false` + `unmapped_label_ids`
listesiyle söylüyor. Yani bu paftada etiket **biçimi ve türü** puanlıyor, bağı puanlamıyor.

**Sonraki dilim için ölçülmüş öneri:** çaplarda kimlik *boyuttur* — etiketin STEP'ten doğrulanan
`diameter_mm` değerleri (20 · 25 · 30 · 40 · 50) okumanın ölçtüğü çaplarda (20,56 · 25,70 · 30,73 · 51,33 ·
41,08) tekil ve %3 içinde. Eşleme konum yerine **çapa** göre yapılırsa üçüncü paftada beş satırın bağı
puanlanabilir hale gelir; kapı: plakada 5/8 değişmez, plastikte 0 kalır.

**Kayıt notu (2026-09-28):** `out/profile-step/reading-coverage.txt` on paftalık ham taramadır ve **20. dilim
öncesi** bir anlık görüntüdür; içindeki bağ sayıları artık geçersiz (plastik 4 → 14, üçüncü pafta 11 → 16),
reddetme satırları geçerli. Süreç son satırını yazdıktan sonra sonlandırıldı (exit -9, kabuk satırı çalışmadı):
kayıp iş yok. Güncel sayılar bu raporun ilgili bölümlerindedir.
