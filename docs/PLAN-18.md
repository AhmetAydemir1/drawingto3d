# PLAN.md — drawingto3d / SEMREAD-001D
## Güncel rota: dev-report → dev input kurulumu → static preflight → Round 1 semantic proof

**Tarih:** 2026-10-05
**Repo:** `AhmetAydemir1/drawingto3d`
**Gözlenen `main` HEAD:** `b2e12182a05c2e8f8176008de63d7a1cd87bd226`
**Aktif deney:** `SEMREAD-001D`
**Aktif tracked plan:** `docs/PLAN-15.md`
**Önerilen yeni plan history entry:** `docs/PLAN-16.md`
**001D bütçe:** dev `0/12`, final `0/20`, toplam `0/32`
**001C:** CLOSED / READ-ONLY HISTORICAL
**001C closure:** `45/45`
**External CI/status:** yok
**İlk canlı 001D inference:** yapılmadı

---

# 0. Yönetici özeti

Önceki plandaki en kritik blocker kapanmış durumda:

```text
semread-candidates/3
semread-candidate-reader/3
semread-001d-run-contract/1
```

üçü de current.

Ayrıca attempt manifest identity alanları, producer/preprocessing identity, dry-run identity checks ve `blocked_contract_identity` gönderim bloğu uygulanmış.

Üretim zarfı 001C kapanışından birebir korunuyor:

```text
model          qwen3-vl:8b-instruct
runtime        0.32.1
num_ctx        22528
num_predict    8192
temperature    0.0
repeat_penalty 1.25
repeat_last_n  512
image_max_side 1280
maxItems       32
```

V/VE generation settings aynı.

Güncel gerçek açık kapı:

```text
1. 001D dev-report / gate katmanı
2. 001D dev input/corpus PNG kurulumu
3. static preflight
4. Round 1 — tam 4 canlı çağrı
```

Önemli ayrım:

- Kimlik dry-run'ı dört Round-1 hücresinin manifestini doğru kurabiliyor.
- Gerçek CLI dry-run `planned_real_calls = 0` veriyor.
- Bunun nedeni 001D corpus PNG/input'larının henüz kurulmamış olması.

Dolayısıyla canlı inference'a geçmeden önce evaluator/gate tanımı, input bytes ve preflight tamamlanmalı.

---

# 1. Report + handoff kontrolü

`report.md` ve `docs/HERMES_SEMREAD_001D_HANDOFF.md` şu current facts üzerinde uyumlu:

```text
active experiment = SEMREAD-001D
schema /3
reader /3
contract 001d/1
dev budget = 0/12
final budget = 0/20
001C closure = 45/45
next = dev-report → static preflight → Round 1
```

Bu uyum korunmalı.

---

# 2. Repo hijyeni invariantı

001C:

```text
READ-ONLY HISTORICAL
```

kalır.

Dokunulmaz:

```text
docs/HERMES_SEMREAD_001C_HANDOFF.md
out/lab/semread-001c/**
eval/semread_001c_closure.json
historical attempts
```

Milestone'larda closure verifier:

```text
45/45
```

geçmeli.

---

# 3. Plan history

Current tracked plan:

```text
docs/PLAN-15.md
```

Bu yeni plan repo authority yapılacaksa:

```text
docs/PLAN-16.md
```

olarak yeni history entry oluştur.

PLAN-15 overwrite edilmemeli.

---

# 4. Current producer contract

Current:

```text
schema   = semread-candidates/3
reader   = semread-candidate-reader/3
contract = semread-001d-run-contract/1
```

Attempt manifest artık:

```text
experiment
schema_version
reader_version
contract_version
producer_identity
preprocessing_identity
```

taşıyor.

Yanlış current identity ile gönderim:

```text
blocked_contract_identity
```

ile inference harcamadan duruyor.

---

# 5. Current test evidence

Son kayıtlı kanıt:

```text
focused suite        101 passed
quick SEMREAD         119 passed
gates                 34/34
001C closure          45/45
check_tables          21 / 0 mismatch
001D inference         0
```

External GitHub commit status yok.

Authority:

```text
local pytest
eval tools
attempt artifacts
closure verifier
```

---

# 6. Şimdiki tek iş — dev-report

Repo'da:

```text
eval/semread_001d_dev_report.py
```

henüz yok.

Bu sıradaki tek somut iştir.

