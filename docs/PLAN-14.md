# PLAN.md — drawingto3d / SEMREAD-001D
## Skeleton sonrası güncel plan

**Tarih:** 2026-10-05
**Repo:** `AhmetAydemir1/drawingto3d`
**Gözlenen `main` HEAD:** `074cc40c2efb094c3d06c6f70a1292a7e3985ad2`
**Aktif deney:** `SEMREAD-001D`
**Aktif plan:** `docs/PLAN-14.md`
**001D bütçe:** dev `0/12`, final `0/20`, toplam `0/32`
**001C:** CLOSED / READ-ONLY HISTORICAL
**External CI/status:** yok
**Current full pytest:** bu HEAD için henüz yok

---

# 0. Durum

Tamamlananlar:

```text
001C hygiene
→ immutable closure
→ closure verify 45/45
→ PLAN-14 tracked
→ 001D handoff
→ budget 12/20 predeclared
→ skeleton tests
→ focused SEMREAD tests
→ gates 34/34
```

Henüz yapılmayanlar:

```text
semantic-content validator
schema /3
reader /3
001D run-contract /1
001D dev report
live 001D inference
```

Current code hâlâ:

```text
CANDIDATE_SCHEMA_VERSION = semread-candidates/2
CANDIDATE_READER_VERSION = semread-candidate-reader/2
CONTRACT_VERSION = semread-001c-run-contract/1
```

İlk canlı 001D çağrıdan önce bunlar mutlaka 001D'ye bump edilmeli.

---

# 1. Repo hijyeni invariantı

001C artık dokunulmaz:

```text
docs/HERMES_SEMREAD_001C_HANDOFF.md
eval/semread_001c_closure.*
out/lab/semread-001c/**
```

Milestone'larda:

```text
001C closure --verify 45/45
```

geçmeli.

001D boyunca:

```text
plan
handoff
report
budget state
contract version
```

aynı current facts'i taşımalı.

Historical değerler `HISTORICAL` etiketiyle tutulmalı.

---

# 2. Root report hijyeni

Kök `report.md` hâlâ 001C faz raporu başlığını taşıyor ama aktif plan 001D.

001D ilk milestone'unda iki seçenekten biri seç:

```text
A) root report'u experiment-neutral living status report yap
B) 001D için ayrı tracked/report artifact aç
```

001C closure history rewrite edilmez.

---

# 3. Semantic content tanımı ikiye ayrılmalı

001D'nin en önemli yeni kuralı:

```text
semantic claim != evidence-only
```

## Semantic claim sayılacaklar

Şunlardan en az biri:

```text
callout.text known/non-empty
form.symbol = R veya diameter
size.state = known
count.printed != null
termination = thru veya finite
depth.state = known
physical.kind != unknown
```

## Tek başına semantic claim SAYILMAYACAKLAR

```text
representation.kind
count.found_circles
target.state
target.observation_id
source.region
uncertainty
```

Bunlar evidence/binding metric olarak ayrı raporlanır.

Bu ayrım gate gaming'i önler.

---

# 4. P1 — tek kaynak helper

`semantic_candidates.py` içinde tek kaynak:

```text
semantic_claim_flags(candidate)
candidate_has_semantic_claim(candidate)
evidence_flags(candidate)
```

Aynı tanım:

```text
parser
dev report
final evaluator
tests
```

tarafından reuse edilmeli.

Kopya semantic-content mantığı oluşturma.

---

# 5. P1.1 — semantic-empty wire output reddi

001D model output'unda:

```text
candidate_id
source.region
all semantic fields unknown
```

valid candidate değildir.

Yeni failure subtype:

```text
schema_semantic_empty
```

Akış:

```text
JSON
→ structural validation
→ semantic-claim validation
→ references
```

Sessiz tamir yok.

---

# 6. Global Candidate validator'a dikkat

`Candidate` deterministic D tarafından da kullanılıyor olabilir.

Bu yüzden önce D path audit et.

Tercih:

```text
wire-response parse boundary
```

üzerinde semantic-empty enforcement.

Global Pydantic validator koyacaksan önce D regression kanıtı şart.

---

# 7. Empty response valid kalabilir

