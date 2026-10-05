# PLAN.md — drawingto3d / SEMREAD-001D
## `/3` prompt/schema sonrası: 001D producer identity → dev-report → static preflight → Round 1 semantic proof

**Tarih:** 2026-10-05  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Gözlenen `main` HEAD:** `7d9b0c7ecacea8de4621dc4e61541bd37e47ed53`  
**Aktif deney:** `SEMREAD-001D`  
**Aktif tracked plan:** `docs/PLAN-14.md`  
**001D bütçe:** dev `0/12`, final `0/20`, toplam `0/32`  
**001C:** CLOSED / READ-ONLY HISTORICAL  
**001C closure:** `--verify 45/45`  
**External CI/status:** yok  
**Sıradaki açık kapı:** `semread-001d-run-contract/1` + producer identity

---

# 0. Yönetici özeti

Repo artık 001D'nin semantic-content hipotezini gerçekten kodluyor.

Tamamlanan zincir:

```text
001C immutable closure
→ 001D skeleton + bütçe
→ semantic claim != evidence-only
→ semantic-empty wire rejection
→ schema/reader /3
→ prompt v3
→ no-guess anti-pressure
→ VE observation-row echo yasağı
→ acceptance measurement gate fix
```

Güncel contract parçaları:

```text
candidate schema = semread-candidates/3
reader           = semread-candidate-reader/3
run contract     = HÂLÂ semread-001c-run-contract/1
```

Bu yüzden sıradaki iş canlı model çağrısı değildir.

Doğru sıra:

```text
1. semread-001d-run-contract/1 + producer identity
2. 001D dev-report / semantic-valid metrics
3. static preflight / prompt-context / manifest identity
4. gates + closure + D regression
5. Round 1 = 4 canlı çağrı
6. offline semantic evaluation
7. gate geçerse contract freeze
8. Round 2 = 4 canlı çağrı
9. full pytest
10. ancak sonra bağımsız holdout
```

---

# 1. Son repo kontrolü

## 1.1 `/3` schema + reader tamamlandı

Current:

```text
semread-candidates/3
semread-candidate-reader/3
```

001D anlamı:

```text
semantic-empty candidate invalid
semantic claim != evidence-only
semantic-first prompt
no-guess korunur
```

Parser eski `/2` wire response'u kabul etmez.

## 1.2 Prompt v3 tamamlandı

Ortak V/VE prompt artık semantic-first çalışıyor:

```text
First identify a printed semantic fact.
Only then create a candidate.
A region alone is not a candidate.
A machine observation row is not a semantic claim.
Do not emit a candidate unless it contains at least one semantic claim.
```

Ayrıca:

```text
If you cannot read at least one semantic fact, emit no candidate.
Do not invent a semantic fact merely to satisfy the semantic-content requirement.
```

ile hallucination baskısı sınırlanıyor.

## 1.3 VE evidence contract tamamlandı

VE bölümü:

```text
Observations are evidence, not candidate seeds.
Do not create one candidate per observation row.
Use an observation only if it helps support a semantic claim.
```

V/VE common task aynı; fark yalnız evidence katmanı.

---

# 2. Semantic-content tek kaynak

Repo:

```text
semantic_claim_flags
candidate_has_semantic_claim
evidence_flags
```

fonksiyonlarını tek kaynak olarak kullanıyor.

Semantic claim:

```text
callout text
R / Ø
known size
printed count
explicit termination
known depth
supported physical meaning
```

Evidence-only:

```text
representation
found circles
target state
observation id
source region
uncertainty
```

Tek başına gate geçiremez.

---

# 3. Wire semantic-empty reddi

Şu gövde artık invalid:

```text
candidate_id
source.region
representation / target / observation evidence
ama semantic claim yok
```

Failure subtype:

```text
schema_semantic_empty
```

Sessiz tamir yok.

Boş `items=[]` abstention olarak geçerli kalır.

---

# 4. D yolu korunuyor

Semantic-empty rule wire parser sınırında.

D parser'a girmeden `Candidate` kuruyor.

D regresyon kanıtı historical kayıtla aynı:

```text
53 aday
53 content-bearing
2 match
%9.1 localization
%66.7 field accuracy
```

001D wire değişikliği D'yi kırmamış durumda.

---

# 5. Acceptance bonus koşusunda bulunan gerçek kusur