Neden inference öncesi yazılmalı?

Çünkü Round 1 sonuçlarını gördükten sonra şu tanımları değiştirmek bilimsel olarak sorun yaratır:

```text
eligible attempt
formal pass
semantic-valid
measurement
echo
duplicate
overclaim
gate
```

Bunlar sonuçlardan önce dondurulmalı.

---

# 7. P1 — dev-report

Yeni salt-okur araç:

```text
eval/semread_001d_dev_report.py
```

Görev:

```text
current 001D attempt seçimi
formal metrics
semantic-content metrics
gold scoring
echo/duplicate/overclaim
Round 1 / Round 2 gate status
```

Canlı inference yapmaz.

---

# 8. Eligible attempt contract

Yalnız:

```text
experiment == semread-001d
schema_version == semread-candidates/3
reader_version == semread-candidate-reader/3
contract_version == semread-001d-run-contract/1
producer_identity == current producer identity
```

eligible.

Historical fallback YOK.

Current attempt yoksa:

```text
status = missing
```

---

# 9. Salt-okur invariant

Dev-report çalıştırmak:

```text
ledger yaratmamalı
budget mutate etmemeli
attempt dizini yaratmamalı
```

`out/lab/semread-001d` yoksa bile:

```text
all current cells = missing
```

raporlayabilmeli.

---

# 10. Formal metrics

Her cell:

```text
page_id
arm
attempt_id
attempt_state
send_attempted
done_reason
candidate_count
parse_valid
coordinate_valid
reference_valid
leak_clean
shared_settings
producer_identity_match
maxItems_hit
```

---

# 11. Semantic metrics

Tek kaynak reuse:

```text
semantic_claim_flags
candidate_has_semantic_claim
evidence_flags
```

Ölç:

```text
semantic_candidate_count
semantic_claim_count
semantic_candidate_rate
semantic field fill
evidence_only_count
```

Kopya semantic tanımı yok.

---

# 12. Semantic-valid output

First-class metric:

```text
semantic_valid_output =
    formal_valid
    AND semantic_claim_count >= 1
```

001D'nin ana dev reliability metriği budur.

---

# 13. Empty response ayrımı

```json
{"items":[]}
```

wire açısından valid abstention olabilir.

Ama claim olduğu bilinen dev sayfada:

```text
formal_valid = true
semantic_valid_output = false
```

olur.

---

# 14. Gold-scored metrics

Dev gold'a karşı:

```text
scorable_target_count
matched_claim_count
localization
form accuracy
size accuracy
count accuracy
termination accuracy
depth accuracy
physical accuracy
target binding
abstention
overclaim
false positive
unscorable extra
```

---

# 15. Measurement gate

001B'de bulunan bug tekrar edilmemeli.

Yanlış:

```text
comparison row exists → measured
```

Doğru:

```text
actual scorable measurement exists
```

Minimum objektif ölçüt:

```text
scorable_target_count > 0
```

---

# 16. Report completion

`complete=true` olamaz eğer:

```text
eligible attempt yok
semantic-valid output yok
actual measurement yok
```

Marker veya boş karşılaştırma satırı completion değildir.

---

# 17. VE echo v2

İki sınıf:

```text
empty_echo
contentful_observation_supported
```

`empty_echo`:

```text
observation region copied
semantic claim absent
```

`contentful_observation_supported`:

```text
observation evidence used
semantic claim exists
```

İkincisi otomatik hata değildir; gold correctness belirler.

---

# 18. Duplicate metrics

Ayrı ölç:

```text
exact duplicate
near-region duplicate
same semantic signature + same target
same callout repeated
duplicate_rate
```

Parser silent dedupe yapmaz.

---

# 19. maxItems signal

```text
candidate_count == 32
```

ise:

```text
max_items_hit = true
```

Tek başına failure değil; sürekli 32 degeneracy warning.

---

# 20. Overclaim metrics

Özel sınıflar:

```text
invented R/Ø
invented size
invented printed count
invented THRU
invented depth
unsupported physical meaning
```

Semantic alan doluluğu tek başına başarı değildir.

---

# 21. Dev-report test matrisi

En az:

```text
no current attempt → missing
001C attempt → ignored
wrong producer → ignored
wrong contract → ignored
formal pass + semantic 0 → semantic_valid false
formal pass + semantic >0 → semantic_valid true
zero-row comparison → measured false
scorable target → measured true
empty echo
contentful observation-supported
exact duplicate
near duplicate
maxItems flag
overclaim categorization
no ledger mutation
```

---

# 22. P1 acceptance

- [ ] 0 inference
- [ ] dev-report tool exists
- [ ] only current 001D identity eligible
- [ ] historical fallback yok
- [ ] `missing` first-class
- [ ] salt-okur
- [ ] no ledger mutation
- [ ] formal metrics
- [ ] semantic metrics
- [ ] real measurement gate
- [ ] semantic_valid_output
- [ ] echo v2
- [ ] duplicate metrics
- [ ] overclaim metrics
- [ ] maxItems flag
- [ ] focused tests green
- [ ] closure 45/45
- [ ] report/handoff aligned

---

# 23. İkinci adım — dev input kurulumu

Dev-report kapanmadan bu işe geçme.

Sonraki commit:

```text
001D dev input/corpus materialization
```

Still:

```text
0 inference
```

---

# 24. Dev corpus

Development için aynı dört source:

```text
dev-plate-pocket
dev-flange-book
dev-flange-elbow
dev-drawing-2
```

Bunlar final holdout değildir.

---

# 25. Input source-of-truth

Source-of-truth:

```text
repo source file
page/view selector
current preprocessing contract
```

Historical `out/lab/semread-001c/**` source-of-truth olmamalı.

---

# 26. Deterministic materialization

Her page için prepared raw page üret.

Kaydet:

```text
source path
source_sha256
page/view
prepared_sha256
width
height
preprocessing_identity
```

---

# 27. V/VE raw page invariant

Aynı page:

```text
raw page bytes V == raw page bytes VE
```

zorunlu.

VE yalnız ek evidence alır.

---

# 28. VE evidence hashes

Ayrı kaydet:

```text
overlay_sha256
observation_table_sha256
```

Raw-page identity ile karıştırma.

---

# 29. Leakage yasağı

Input prep:

```text
gold
expected answer
reference STEP
```

okumamalı.

Yalnız:

```text
source page
deterministic observations
```

---

# 30. P2 acceptance

- [ ] 0 inference
- [ ] 4 dev pages prepared
- [ ] source hashes
- [ ] prepared hashes
- [ ] V/VE raw bytes identical
- [ ] VE evidence separately hashed
- [ ] no gold dependency
- [ ] preprocessing identity current
- [ ] deterministic rebuild
- [ ] budget still 0/12

---

# 31. Dry-run gate

Input prep sonrası:

```text
--dry-run --phase dev
```

Round 1 için:

```text
planned_real_calls = 4
```

vermek zorunda.

Şu anki:

```text
planned_real_calls = 0
```

durumu artık kabul edilmez.

---

# 32. Üçüncü adım — static preflight

Dev-report + inputs hazır olduktan sonra:

```text
static preflight
```

0 inference ile kapanır.

---

# 33. Identity checks

Her Round-1 cell:

```text
experiment = semread-001d
schema = semread-candidates/3
reader = semread-candidate-reader/3
contract = semread-001d-run-contract/1
producer_identity = current
preprocessing_identity = current
```

---

# 34. Budget checks

Round 1 öncesi exactly:

```text
dev used = 0
dev cap = 12
final used = 0
final cap = 20
```

---

# 35. Runtime checks

Kontrol:

```text
model exact
digest exact
runtime exact
```

Mismatch = block.

---

# 36. Shared settings

Assert:

```text
generation_settings(V) == generation_settings(VE)
```

---

# 37. Prompt/context measurement

Dört Round-1 job için model çağırmadan ölç:

```text
prompt bytes
prompt tokens
image bytes
observation row count
num_ctx
num_predict
headroom
```

---

# 38. Context gate

Şart:

```text
prompt_tokens + NUM_PREDICT <= NUM_CTX
```

Safety headroom ayrıca raporlanmalı.

Fail olursa live call yok.

---

# 39. Context değişikliği politikası

Headroom yetersizse önce:

```text
cell
prompt token count
current ctx
required ctx
deficit
```

kanıtla.

Kör `num_ctx` artışı yok.

---

# 40. Structured-output compatibility

`anyOf` hâlâ bilinçli olarak yok.