Şu response:

```json
{"schema_version":"...","items":[]}
```

genel abstention olarak valid kalabilir.

Ama dev sayfalarda claim var.

Bu yüzden dev gate ayrıca:

```text
semantic_claim_count >= 1
```

ister.

---

# 8. Negatif testler

Bunların her biri reddedilmeli:

```text
source.region only
representation=circle only
found_circles only
target.state=bound only
target.observation_id only
uncertainty only
```

Failure:

```text
schema_semantic_empty
```

---

# 9. Pozitif testler

Bunlar semantic claim'i sağlamalı:

```text
known callout text
form=R
form=diameter
known size
printed count
termination=thru + stated
finite + depth
known depth
physical non-unknown
```

Fixture'lar generic olmalı.

Frozen/dev answer leakage yok.

---

# 10. P2 — version bump

İlk canlı 001D inference öncesi:

```text
semread-candidates/3
semread-candidate-reader/3
semread-001d-run-contract/1
```

olmalı.

Attempt manifestinde:

```text
experiment = semread-001d
schema = /3
reader = /3
run contract = 001d/1
```

açıkça görünmeli.

---

# 11. Run contract geçişi

Mevcut `semantic_run_contract.py` 001C closure contract'ını taşıyor.

001D için aynı modül version bump ile ilerletilebilir.

Ama bump sonrası:

```text
001C closure --verify 45/45
```

hala geçmeli.

Geçmezse history coupling çözülmeden inference yok.

---

# 12. P3 — Prompt v3

Ortak V/VE task:

```text
First identify a printed semantic fact.
Only then create a candidate.
A region alone is not a candidate.
A machine observation row is not a semantic claim.
Do not create one candidate per observation row.
```

Ana kural:

```text
Do not emit a candidate unless it contains at least one semantic claim.
```

---

# 13. No-guess korunur

Semantic-content zorunluluğu hallucination teşvik etmemeli.

Prompt ayrıca:

```text
If you cannot read a semantic fact, omit that candidate.
Do not invent a value merely to satisfy the semantic-content rule.
```

demeli.

---

# 14. VE observation table

Observation table:

```text
optional evidence
```

olarak kalır.

Yasak:

```text
row box → empty candidate
```

Ama observation text'i gerçekten callout okumaya yardımcı oluyorsa kullanılabilir.

Bu evidence etkisinin kendisidir.

---

# 15. P4 — echo metriği v2

VE için iki ayrı sınıf:

```text
empty_echo
contentful_observation_supported
```

`empty_echo` hata/degeneracy.

`contentful_observation_supported` otomatik hata değildir; gold evaluator karar verir.

---

# 16. P4.1 — duplicate metriği

Ölç:

```text
exact region duplicate
near-region duplicate
same semantic signature + same target
same callout repeated
duplicate_rate
maxItems_hit
```

Parser silent dedupe yapmaz.

---

# 17. maxItems

`maxItems=32` safety rail olarak kalabilir.

Ama ana çözüm bu olmamalı.

Ana çözüm:

```text
semantic-empty candidate rejection
```

Candidate count sürekli 32'ye dayanıyorsa degeneracy sinyali.

---

# 18. P5 — 001D dev report

Yeni salt-okur rapor:

```text
formal validity
semantic_claim_count
semantic_candidate_rate
evidence_only_count
empty_echo
contentful observation-supported
duplicates
maxItems hit
gold matches
field accuracy
abstention
overclaim
```

D/V/VE aynı semantic evaluator'u kullanmalı.

---

# 19. Attempt selection

001D dev report yalnız:

```text
current 001D producer identity
```

altındaki attemptleri seçmeli.

001C pass'e fallback yasak.

Geçerli 001D attempt yoksa:

```text
missing / failed
```

raporla.

---

# 20. Static preflight — 0 inference

Canlı çağrıdan önce doğrula:

```text
schema /3
reader /3
run-contract 001d/1
V==VE settings
budget 0/12
final 0/20
001D ledger path
001C closure 45/45
prompt size
ctx headroom
model tag
digest
runtime
```

Dry-run yalnız 4 Round-1 job göstermeli.

---