Zorunlu listedeki testlerin dışında 001B acceptance suite de koşuldu.

İlk sonuç:

```text
1 failed / 25 passed
```

Bulunan kusur:

```text
aggregates boş
ama comparison.vs_d sıfır satırlar taşıyor
→ measured=True
→ B06 ölçüm yokken kapanabiliyor
```

Bu gerçek evaluator/acceptance bug'ıydı.

---

# 6. Acceptance düzeltmesi

Tek kaynak:

```text
arms_with_measurement(payload)
```

eklendi.

Ölçüm kriteri:

```text
en az bir scorable_target_count > 0
```

Sıfır satırlı `vs_d` artık ölçüm sayılmıyor.

Düzeltme sonrası acceptance suite:

```text
27 passed
~31:48
```

Tek-test arka plan koşusunun harness tarafından öldürülmesi kanıt sayılmadı; tam suite sonucu authority kabul edildi.

---

# 7. Repo hygiene durumu

`report.md` artık experiment-neutral living report.

Current:

```text
SEMREAD-001D active
```

001C:

```text
HISTORICAL
READ-ONLY
```

olarak tutuluyor.

Handoff da aynı current facts'i taşıyor:

```text
OPEN GATE = semread-001d-run-contract/1 + producer identity
NEXT = run-contract → dev report → static preflight → Round 1
```

Bu plan bu kayıtla uyumlu.

---

# 8. EN KRİTİK AÇIK — producer identity

Semantic behavior değişti ama current run contract hâlâ:

```text
semread-001c-run-contract/1
```

Bu haliyle inference yapmak yasak.

Çünkü:

```text
experiment = 001D
producer contract = 001C
```

olur ve provenance/reproducibility bozulur.

---

# 9. P1 — `semread-001d-run-contract/1`

Bir sonraki commit:

```text
CONTRACT_VERSION = semread-001d-run-contract/1
```

olmalı.

Docstring current contract'ı:

```text
SEMREAD-001D
semantic-content-aware full-page V/VE experiment
```

olarak anlatmalı.

001C history closure artifact'ında kalır.

---

# 10. Generation envelope DEĞİŞMEZ

Run-contract bump sırasında:

```text
model
digest
runtime
num_ctx
num_predict
temperature
repeat_penalty
repeat_last_n
image_max_side
timeout hierarchy
```

değiştirilmez.

Current shared envelope:

```text
model          qwen3-vl:8b-instruct
runtime        0.32.1
num_ctx        22528
num_predict    8192
temperature    0.0
repeat_penalty 1.25
repeat_last_n  512
maxItems       32
image_max_side 1280
```

001D'nin test ettiği şey semantic-content-aware contract olmalı.

---

# 11. V/VE causal invariant

Şart:

```text
generation_settings(V) == generation_settings(VE)
```

İzin verilen fark:

```text
evidence_mode
overlay
observation table
evidence prompt section
image count
```

Bunun dışındaki fark blocker.

---

# 12. Producer identity bump

Yeni producer identity şunları bağlamalı:

```text
schema /3
reader /3
prompt v3
semantic-empty parser behavior
run-contract 001d/1
```

Attempt manifest ayrıca açıkça:

```text
experiment
schema_version
reader_version
contract_version
producer_identity
preprocessing_identity
```

taşımalı.

---

# 13. Dry-run manifest acceptance

İlk canlı call öncesi dry-run manifest:

```text
experiment = semread-001d
phase = dev
schema = semread-candidates/3
reader = semread-candidate-reader/3
contract = semread-001d-run-contract/1
```

olmalı.

Eski 001C identity current attempt manifestinde görünürse gönderim bloklanmalı.

---

# 14. 001C closure coupling

Current source hash'lerinin değişmesi normal.

Ama historical closure:

```text
eval/semread_001c_closure.py --verify
```

hala:

```text
45/45
```

geçmeli.

Geçmezse inference yok.

---

# 15. P1 acceptance — run-contract commit

- [ ] 0 inference
- [ ] `semread-001d-run-contract/1`
- [ ] schema `/3`
- [ ] reader `/3`
- [ ] docstring current 001D
- [ ] model unchanged
- [ ] digest unchanged
- [ ] runtime unchanged
- [ ] generation settings unchanged
- [ ] V==VE invariant
- [ ] producer identity changed
- [ ] budget `0/12 + 0/20`
- [ ] dry-run manifest current identities
- [ ] closure `45/45`
- [ ] report + handoff birlikte güncel