Current schema'nın backend structured-output yolu ile kabul edildiği static/synthetic yolla kanıtlanmalı.

Semantic inference call harcanmamalı.

---

# 41. P3 acceptance

- [ ] 0 inference
- [ ] planned_real_calls = 4
- [ ] inputs exist
- [ ] identities current
- [ ] hashes current
- [ ] budget 0/12
- [ ] model/digest/runtime exact
- [ ] V==VE settings
- [ ] raw V/VE byte identity
- [ ] context headroom
- [ ] backend schema compatible
- [ ] closure 45/45

---

# 42. Pre-live test gate

Static preflight sonrası:

```text
001D focused tests
dev-report tests
identity tests
candidate/reader tests
lifecycle tests
gates
001C closure
D regression
```

geçmeli.

---

# 43. Gates

Dev-report/input/preflight code değişeceği için tekrar:

```text
34/34
```

şart.

---

# 44. Acceptance regression

Eğer ortak measurement helper değişirse:

```text
001B acceptance regression
```

yeniden koşulmalı.

Özellikle zero-row measurement bug'ı geri gelmemeli.

---

# 45. Full pytest zamanlaması

Round 1 öncesi full suite şart değil.

Şu yeterli:

```text
focused
gates
closure
D regression
relevant acceptance
```

Primary 8 tamamlanınca full pytest zorunlu.

---

# 46. Round 1 — ilk canlı inference

Yalnız yukarıdaki kapılar kapanınca tam dört call:

```text
dev-plate-pocket V
dev-plate-pocket VE
dev-flange-book V
dev-flange-book VE
```

---

# 47. Dispatch

Round 1:

```text
sequential
```

koş.

001C'deki queue/kill belirsizliğini tekrar etme.

---

# 48. Session hygiene

İlk call öncesi:

```text
active Ollama request yok
queue boş
correct model
digest exact
runtime exact
```

---

# 49. Reservation order

Her request:

```text
reserve budget
persist attempt manifest
persist input identity
persist producer identity
then send
```

Gönderilmiş failure budget sayar.

---

# 50. Round 1 formal gate

4/4:

```text
send_attempted = true
valid result
done_reason = stop
coordinate valid
refs valid
leak clean
correct identity
shared settings
```

---

# 51. Round 1 semantic gate

Her cell:

```text
semantic_claim_count >= 1
```

Aggregate:

```text
V >= 1 gold-matched semantic claim
VE >= 1 gold-matched semantic claim
V field accuracy > 0
VE field accuracy > 0
```

---

# 52. Primary Round-1 metric

```text
semantic_valid_output_rate = 4/4
```

Tanım:

```text
formal valid
AND semantic content
```

---

# 53. Gold-match guard

Semantic-looking ama yanlış output başarı değildir.

Her arm için en az bir actual gold-matched semantic claim gerekir.

---

# 54. Overclaim guard

Özellikle:

```text
R/Ø
size
count
THRU
depth
physical
```

fabrication izlenir.

No-guess geri çekilmez.

---

# 55. Round 1 fail olursa

Yeni çağrı yok.

Önce:

```text
offline forensic diagnosis
```

---

# 56. Reserve budget

Dev:

```text
12 total
8 primary
4 one-revision requalification reserve
```

Reserve keyfi retry değildir.

---

# 57. Tek revision hakkı

Round 1 fail ise:

```text
ONE contract revision
```

izinli.

Yasak:

```text
sampling sweep
model change
page-specific tweak
single-cell patch
```

---

# 58. Requalification

Revision sonrası aynı dört Round-1 cell tamamı yeniden koşulur.

Tek kötü hücre redo yok.

---

# 59. İkinci Round-1 de fail

001D kapanır:

```text
Round 2 yok
holdout yok
final yok
budget artışı yok
```

Sonraki deney `SEMREAD-001E`.

---

# 60. Round 2

Round 1 pass sonrası contract freeze.

Sonra:

```text
dev-flange-elbow V
dev-flange-elbow VE
dev-drawing-2 V
dev-drawing-2 VE
```

4 call.

---

# 61. Round 2 tuning yok

Round 2 sırasında prompt/schema/parser/generation settings değişmez.

---

# 62. Primary 8 gate

Holdout'a geçmek için:

```text
formal valid 8/8
semantic-valid 8/8
stop 8/8
coordinate 8/8
refs 8/8
leak clean 8/8
shared settings 8/8
V field accuracy > 0
VE field accuracy > 0
```

