# PLAN.md — drawingto3d / SEMREAD-001D
## Static preflight yeşil sonrası: Round 1 → offline semantic evaluation → tek karar noktası

**Tarih:** 2026-10-06
**Repo:** `AhmetAydemir1/drawingto3d`
**Gözlenen `main` HEAD:** `8efbec0e82e3dfab09fdd116f04d6415829f20c9`
**Aktif deney:** `SEMREAD-001D`
**Aktif tracked plan:** `docs/PLAN-18.md`
**Önerilen yeni history entry:** `docs/PLAN-19.md`
**Schema:** `semread-candidates/3`
**Reader:** `semread-candidate-reader/3`
**Run contract:** `semread-001d-run-contract/2`
**001D bütçe:** dev `0/12`, final `0/20`
**001C:** CLOSED / READ-ONLY
**001C closure:** `45/45`
**Static preflight:** `10/10 GREEN`
**Round 1:** henüz başlamadı
**External CI/status:** yok

---

# 0. Yönetici özeti

Hazırlık fazı artık tamamlandı.

Kapanan işler:

```text
semantic-content validator
→ schema/reader /3
→ prompt v3
→ run-contract 001d/1
→ dev-report
→ deterministic dev inputs
→ raw V/VE byte identity
→ static preflight
→ measured num_ctx revision
→ run-contract 001d/2
→ input cache rebuild
→ preflight 10/10 GREEN
```

Current measured envelope:

```text
model            qwen3-vl:8b-instruct
runtime          0.32.1
num_ctx          24576
num_predict      8192
temperature      0.0
repeat_penalty   1.25
repeat_last_n    512
image_max_side   1280
maxItems         32
```

Tek değişiklik:

```text
num_ctx 22528 → 24576
```

Bu değişiklik ilk canlı çağrıdan önce, static preflight kanıtıyla yapılmıştır.

Preflight sonucu:

```text
planned_real_calls = 4
all checks = 10/10 green
flange-book-VE headroom = +1140
other Round-1 cells = positive
budget = 0/12
```

Dolayısıyla sıradaki gerçek iş:

```text
ROUND 1 — TAM 4 CANLI ÇAĞRI
```

---

# 1. Repo kontrolü — current facts

Güncel HEAD:

```text
8efbec0e82e3dfab09fdd116f04d6415829f20c9
```

Current identities:

```text
experiment = semread-001d
schema     = semread-candidates/3
reader     = semread-candidate-reader/3
contract   = semread-001d-run-contract/2
```

Producer identity `/2` revizyonuyla yenilenmiş durumda.

---

# 2. report.md durumu

Living report current state'i doğru taşıyor:

```text
001D active
dev budget 0/12
final 0/20
contract 001d/2
num_ctx 24576
dev-report ready
dev inputs ready
preflight 10/10 green
next = Round 1
```

---

# 3. Handoff durumu

Handoff'ta `/1 → /2` pre-inference revision kayıtlı.

Kayıt açıkça:

```text
0 inference before revision
no invalidated attempts
preflight /2 green
planned_real_calls 4
next single step = Round 1
```

diyor.

---

# 4. Static preflight kanıtı

Preflight current `/2` için:

```text
10/10 GREEN
ok = true
```

Critical cell:

```text
dev-flange-book-VE
prompt estimate = 15244
num_predict     = 8192
required        = 23436
num_ctx         = 24576
headroom        = +1140
```

---

# 5. Input identity

Dört dev page current producer/preprocessing identity ile yeniden bağlanmış.

Kayıt:

```text
input-identity.json
contract /2
```

Prepared PNG'ler byte-stable.

001B/001C cross-check aynı raw page bytes'ı doğruluyor.

---

# 6. V/VE causal invariant

Round 1 boyunca:

```text
generation_settings(V) == generation_settings(VE)
```

zorunlu.

Tek fark:

```text
VE evidence
```

yani overlay + observation table + evidence prompt section.

---

# 7. Bütçe politikası

Current:

```text
dev used = 0
dev cap  = 12
final used = 0
final cap  = 20
```

Dev budget dağılımı:

```text
8 primary
4 one-revision requalification reserve
```

Round 1 sonunda beklenen:

```text
dev used = 4/12
```

---

# 8. ŞİMDİKİ TEK İŞ — Round 1

Exactly:

```text
dev-plate-pocket V
dev-plate-pocket VE
dev-flange-book V
dev-flange-book VE
```

Bunların dışında çağrı yok.

---

# 9. Dispatch sırası

Sequential çalıştır:

```text
1. plate-pocket V
2. plate-pocket VE
3. flange-book V
4. flange-book VE
```

Parallel dispatch yok.

---

# 10. Session hygiene

İlk call öncesi:

```text
active Ollama request = none
queue = empty
model = qwen3-vl:8b-instruct
digest exact
runtime = 0.32.1
```

