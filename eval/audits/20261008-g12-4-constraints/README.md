# G12.4 — exact supported 2D constraints (PLAN-25 §55–§60)

Bu dizin G12.4'ün kanıtıdır. Fazın özü: basılı ölçü *koordinatı belirler* — tek bir küresel ölçek uydurulmaz
(§56), her çözülen koordinat kendi kökenini yapısal olarak taşır (§57), çözüm durumları
(`constrained`/`underconstrained`/`conflict`/`unsupported`) ortalamasız raporlanır (§58), yetersiz belirlenmiş
taslak yalnız açık izleme onayıyla üretilir ve N/M denetimi yazılır (§59). §60'ın beş P4 senaryosu gerçek
STEP üretip yeniden açar.

## Ne değişti
- `sketch_constraints.solve_constraints`: sonuç artık **`coordinates`** taşır — her koordinat değeri
  (nokta × eksen) için kaynak (`dimension`/`trace`), değer ve **adım zinciri**: bağ kimliği, denklem türü
  (`x-distance`/`y-distance`/`horizontal`/`vertical`), basılı değer (denklemin kullandığı işaretle), birim,
  basılı ölçünün kaydı (`span_ids`) ve geometri hedefleri. Datum ve serbest bileşenler boş zincirle `trace`.
- Aynı sonuç **`audit`** taşır: `dimension_derived` (N) / `trace_derived` (M) — §59'un sayımı, koordinat
  değeri başına.
- `guided.user_dimensions`: rapor `coordinates` + `audit` alanlarını taşır (desteklenmeyen ve çakışan
  durumlarda sıfır denetimle) — önizleme, plan ve kabul aynı kaydı okur.
- Davranış değişmedi: çelişen ölçü yine ortalamasız reddedilir ("bağlanan ölçüler birlikte tutmuyor"),
  çözülemeyen bağ `unsupported`, izleme onayı olmayan taslak üretilmez.

## Kanıt
- `tests/test_g12_p4_constraints.py` (**5/5**) — §60 P4: 60 × 40 dikdörtgen **tam** (§56; izlenen 50 × 30
  değil), daire merkezleri arası 30/6 mm **tam**, delik Ø6 **tam** (izlenen Ø8 değil), çelişen genişlik
  adlarıyla reddeder ve STEP üretmez, yetersiz taslak sayılır (N=1/M=11) ve izleme onayı olmadan başlamaz.
  Her senaryo ürün yolundan geçer (`make_plan` → `build_general` → STEP yeniden açılır).
- `pytest-relevant.log` — ilgili süit (`test_sketch*`, `test_dimensions`, `test_user_dimensions`, `test_guided*`,
  `test_callout*`, `test_build_strategy`, `test_g12*`, `test_g11*`): **678 passed / 4:06 / EXIT=0**.
- `pytest-broad.log` — geniş regresyon (`pytest -q tests -k "not semread"`): **1590 passed / 339 deselected /
  29:31 / EXIT=0** (G12.3: 1582 → +8).
- `plate-regression.log` — G12R Plate kabulü: **11/11** (kabul edilmiş üretim yolu bozulmadı).
- `p4_step_artifact.py` → `p4-rectangle.step` (20173 bayt), `p4-geometry.json` (size 60 × 40 × 10, hacim
  24000 − π·9·10, silindir r=3), `p4-provenance.json` (§57 zincirleri + §59: 6 boyut türevi, 6 izlenen).
- `test_sketch_constraints.py` (+2 test) ve `test_user_dimensions.py` (+1 test) — §57/§59 sözleşmeleri.

## Dokunulmayan
Eski kanıt dizinleri, dondurulmuş manifest ve `eval/metrics.py` değişmedi; ana metrik hâlâ **1/9**.
Bu fazda UI değişmedi (§99'un Chrome kontrol listesinde G12.4 yok).