---

# 63. Degeneracy blockers

Holdout yok eğer:

```text
duplicate flood
all maxItems
VE table-copy dominates
semantic claims mostly fabricated
one arm semantic accuracy = 0
```

---

# 64. Primary 8 sonrası full pytest

```bash
.venv/bin/python -m pytest -q
```

Şart:

```text
0 fail
```

Kaydet:

```text
HEAD
collected
passed
failed
skipped
runtime
```

---

# 65. Repo hygiene

Her milestone sonrası:

```text
report.md
HERMES_SEMREAD_001D_HANDOFF.md
active PLAN
budget
contract identity
```

aynı facts'i taşımalı.

---

# 66. Holdout zamanı

Yalnız:

```text
Primary 8 pass
+
full pytest 0 fail
```

sonrası.

---

# 67. Holdout

Repo examples unseen değildir.

Tercihen kullanıcıdan:

```text
12–20 yeni technical drawing
```

al.

Bunlardan 10 final page model görmeden seç.

---

# 68. Freeze

Freeze bağlamalı:

```text
git HEAD
schema /3
reader /3
contract 001d/1
producer identity
evaluation identity
preprocessing identity
prompt identity
model/digest/runtime
shared settings
gold identity
D baseline
final budget 0/20
```

---

# 69. Final

```text
10 page × V/VE = 20 calls
retry = 0
```

Post-freeze tuning yok.

---

# 70. Şu anda YAPMA

```text
live call before dev-report
live call before dev inputs
live call while planned_real_calls=0
sampling sweep
model change
blind num_ctx increase
single-cell retry
budget increase
001C fallback
silent repair
holdout inference
CAD/planner detour
```

---

# 71. Commit planı

Current HEAD sonrası:

```text
1. semread-001d: dev-report formal + semantic + measurement gates
2. semread-001d: dev input materialization + raw-page identity
3. semread-001d: static preflight + context + dry-run=4
4. semread-001d: pre-live focused/gates/closure evidence
5. semread-001d: Round 1 four calls
6. semread-001d: Round 1 semantic report
7. optional ONE contract revision + four-cell requalification
8. semread-001d: Round 2 four calls
9. semread-001d: primary-8 report + full pytest
10. holdout intake/selection
11. gold
12. D baseline + clean clone
13. freeze
14. final 20
15. immutable final report
```

---

# 72. ŞİMDİKİ TEK SOMUT İŞ

**0 inference.**

Şimdi yalnız:

```text
eval/semread_001d_dev_report.py
```

ve testleri.

Attempt yokken beklenen dürüst çıktı:

```text
all current dev cells = missing
measurement = false
semantic_valid = false
```

---

# 73. İlk commit acceptance

- [ ] 0 inference
- [ ] dev-report exists
- [ ] current 001D identity only
- [ ] historical fallback yok
- [ ] missing first-class
- [ ] salt-okur
- [ ] no ledger mutation
- [ ] formal metrics
- [ ] semantic metrics
- [ ] semantic helper reuse
- [ ] real measurement gate
- [ ] semantic_valid_output
- [ ] echo v2
- [ ] duplicate metrics
- [ ] overclaim metrics
- [ ] maxItems flag
- [ ] focused tests green
- [ ] closure 45/45
- [ ] report/handoff aligned

---

# 74. İlk live call absolute blockers

Aşağıdakilerden biri varsa inference YOK:

```text
dev-report missing
dev inputs missing
planned_real_calls != 4
budget != 0/12
schema != /3
reader != /3
contract != 001d/1
producer mismatch
model mismatch
digest mismatch
runtime mismatch
V/VE settings mismatch
raw page bytes mismatch
context headroom fail
gates fail
closure != 45/45
```

---

# 75. Son yön

Producer contract hazır.

Bir sonraki bilimsel risk:

```text
sonuçları gördükten sonra evaluator/gate tanımlamak
```

Bu yüzden dev-report şimdi dondurulmalı.

Bir sonraki operasyonel risk:

```text
input corpus kurulmadan inference'a geçmek
```

Bu yüzden dev-report sonrası dev input materialization.

Doğru kısa rota:

```text
dev-report
→ dev inputs
→ static preflight
→ Round 1 four calls
→ semantic proof
```