Mismatch varsa gönderim yok.

---

# 11. Pre-dispatch invariant

İlk request öncesi:

```text
corpus/static-preflight.json
ok == true
contract == semread-001d-run-contract/2
planned_real_calls == 4
```

olmalı.

---

# 12. Attempt lifecycle

Her call için sıra:

```text
reserve budget
create attempt directory
persist request manifest
persist input identity
persist producer identity
persist generation settings
then send
```

Gönderilmiş request başarısız olsa bile budget sayılır.

---

# 13. Manual kill YOK

Canlı call başladıktan sonra:

```text
manual kill
ad-hoc timeout
restart-and-retry
```

yapma.

---

# 14. Retry YOK

Round 1 sırasında:

```text
bad output → immediate retry
transport failure → retry
single-cell redo
```

yasak.

İlk dört call first-shot result'tur.

---

# 15. Round 1 tamamlanınca ilk iş

Yeni inference yapmadan:

```text
eval/semread_001d_dev_report.py
```

çalıştır.

---

# 16. Formal gate

Her dört cell:

```text
send_attempted = true
done_reason = stop
parse valid
coordinate valid
refs valid
leak clean
correct producer identity
shared generation settings
```

Gate:

```text
formal_valid = 4/4
```

---

# 17. Semantic gate

Her cell:

```text
semantic_claim_count >= 1
```

Gate:

```text
semantic_valid_output = 4/4
```

---

# 18. Gold sanity gate

Aggregate:

```text
V >= 1 gold-matched semantic claim
VE >= 1 gold-matched semantic claim
V field accuracy > 0
VE field accuracy > 0
```

---

# 19. Semantic-valid tanımı

```text
semantic_valid_output =
    formal_valid
    AND semantic_claim_count >= 1
```

---

# 20. Empty abstention

Model:

```json
{"items":[]}
```

döndürürse:

```text
formal valid olabilir
semantic_valid = false
```

---

# 21. Overclaim guard

Ayrı ölç:

```text
invented R/Ø
invented size
invented count
invented THRU
invented depth
unsupported physical meaning
```

---

# 22. Duplicate guard

Report:

```text
exact duplicate
near duplicate
same semantic signature + same target
same callout repeated
```

ölçmeli.

---

# 23. VE echo guard

Ölç:

```text
empty_echo
contentful_observation_supported
```

---

# 24. maxItems guard

```text
candidate_count == 32
```

ise:

```text
max_items_hit = true
```

---

# 25. Round 1 başarı koşulu

Round 1 başarılı sayılırsa:

```text
formal valid 4/4
semantic-valid 4/4
V gold-matched >= 1
VE gold-matched >= 1
V field accuracy > 0
VE field accuracy > 0
```

---

# 26. Round 1 geçerse

Yeni inference yapmadan önce current dev contract freeze kaydı oluştur:

```text
001d/2
schema /3
reader /3
producer identity
preprocessing identity
input identity
generation settings
Round-1 selected attempts
```

Sonra Round 2 açılır.

---

# 27. Round 2

Round 1 başarıyla geçerse:

```text
dev-flange-elbow V
dev-flange-elbow VE
dev-drawing-2 V
dev-drawing-2 VE
```

4 call.

Aynı contract.

---

# 28. Round 2'de tuning YOK

Round 2 sırasında:

```text
prompt change
schema change
num_ctx change
sampling change
parser change
```

yasak.

---

# 29. Round 1 FAIL olursa

Yeni call yapmadan:

```text
offline forensic diagnosis
```

yap.

İncelenecek:

```text
raw response
failure kind
done_reason
eval_count
semantic claim fields
duplicate behavior
echo behavior
overclaim
localization
```

---

# 30. Reserve policy

Round 1 fail olursa en fazla:

```text
4 reserve calls
```

kullanılabilir.

Ama yalnız:

```text
ONE declared contract revision
```

sonrası.

---

# 31. Tek revision hakkı

Revision generic contract hypothesis olmalı.

Yasak:

```text
page-specific prompt
single-cell hack
gold value
sampling sweep
model switch
retry until pass
```

---

# 32. Requalification şekli

Revision sonrası:

```text
same 4 Round-1 cells
```

tamamı yeniden koşulur.

Tek kötü cell redo edilmez.

---

# 33. Round 1 ikinci kez fail olursa

001D kapanır:

```text
Round 2 yok
holdout yok
final yok
budget artışı yok
```

Yeni experiment:

```text
SEMREAD-001E
```

---

# 34. Primary 8 gate

Round 2 sonrası holdout'a geçmek için:

```text
formal valid 8/8
semantic-valid 8/8
stop 8/8
coordinate 8/8
refs 8/8
leak clean 8/8
shared settings 8/8
V accuracy > 0
VE accuracy > 0
```

---

# 35. Degeneracy blockers

Holdout yok eğer:

