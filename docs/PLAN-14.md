# PLAN.md — drawingto3d / SEMREAD-001D
## 001C immutable kapanış + repo hijyeni → semantic-content contract → dev proof → bağımsız holdout → freeze → final karşılaştırma

**Tarih:** 2026-10-05  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Başlangıç HEAD:** `2c42f1b3acbe026bb66215afb8c67fb80064acce`  
**001C requalification:** 7/8 resmî gate, 32/32 dev bütçe, final 0/20  
**001C ortak generation envelope:** doğrulandı  
**001C semantic içerik:** 0/8  
**001C kararı:** final fazına geçme; yeni experiment version aç  
**Yeni experiment:** `SEMREAD-001D`

---

# 0. Yönetici özeti

001C artık daha fazla canlı çağrıyla kurtarılmaya çalışılmayacak.

001C'nin verdiği gerçek bilgi:

```text
wire/output contract büyük ölçüde düzeldi
V/VE shared generation settings sağlandı
truncation/sonsuz loop kontrol altına alındı
ama semantic content üretimi başarısız
```

Son requalification:

```text
7/8 formal valid
8/8 stop
8/8 shared settings
7/8 coordinate/refs
0/8 semantic content
32/32 dev budget
```

Tek coordinate ihlali:

```text
flange-elbow-VE
c32.callout_region.y1 = 1.05
```

001C final'e geçmeyi blokladı. Fakat asıl blocker `semantic content = 0/8`.

001D'nin hedefi artık “aynı formatı biraz daha sağlamlaştırmak” değil; modeli boş kutu / observation-table yankısı üretmekten çıkarıp gerçek callout semantics üretmeye zorlamak.

---

# 1. P0 — 001C REPO HİJYENİ VE IMMUTABLE KAPANIŞ

İlk iş inference değildir.

001D koduna başlamadan önce 001C'nin repo kayıtları kendi içinde tutarlı hale getirilecek.

Bu faz yalnız:

```text
documentation
metadata
closure verification
```

işidir.

Canlı model çağrısı:

```text
0
```

---

# 2. P0.1 — report.md stale alanlarını düzelt

`report.md` güncel §2c'de doğru requalification sonucunu taşıyor.

Fakat aşağıdaki eski satırlar stale:

## Eski stale zarf

Şu tarihsel metin:

```text
repeat_penalty V 1.4 / VE 1.25
```

artık “current locked envelope” diye görünmemeli.

Güncel 001C requalification envelope:

```text
repeat_penalty = 1.25
repeat_last_n = 512
num_ctx = 22528
num_predict = 8192
temperature = 0.0
V == VE generation settings
```

Eski V=1.4 / VE=1.25 değerleri historical dev tuning step olarak korunabilir ama current/final envelope diye sunulamaz.

---

# 3. P0.2 — budget satırlarını güncelle

Eski raporda kalan:

```text
24/24
```

current state olarak yanlış.

001C closure:

```text
dev used = 32
dev ceiling = 32
final used = 0
final planned ceiling = 20
```

olarak yazılmalı.

Budget history kaybolmamalı:

```text
10 → 12 → 16 → 18 → 20 → 22 → 24 → 32
```

ama current snapshot `32/32` olmalı.

---

# 4. P0.3 — evidence paths / handoff referanslarını güncelle

Stale satırlar:

```text
24 calls
24 attempts
handoff §1p
```

yerine current closure:

```text
32 dev calls
32/32 budget
handoff §1s
requalification batch
dev-report refreshed
dev-semantic-report refreshed
```

yazılmalı.

Kanıt yolları gerçekten repoda mevcut olan dosyalara işaret etmeli.

---

# 5. P0.4 — historical vs current ayrımı

`report.md` içinde tarihsel tuning değerleri tamamen silinmemeli.

Ama yapı:

```text
Historical envelope evolution
Current 001C closure envelope
```

olarak ayrılmalı.

Örnek:

```text
Historical:
V=1.4 / VE=1.25 arm-specific phase

Closure:
V=VE=1.25 shared envelope
```

Böylece geçmiş korunur ama current fact drift oluşmaz.

---

# 6. P0.5 — run_contract docstring hijyeni