# 21. İlk inference öncesi test paketi

Minimum:

```text
semantic_candidates
semantic_candidate_reader
001d skeleton
001d semantic-content tests
identity/lifecycle
gates relevant subset
001C closure verify
```

Ayrıca 4 dev D page offline regression.

---

# 22. Full gates

Gates dosyası şu an:

```text
34 passed / ~990 s
```

Semantic contract v3 sonrası ilk live call öncesi tekrar:

```text
34/34
```

koşmak mantıklı.

Yanlış contract ile inference harcamaktan ucuz.

---

# 23. Full pytest

Current 001D HEAD için full-suite kanıt yok.

Zamanlama:

```text
ilk 4 call öncesi:
focused + gates + closure

primary 8 call başarıyla bittikten sonra:
full pytest -q
```

Holdout/freeze'e full suite olmadan geçme.

---

# 24. Bütçe değişmez

```text
dev = 12
final = 20
total = 32
```

Artış yok.

---

# 25. Dev Round 1

İlk dört call:

```text
dev-plate-pocket V
dev-plate-pocket VE
dev-flange-book V
dev-flange-book VE
```

Toplam:

```text
4
```

---

# 26. Round 1 formal gate

4/4:

```text
valid JSON
stop
coordinate valid
refs valid
leak clean
shared settings
current 001D identities
```

---

# 27. Round 1 semantic gate

Her cell:

```text
semantic_claim_count >= 1
```

Ek aggregate gate:

```text
V: en az 1 gold-matched semantic claim
VE: en az 1 gold-matched semantic claim
V semantic field accuracy > 0
VE semantic field accuracy > 0
```

Bu önceden ilan edilmiş düşük sanity gate'tir.

---

# 28. Round 1 başarısızsa

Reserve en fazla:

```text
4 calls
```

kullanılabilir.

Kurallar:

```text
önce offline diagnosis
yalnız bir contract revision
4 Round-1 cell'in tamamı aynı yeni contract ile tekrar
```

Tek hücre retry/cherry-pick yok.

Revision sonrası contract freeze.

---

# 29. Round 1 ikinci kez de geçmezse

001D kapanır.

```text
Round 2 yok
final yok
budget artışı yok
```

Yeni architecture experiment gerekir.

---

# 30. Round 2

Round 1 geçtikten sonra aynı frozen contract:

```text
flange-elbow V
flange-elbow VE
drawing-2 V
drawing-2 VE
```

4 calls.

Round 2 sırasında contract değişikliği yok.

---

# 31. Round 2 fail olursa

```text
no tuning
no retry to pass
```

001D dev sonucu olarak kaydedilir.

Reserve Round 2'yi kurtarmak için kullanılmaz.

---

# 32. Primary 8 acceptance

Holdout'a geçmek için:

```text
formal valid 8/8
semantic_claim_count >=1 8/8
shared settings 8/8
stop 8/8
coordinate 8/8
refs 8/8
leak 0
V field accuracy >0
VE field accuracy >0
```

Ek:

```text
not all outputs maxItems
not all VE outputs empty echoes
```

---

# 33. Overclaim gate

Semantic-content baskısı hallucination üretebilir.

Özellikle say:

```text
invented size
invented count
invented THRU
invented depth
physical overclaim
```

Content artıp overclaim patlarsa başarı sayma.

---

# 34. Üç dev sonucu

## A — V ve VE semantic üretir
Holdout'a geç.

## B — yalnız bir kol semantic üretir
Causal soru eksik kalır; önce analiz et.

## C — ikisi de yine sıfır/yanlış
001D final yok.

---

# 35. Architecture shift gerekirse

Sonraki deney adayları:

```text
crop-first
detect→read staged
OCR-first proposal
one-callout-per-query
typed extraction questions
smaller structured task
```

Bunları 001D içine sıkıştırma.

---

# 36. Holdout

Primary 8 + full pytest sonrası kullanıcıdan:

```text
12–20 yeni technical drawing
```

tercih edilir.

10 final page model output görülmeden seçilir.

---

# 37. Holdout eligibility

```text
repo tarihinde yok
001B/001C/001D dev'de yok
duplicate değil
technical drawing
SEMREAD scope claim içeriyor
```