---

# 16. P2 — 001D dev-report katmanı

Run-contract identity kapanınca sıradaki iş:

```text
001D dev-report
```

Inference yok.

Source-of-truth:

```text
attempt manifests
result.json
response-parsed.json
resources.json
budget state
```

`report.md` source-of-truth değildir.

---

# 17. Attempt selection

Yalnız:

```text
experiment = semread-001d
current producer_identity
current schema/reader/contract
```

ile uyumlu attempt seç.

001B/001C fallback yok.

Attempt yoksa:

```text
missing
```

---

# 18. Formal metrics

Her cell:

```text
attempt state
done_reason
parse valid
coordinate valid
references valid
leak clean
shared settings
producer identity
candidate count
maxItems hit
```

---

# 19. Semantic metrics

Her cell:

```text
semantic_claim_count
semantic_candidate_rate
semantic field fill
evidence_only_count
gold matched claims
field accuracy
abstention
overclaim
```

Semantic logic doğrudan `semantic_claim_flags` reuse etmeli.

---

# 20. VE echo metric v2

İki sınıf:

```text
empty_echo
contentful_observation_supported
```

`empty_echo` valid response içinde normalde bulunmamalı; parser semantic-empty reddeder.

`contentful_observation_supported` otomatik hata değildir; gold doğruluğu belirler.

---

# 21. Duplicate metric

Ölç:

```text
exact region duplicate
near-region duplicate
same semantic signature + same target
same callout repeated
```

Parser dedupe etmez; report eder.

---

# 22. Measurement gate dersi

001B acceptance bug tekrar edilmemeli.

Şu:

```text
comparison satırı var
```

tek başına measurement değildir.

001D report completion gerçek scorable measurement gerektirmeli.

---

# 23. P2 acceptance — dev report

- [ ] 0 inference
- [ ] only 001D attempts
- [ ] producer identity filtering
- [ ] formal metrics
- [ ] semantic metrics
- [ ] semantic helper reused
- [ ] echo v2
- [ ] duplicate metrics
- [ ] real measurement gate
- [ ] zero-row fake completion impossible
- [ ] tests green

---

# 24. P3 — static preflight

Dev-report sonrası live call öncesi static preflight.

0 inference.

Kontrol:

```text
schema /3
reader /3
contract 001d/1
budget 0/12
final 0/20
001D attempt root
producer identity
V==VE settings
prompt identity
model tag/digest/runtime
context headroom
001C closure
```

---

# 25. Prompt/context measurement

Round 1 dört cell için model çağırmadan:

```text
plate-pocket V
plate-pocket VE
flange-book V
flange-book VE
```

prompt serialize et.

Kaydet:

```text
prompt bytes
prompt token estimate
image bytes
observation rows
num_ctx
num_predict
headroom
```

---

# 26. Context gate

Prompt v3 büyüdü.

Bu yüzden `num_ctx=22528` otomatik güvenli kabul edilmez.

Gate:

```text
prompt_tokens + output_budget <= context
```

Yetersizse canlı call yok.

---

# 27. Backend schema compatibility

`anyOf` bilinçli olarak eklenmedi; bu doğru.

Structured-output backend'in current schema'yı kabul ettiği inference olmadan mümkün olan static/synthetic yolla doğrulanmalı.

---

# 28. P3 acceptance — static preflight

- [ ] 0 inference
- [ ] exactly 4 Round-1 dry-run jobs
- [ ] correct identities
- [ ] context headroom
- [ ] V/VE common task invariant
- [ ] shared settings invariant
- [ ] model/digest/runtime exact
- [ ] budget `0/12`
- [ ] closure `45/45`
- [ ] no 001C writes
- [ ] dry-run manifest preserved

---

# 29. Pre-live test gate

İlk live call öncesi:

```text
focused semantic tests
prompt-v3 tests
001D identity tests
dev-report tests
lifecycle/identity
gates
001C closure
D regression
```

geçmeli.

Run-contract/dev-report değişiklikleri sonrası gates tekrar:

```text
34/34
```

olmalı.

---

# 30. Full pytest zamanlaması

İlk Round 1 öncesi full suite zorunlu değil.

Şu yeterli:

```text
focused + gates + closure + D regression
```

Primary dev 8 tamamlandığında:

```text
pytest -q
```

zorunlu.

---

# 31. Dev budget

Değişmez:

```text
dev   12
final 20
total 32
```

Budget creep yok.

---

# 32. Round 1 — ilk canlı inference

Yalnız preflight kapanınca:

```text
dev-plate-pocket-V
dev-plate-pocket-VE
dev-flange-book-V
dev-flange-book-VE
```

Toplam 4 call.

---

# 33. Dispatch politikası

Tercih sequential.

Sebep:

```text
Ollama queue
server-side uzun request
manual kill ambiguity
```

001C'de bunlar yaşandı.

İlk semantic proof'ta concurrency gereksiz.

---

# 34. Round 1 formal gate

Her 4 cell:

```text
pass
done_reason=stop
coordinate valid
refs valid
leak clean
shared settings
correct producer identity
```

---

# 35. Round 1 semantic gate

Her cell:

```text
semantic_claim_count >= 1
```

Aggregate:

```text
V >=1 gold-matched semantic claim
VE >=1 gold-matched semantic claim
V field accuracy > 0
VE field accuracy > 0
```

---

# 36. Semantic-valid output

Tanım:

```text
semantic_valid_output =
formal valid
AND
semantic_claim_count >= 1
```

Round 1 hedef/gate:

```text
4/4
```

---

# 37. Overclaim gate

Özellikle say:

```text
invented size
invented count
invented R/Ø
invented THRU
invented depth
unsupported physical meaning
```

Semantic fill artışı tek başına başarı değildir.

---

# 38. Round 1 başarısızsa

Önce 0-inference offline diagnosis.

Reserve:

```text
4 calls
```

var.

Ama yalnız **ONE contract revision** için kullanılabilir.

---

# 39. Requalification şekli

Revision sonrası yalnız kötü cell değil:

```text
Round 1'in tüm 4 cell'i
```

aynı contract ile tekrar koşulur.

Cherry-pick yok.

---

# 40. Round 1 ikinci kez geçmezse

001D kapanır:

```text
Round 2 yok
holdout yok
final yok
budget artışı yok
```

Yeni experiment `001E` gerekir.

---

# 41. Round 2

Round 1 gate geçerse contract freeze.

Sonra:

```text
dev-flange-elbow V
dev-flange-elbow VE
dev-drawing-2 V
dev-drawing-2 VE
```

4 call.

Round 2 sırasında tuning yok.

---

# 42. Primary 8 final dev gate

Holdout'a geçmek için:

```text
formal valid 8/8
semantic-valid 8/8
stop 8/8
coordinate 8/8
refs 8/8
leak clean
shared settings 8/8
V field accuracy > 0
VE field accuracy > 0
```

---

# 43. Degeneracy blockers

Holdout yok eğer:

```text
all outputs maxItems
duplicate flood dominates
all VE candidates table-copy behavior
one arm semantic content = 0
semantic claims mostly fabricated
```

---

# 44. Primary 8 sonrası full suite

Çalıştır:

```bash
.venv/bin/python -m pytest -q
```

Kaydet:

```text
passed
failed
runtime
collection count
```

0 fail.

---

# 45. External CI

Gözlenen HEAD için GitHub status yok.

Report açıkça:

```text
External CI: none
Acceptance evidence: local pytest + eval artifacts
```

demeli.

---

# 46. Repo hygiene milestone

Her milestone sonrası:

```text
report.md
HERMES_SEMREAD_001D_HANDOFF.md
PLAN
budget state
contract version
```

aynı current facts'i taşımalı.

Özellikle:

```text
HEAD
schema/reader/contract
budget
latest gate
next single step
```

uyumlu olmalı.

---

# 47. 001C read-only invariant

Şunlara yazma yok:

```text
out/lab/semread-001c/**
docs/HERMES_SEMREAD_001C_HANDOFF.md
historical attempt artifacts
```

Closure verify bunu korur.

---

# 48. Plan history

Bu yeni plan repo authority olacaksa yeni history entry tercih edilir:

```text
docs/PLAN-15.md
```

PLAN-14 geçmiş olarak korunmalı.

---

# 49. Holdout'a ne zaman geçilir?

Yalnız:

```text
Primary 8 dev gate
+
full pytest 0 fail
```