`semantic_run_contract.py` docstring eski envelope revizyonlarını eksik anlatıyorsa yalnız dokümantasyon metni düzeltilir.

Kod davranışı değiştirilmez.

Şu ayrım açık olmalı:

```text
001C historical envelope iterations
001C final shared requalification envelope
```

Bu commit inference üretmez.

---

# 7. P0.6 — PLAN / report / handoff tutarlılık kontrolü

Karşılaştır:

```text
docs/PLAN-13.md
report.md
docs/HERMES_SEMREAD_001C_HANDOFF.md
semantic_run_contract.py comments
```

Aşağıdaki facts birebir uyuşmalı:

```text
dev budget 32/32
final budget 0/20
requalification 7/8
shared settings 8/8
stop 8/8
semantic content 0/8
coordinate failure elbow-VE y1=1.05
001C final blocked
next = new experiment version
```

---

# 8. P0.7 — 001C closure commit

Tek bir docs-only commit önerisi:

```text
semread-001c: closure hygiene — report/handoff/current envelope/budget evidence aligned
```

Bu commit:

```text
NO inference
NO schema change
NO reader change
NO evaluator change
NO budget change
NO attempt mutation
```

yapmalı.

---

# 9. P0.8 — 001C immutable closure snapshot

Hygiene commit sonrası bir closure snapshot kaydet.

Minimum:

```text
closure HEAD
report.md sha256
handoff sha256
PLAN-13 sha256
001C state/budget summary
selected final dev attempts
producer identity
evaluation identity
run-contract identity
```

Eski attempt artifact'larını rewrite etme.

001C bundan sonra:

```text
READ-ONLY HISTORICAL EXPERIMENT
```

kabul edilir.

---

# 10. P0 acceptance

- [ ] 0 inference
- [ ] report current envelope correct
- [ ] report budget 32/32 correct
- [ ] report evidence paths current
- [ ] handoff §1s referenced
- [ ] historical tuning retained but labeled historical
- [ ] run-contract comments current
- [ ] PLAN/report/handoff facts aligned
- [ ] no code behavior change
- [ ] no attempt mutation
- [ ] closure commit created
- [ ] closure snapshot recorded

---

# 11. Neden 001C retry yapılmıyor?

Bir redo:

```text
elbow-VE only
budget 33
```

ile formal gate belki 8/8 olabilir.

Ama bu asıl problemi çözmez:

```text
semantic content 0/8
```

Dolayısıyla retry formal success üretebilir ama semantic reader success üretmez.

Ayrıca mevcut plan 32 sonrası tuning yok diyor.

Bu nedenle 001C burada kapanır.

---

# 12. SEMREAD-001D — tek araştırma sorusu

001D sorusu:

```text
Local VLM, technical drawing callout'larından
gerçek semantic fields üretebilir mi?
```

İlk hedef `valid JSON` değil, `meaningful semantic candidate`.

---

# 13. 001D başarı tanımı

Bir candidate semantic-content-bearing sayılırsa en az biri dolu olmalı:

```text
callout.text known
form.symbol known
size known
count.printed known
termination known
depth known
representation known
target.state bound
```

Sadece `source.region` taşıyan candidate content-bearing sayılmaz.

Sadece observation row box'ı kopyalamak da sayılmaz.

---

# 14. P1 — semantic-content gate'i first-class yap

001D evaluator/dev gate:

```text
parse valid
refs valid
stop
coordinate valid
leak clean
```

yanında zorunlu:

```text
semantic_content_count > 0
```

ölçmeli.

Dev page bazında en az bir content-bearing candidate minimum gate olabilir.

Bu final accuracy threshold değildir.

---

# 15. P1.1 — observation echo metriği

VE için first-class metric:

```text
observation_echo_count
observation_echo_rate
```

Candidate region observation table satırını kopyalıyor ama semantic fields boşsa echo say.

001C'deki 45/45 davranışını doğrudan ölç.

---

# 16. P1.2 — duplicate metric

First-class:

```text
exact_duplicate_count
near_duplicate_count
duplicate_rate
```

Candidate ID farklı olsa bile aynı semantic+region body tekrar ise duplicate.