Hash + group id.

---

# 38. Holdout diversity

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
finite depth
unknown termination
rotated text
multi-view
crowded leaders
low-res raster
clean vector
```

---

# 39. Gold

V/VE output görülmeden.

Reuse:

```text
tracked spec
vision checked
source evidence
target reason
independent corroboration
cycle validation
stable identity
atomic regeneration
```

---

# 40. D baseline

Yeni holdout D:

```text
V/VE finalden önce
```

deterministic koşulur.

Page selection değişmez.

---

# 41. Freeze blockers

```text
001D schema/reader/contract final
primary 8 pass
semantic sanity pass
full pytest 0 fail
holdout 10/10
D baseline
final 0/20
raw V/VE equality
shared settings
model/digest/runtime exact
context preflight
leak audit
clean clone
001C closure verify
```

---

# 42. Final

```text
10 pages × V/VE = 20 calls
retry = 0
```

Final sırasında:

```text
prompt tuning
schema change
sampling change
repair
```

yok.

---

# 43. Final primary metric

```text
semantic_valid_output_rate
```

Tanım:

```text
formal valid
AND
>=1 semantic claim
```

Sonra:

```text
localization
form
size
count
termination
depth
physical
target binding
overclaim
abstention
```

---

# 44. VE evidence analizi

Ayrı raporla:

```text
empty echo
contentful observation-supported
non-observation-supported
```

VE'nin başarısını yalnız table-copy oranıyla karıştırma.

---

# 45. Repo hijyeni checklist

Her milestone:

- [ ] 001C READ-ONLY
- [ ] closure verify gerektiğinde 45/45
- [ ] 001D handoff current HEAD
- [ ] 001D budget current
- [ ] schema/reader/contract versions current
- [ ] root report stale current-state taşımıyor
- [ ] historical facts labelled
- [ ] state/contract/attempt source-of-truth
- [ ] CI yoksa açıkça yazıyor

---

# 46. Commit sırası

```text
1. semantic claim definition + tests
2. semantic-empty wire rejection
3. schema/reader v3 + prompt v3
4. run-contract 001d/1 + identity
5. echo/duplicate/dev-report
6. static preflight + gates
7. Round 1 four calls
8. Round 1 semantic evaluation
9. optional ONE revision + 4-call requalification
10. Round 2 four calls
11. dev report + full pytest
12. holdout intake
13. holdout selection/gold
14. D baseline + clean clone
15. freeze
16. final 20
17. immutable final report
```

---

# 47. ŞİMDİKİ TEK İŞ

**Canlı model çağrısı YOK.**

Şimdi yalnız:

```text
semantic_claim_flags
candidate_has_semantic_claim
semantic-empty wire rejection
schema_semantic_empty failure kind
focused unit tests
```

yap.

Prompt/schema/run-contract bump bir sonraki committe.

---

# 48. İlk commit acceptance

- [ ] 0 inference
- [ ] semantic definition tek kaynak
- [ ] representation-only semantic sayılmıyor
- [ ] target-only semantic sayılmıyor
- [ ] found_circles-only semantic sayılmıyor
- [ ] source-only rejected
- [ ] callout accepted
- [ ] R/Ø accepted
- [ ] size accepted
- [ ] printed count accepted
- [ ] THRU/depth accepted
- [ ] empty response valid abstention
- [ ] failure kind schema_semantic_empty
- [ ] D regression audited
- [ ] focused tests green
- [ ] 001C untouched

---

# 49. İlk live call için absolute blockers

Aşağıdakilerden biri doğruysa inference YOK:

```text
schema still /2
reader still /2
run contract still 001c/1
budget != 0/12
closure verify broken
shared settings broken
semantic-empty tests missing
prompt v3 missing
```

---

# 50. Son yön

Şu an darboğaz:

```text
JSON format
```

değil.

Darboğaz:

```text
semantic claim üretimi
```

Doğru rota:

```text
semantic claim contract
→ v3 identity
→ static tests
→ 4-call Round 1
→ semantic gate
→ contract freeze
→ 4-call Round 2
→ full pytest
→ new holdout
```