```text
duplicate flood dominates
all outputs maxItems
VE table-copy dominates
semantic claims mostly fabricated
one arm semantic accuracy = 0
```

---

# 36. Primary 8 sonrası full pytest

Çalıştır:

```bash
.venv/bin/python -m pytest -q
```

Şart:

```text
0 fail
```

---

# 37. Repo hygiene

Round 1 sonrası:

```text
report.md
HERMES_SEMREAD_001D_HANDOFF.md
dev-report
budget state
```

aynı current facts'i taşımalı.

---

# 38. PLAN history

Bu plan repo authority yapılacaksa:

```text
docs/PLAN-19.md
```

olarak yeni history entry tercih et.

PLAN-18 overwrite edilmemeli.

---

# 39. 001C invariant

001C READ-ONLY.

Milestone sonrası:

```text
closure verify 45/45
```

korunmalı.

---

# 40. Round 1 artifact checklist

Her attempt için:

- [ ] request manifest
- [ ] input identity
- [ ] producer identity
- [ ] preprocessing identity
- [ ] model/digest/runtime
- [ ] generation settings
- [ ] raw response
- [ ] parsed response if valid
- [ ] resources
- [ ] done_reason
- [ ] budget disposition
- [ ] failure subtype if any

---

# 41. Round 1 report checklist

- [ ] four cells accounted
- [ ] formal-valid count
- [ ] semantic-valid count
- [ ] gold matches
- [ ] field accuracy
- [ ] overclaim
- [ ] duplicates
- [ ] VE echo metrics
- [ ] maxItems hits
- [ ] latency
- [ ] prompt/eval token counts
- [ ] no retry
- [ ] current producer only

---

# 42. PASS/FAIL karar ağacı

## 4/4 formal + semantic, gold sanity > 0

Round 1 PASS → contract dev-freeze → Round 2.

## Formal 4/4 ama semantic < 4/4

Round 1 FAIL → offline diagnosis → optional one revision.

## Semantic 4/4 ama gold accuracy = 0

Round 1 FAIL → semantic-looking hallucination/irrelevance analizi.

## V geçer, VE kalır

Round 1 FAIL → VE evidence forensic.

## VE geçer, V kalır

Round 1 FAIL → raw-image arm forensic.

---

# 43. Holdout zamanı

Yalnız:

```text
Primary 8 pass
+
full pytest 0 fail
```

sonrası.

---

# 44. Freeze

Final freeze bağlamalı:

```text
git HEAD
schema /3
reader /3
contract 001d/2
producer identity
evaluation identity
preprocessing identity
prompt identity
model/digest/runtime
generation settings
gold identity
D baseline
final budget 0/20
```

---

# 45. Final

```text
10 page × V/VE = 20 calls
retry = 0
```

---

# 46. Şu anda YAPMA

```text
başka preflight tuning
num_ctx tekrar artırma
model değiştirme
sampling sweep
single-cell retry
Round 2'yi Round 1 raporundan önce başlatma
budget artırma
001C fallback
silent repair
holdout inference
CAD/planner'a dönme
```

---

# 47. Commit planı

Current HEAD sonrası:

```text
1. semread-001d: Round 1 four live calls
2. semread-001d: Round 1 dev-report + forensic summary
3a. PASS → contract dev-freeze + Round 2
3b. FAIL → offline diagnosis + optional ONE revision
4. Round 2 four live calls
5. primary-8 report + full pytest
6. holdout intake/selection
7. gold
8. D baseline + clean clone
9. freeze
10. final 20
11. immutable final report
```

---

# 48. ŞİMDİKİ TEK SOMUT İŞ

**Round 1 — dört canlı çağrı.**

Exactly:

```text
dev-plate-pocket V
dev-plate-pocket VE
dev-flange-book V
dev-flange-book VE
```

Başka call yok.

---

# 49. Round 1 öncesi son acceptance

- [ ] contract `001d/2`
- [ ] schema `/3`
- [ ] reader `/3`
- [ ] static preflight `10/10 GREEN`
- [ ] `planned_real_calls = 4`
- [ ] budget `0/12`
- [ ] final `0/20`
- [ ] input cache current `/2`
- [ ] V/VE raw bytes identical
- [ ] model/digest/runtime exact
- [ ] shared generation settings
- [ ] closure `45/45`
- [ ] gates `34/34`
- [ ] no active Ollama request
- [ ] no retry policy
- [ ] report/handoff current

---

# 50. Son yön

Hazırlık katmanında daha fazla kalmamalıyız.

Şu an:

```text
contract
identity
inputs
evaluator
preflight
budget
tests
```

hazır.

Bilimsel olarak sıradaki anlamlı bilgi ancak canlı Round 1'den gelecek.

Doğru kısa rota:

```text
4 live calls
→ offline dev-report
→ PASS/FAIL decision
```