Parser silently dedupe etmez; evaluator raporlar.

---

# 17. P2 — task contract'ı semantic extraction'a odakla

Yeni ortak prompt önceliği:

```text
DO NOT emit a candidate unless you can report at least one semantic fact.
```

Açık kural:

```text
A candidate with only a region and all semantic fields unknown is invalid for this task.
```

Bu 001D contract'ının merkezidir.

---

# 18. P2.1 — region ikincil olmalı

Model önce semantic claim üretmeli.

Region, claim'e bağlı localization olmalı; görev page segmentation'a dönüşmemeli.

---

# 19. P2.2 — output schema minimum semantic content

Mümkünse deterministic validator:

```text
if all semantic fields default/unknown:
    reject semantic-empty candidate
```

Yeni schema version gerekir.

---

# 20. P2.3 — source-only candidate yasak

Şu body 001D'de valid candidate olmamalı:

```text
candidate_id
source.region
everything else unknown
```

Unit testle bağlanmalı.

---

# 21. P2.4 — VE observation table'ın rolünü değiştir

Prompt açıkça:

```text
Do not create one candidate per observation row.
Observations are optional evidence only.
A row is not a semantic claim.
```

demeli.

---

# 22. P2.5 — VE observation_id

`observation_id` yalnız semantic claim'i gerçekten destekliyorsa kullanılmalı.

Şu davranış yasak:

```text
one observation row → one empty candidate
```

---

# 23. P3 — dev protocol

001D development için mevcut 4 dev page kullanılabilir.

Kollar:

```text
V
VE
```

D offline baseline.

---

# 24. 001D dev budget

Baştan kesin:

```text
dev max = 12
final max = 20
total = 32
```

Dev:

```text
8 primary calls
4 diagnostic reserve
```

12 sonrası yeni experiment version gerekir.

---

# 25. 001D dev sequence

Round 1:

```text
plate-pocket V/VE
flange-book V/VE
```

4 calls.

Gate geçerse:

```text
flange-elbow V/VE
drawing-2 V/VE
```

+4.

Reserve 4 yalnız blocker diagnosis.

---

# 26. 001D dev acceptance

Her primary cell:

```text
parse valid
stop
coordinate valid
refs valid
leak clean
shared settings
semantic_content_count >= 1
```

VE ayrıca tüm candidate'ların observation echo olmaması gerekir.

V ayrıca tüm candidate'ların duplicate source-only box olmaması gerekir.

---

# 27. Semantic quality sanity

Final holdout'a geçmeden dev gold'a karşı:

```text
matched semantic fields
localization
field accuracy
abstention
overclaim
```

ölç.

Minimum:

```text
non-zero semantic field accuracy
```

olmalı.

001C'deki 0% tekrarlanırsa final'e geçme.

---

# 28. Shared generation invariant korunur

001D V ve VE:

```text
same model
same digest
same runtime
same task
same schema
same sampling
same num_ctx
same num_predict
same repeat settings
```

Tek fark evidence.

---

# 29. Structural cap

`maxItems=32` korunabilir ama artık ana anti-loop mekanizma olmamalı.

Semantic-empty candidate yasaklanınca gerçek candidate count doğal olarak düşmeli.

---

# 30. 001D holdout

Dev semantic gate geçmeden yeni holdout'a model çalıştırma.

Kullanıcıdan tercihen:

```text
12–20 yeni teknik çizim
```

al.

Bunlardan 10 final page model output görülmeden seçilir.

---

# 31. Holdout eligibility

- repo geçmişinde yok
- 001B/001C/001D dev'de görülmemiş
- duplicate değil
- technical drawing
- SEMREAD scope claim içeriyor

Hash + group ID.

---

# 32. Holdout diversity

Mümkünse:

```text
4 vector/PDF
6 raster
```

Coverage:

```text
Ø
R
count
THRU
depth
unknown termination
rotated text
multi-view
crowded leader
low-res raster
```

---

# 33. Gold

Gold model output görülmeden hazırlanır.

Reuse:

```text
tracked spec
vision checked
source evidence
target reason
independent corroboration
cycle validation
stable identity
```

---

# 34. Freeze

Freeze öncesi:

```text
dev semantic-content gate passed
dev semantic field accuracy non-zero
shared settings invariant
full pytest 0 fail
new holdout 10/10
D baseline
final 0/20
model/digest/runtime exact
context preflight
raw V/VE equality
leak audit
clean clone
```

---

# 35. Final

```text
10 pages × V/VE = 20 calls
retry = 0
```

First-shot; failures preserved.

---

# 36. Final primary metrics

İlk metric:

```text
semantic_valid_output_rate
```

Yani:

```text
parse valid
AND content-bearing
```

Sonra:

```text
localization
form
size
count
termination
depth
target binding
overclaim
abstention
```

---

# 37. 001D karar ağacı

## V semantic-content üretir, VE yankıya düşerse

Ürün yönü:

```text
raw VLM
+
deterministic validation
```

## VE V'den iyi ise

Observation evidence faydalı.

## İkisi de 0'a yakınsa

Bu model/prompt architecture task için uygun değil.

Sonraki experiment:

```text
crop-based
staged
OCR-first
structured query
```

gibi farklı yaklaşım olmalı.

---

# 38. Full pytest / CI

001D freeze öncesi full pytest zorunlu.

External CI yoksa:

```text
local evidence only
```

açıkça yaz.

CI borcu experiment'ı geciktirmemeli.

---

# 39. Repo hijyeni 001D boyunca da kural

Her phase sonunda:

```text
report
handoff
plan
run contract comments
budget state
```

aynı current facts'i taşımalı.

Stale sayı bırakma.

Historical value gerekiyorsa:

```text
HISTORICAL
```

etiketiyle tutulmalı.

---

# 40. Dokümantasyon invariant testi

Mümkünse küçük script/test:

```text
current dev_used
current final_used
contract version
shared repeat penalty
current experiment
```

değerlerini state/run-contract'tan alıp report summary ile karşılaştırır.

Source-of-truth:

```text
state + contract + attempts
```

olmalı.

Report source-of-truth olmamalı.

---

# 41. Commit planı

```text
1. 001C closure hygiene docs-only
2. 001C closure snapshot
3. 001D plan + experiment skeleton
4. semantic-content validator
5. observation-echo / duplicate metrics
6. 001D prompt/schema v3
7. focused tests
8. first 4 dev calls
9. remaining 4 dev calls
10. dev semantic report
11. full pytest
12. holdout intake/selection
13. gold
14. D baseline + clean clone
15. freeze
16. final 20
17. immutable final report
```

---

# 42. Şimdi yapılacak TEK iş

**Inference yok.**

Önce:

```text
001C REPO HİJYENİ + IMMUTABLE CLOSURE
```

Tam olarak:

```text
report.md stale envelope düzelt
report.md budget 32/32 yap
evidence paths / handoff §1s düzelt
historical/current ayrımı yap
run-contract docstring/comments güncelle
PLAN/report/handoff fact alignment kontrol et
docs-only closure commit
closure snapshot
```

Bundan sonra `SEMREAD-001D implementation` başlar.

---

# 43. İlk iş acceptance

- [ ] 0 inference
- [ ] report current envelope = shared rp 1.25
- [ ] historical arm-specific envelope history olarak korunuyor
- [ ] report dev budget = 32/32
- [ ] report final = 0/20
- [ ] handoff §1s
- [ ] requalification = 7/8
- [ ] stop = 8/8
- [ ] shared settings = 8/8
- [ ] semantic content = 0/8
- [ ] elbow-VE y1=1.05 recorded
- [ ] no attempt rewrite
- [ ] no evaluator rewrite
- [ ] docs-only commit
- [ ] closure snapshot
- [ ] 001C read-only ilanı

---

# 44. Son karar

001C'nin görevi bitti.

001C bize:

```text
format reliability ≠ semantic reading
```

dersini verdi.

001D'nin işi modeli gerçekten semantic claim üretmeye zorlamak olacak.

Ama bundan önce repo history temiz ve kendi içinde tutarlı kapanmalı.

Sıra:

```text
001C hygiene
→ immutable closure
→ 001D semantic-content contract
→ dev proof
→ holdout
→ freeze
→ final
```