sonrası.

---

# 50. Holdout kaynağı

Mevcut repo örnekleri unseen değildir.

Kullanıcıdan tercihen:

```text
12–20 yeni teknik çizim
```

alınır.

Model çalıştırılmadan 10 final page seçilir.

---

# 51. Holdout eligibility

```text
repo history'de yok
001B/001C/001D dev'de yok
duplicate değil
technical drawing
SEMREAD-scope callout var
```

Hash + group id.

---

# 52. Holdout gold

V/VE output görülmeden hazırlanır.

Reuse:

```text
tracked specs
vision_checked
source evidence
target reason
independent corroboration
cycle validation
stable identity
atomic freeze
```

---

# 53. Final freeze

Freeze bağlar:

```text
git HEAD
schema /3
reader /3
001d-run-contract/1
producer identity
evaluation identity
prompt identity
model/digest/runtime
shared generation settings
preprocessing identity
gold identity
D baseline
budget 0/20
```

---

# 54. Final 20

```text
10 page × V/VE
20 calls
retry = 0
```

Final sırasında contract değişmez.

---

# 55. Final metrics

Önce:

```text
formal_valid_output_rate
semantic_valid_output_rate
```

Sonra:

```text
localization
callout text
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

# 56. VE evidence metrics

```text
empty_echo
contentful_observation_supported
non-observation-supported
duplicate rate
```

raporlanmalı.

---

# 57. Karar ağacı

## V ve VE semantic üretiyorsa

001D final experiment anlamlı.

## yalnız V

VE evidence formatı zararlı olabilir.

## yalnız VE

Observation evidence kritik olabilir.

## ikisi de 0'a yakın

Full-page one-shot architecture uygun değil.

Sonraki experiment:

```text
crop-first
detect→read
OCR-first
one-callout-per-query
typed subquestions
```

---

# 58. Bu aşamada YAPMA

```text
live inference before 001d/1 identity
sampling sweep
model değiştirme
num_ctx kör artırma
single-cell retry
budget artırma
silent dedupe
coordinate repair
semantic-empty repair
anyOf complexity without backend evidence
holdout inference
CAD/planner work
```

---

# 59. Commit planı

Güncel HEAD sonrası:

```text
1. semread-001d: run-contract /1 + producer identity
2. semread-001d: dev-report semantic/echo/duplicate metrics
3. semread-001d: static preflight + dry-run manifest/context
4. semread-001d: pre-live focused/gates/closure evidence
5. semread-001d: Round 1 four calls
6. semread-001d: Round 1 semantic report
7. optional ONE revision + four-call requalification
8. semread-001d: Round 2 four calls
9. semread-001d: primary 8 dev report + full pytest
10. holdout intake/selection
11. gold
12. D baseline + clean clone
13. freeze
14. final 20
15. immutable final report
```

---

# 60. ŞİMDİKİ TEK SOMUT İŞ

**0 inference.**

Şimdi yalnız:

```text
CONTRACT_VERSION = semread-001d-run-contract/1
```

ve producer identity ayrımı yapılmalı.

Generation settings değiştirilmemeli.

---

# 61. Şimdiki commit acceptance

- [ ] 0 inference
- [ ] contract = `semread-001d-run-contract/1`
- [ ] schema = `semread-candidates/3`
- [ ] reader = `semread-candidate-reader/3`
- [ ] experiment manifest = `semread-001d`
- [ ] producer identity new
- [ ] V==VE generation settings
- [ ] model/digest/runtime unchanged
- [ ] budget `0/12 + 0/20`
- [ ] dry-run manifest current identities
- [ ] 001C closure `45/45`
- [ ] focused tests green
- [ ] report/handoff updated together

---

# 62. Bir sonraki aşama

Contract identity kapanınca:

```text
dev-report
→ static preflight
```

Bu ikisi de 0 inference ile kapanmalı.

Ancak sonra ilk:

```text
4 live calls
```

başlar.

---

# 63. Son yön

Şu an repo ilk kez şu noktaya geldi:

```text
semantic contract kodda
semantic contract promptta
semantic contract schemada
```

Eksik kalan parça:

```text
semantic contract'ın 001D producer identity olarak dondurulması
```

Doğru kısa rota:

```text
001d/1 identity
→ dev-report
→ static preflight
→ Round 1
→ semantic proof
```
