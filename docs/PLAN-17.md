# PLAN.md — drawingto3d / SEMREAD-001D
## `001d/1` producer identity sonrası: dev-report → dev input kurulumu → static preflight → Round 1 semantic proof

**Tarih:** 2026-10-05  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Gözlenen `main` HEAD:** `b2e12182a05c2e8f8176008de63d7a1cd87bd226`  
**Aktif deney:** `SEMREAD-001D`  
**Aktif tracked plan:** `docs/PLAN-15.md`  
**Önerilen yeni history entry:** `docs/PLAN-16.md`  
**001D bütçe:** dev `0/12`, final `0/20`, toplam `0/32`  
**001C:** CLOSED / READ-ONLY HISTORICAL  
**001C closure:** `--verify 45/45`  
**External CI/status:** yok  
**İlk canlı 001D inference:** henüz yapılmadı  

---

# 0. Yönetici özeti

Son repo kontrolünde önceki açık kapı kapanmış durumda:

```text
semread-candidates/3
semread-candidate-reader/3
semread-001d-run-contract/1
```

artık üçü de current.

Ayrıca:

```text
attempt manifest identity alanları
producer_identity
preprocessing_identity
dry-run identity manifest
blocked_contract_identity
```

uygulanmış.

Üretim zarfı değiştirilmemiş:

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

V ve VE generation settings aynı.

Güncel gerçek açık kapı artık:

```text
1. 001D dev-report / gate katmanı
2. 001D dev input/corpus PNG kurulumu
3. static preflight
4. Round 1 — tam 4 canlı çağrı
```

Önemli ayrım:

- Kimlik dry-run’ı dört Round-1 hücresinin manifestini doğru kurabiliyor.
- Fakat gerçek CLI dry-run `planned_real_calls = 0` veriyor.
- Bunun nedeni **001D corpus PNG/input’larının henüz kurulmamış olması**.

Dolayısıyla canlı inference’a geçmek için önce evaluator/gate tanımı, sonra input bytes, sonra preflight tamamlanmalı.

---

# 1. Repo kontrolü — current facts

Güncel HEAD:

```text
b2e12182a05c2e8f8176008de63d7a1cd87bd226
```

Son commitin yaptığı temel işler:

```text
CONTRACT_VERSION = semread-001d-run-contract/1
attempt manifest explicit experiment/schema/reader/contract identities
producer identity separation
preprocessing identity persistence
4-cell Round-1 identity dry-run
wrong identity dispatch block
PLAN-15 tracking
```

Inference:

```text
0
```

Budget:

```text
dev   0/12
final 0/20
```

---

# 2. report.md ile handoff uyumu

`report.md` current bölüm ve `docs/HERMES_SEMREAD_001D_HANDOFF.md` aynı state’i taşıyor:

```text
active experiment = SEMREAD-001D
schema /3
reader /3
contract 001d/1
dev budget 0/12
final budget 0/20
001C closure 45/45
next = dev-report → static preflight → Round 1
```

Bu uyum korunmalı.

---

# 3. Repo hijyeni invariantı

001C:

```text
READ-ONLY HISTORICAL
```

olarak kalır.

Dokunulmaz:

```text
docs/HERMES_SEMREAD_001C_HANDOFF.md
out/lab/semread-001c/**
eval/semread_001c_closure.json
historical attempts
```

Milestone’larda:

```text
eval/semread_001c_closure.py --verify
```

sonucu:

```text
45/45
```

olmalı.

---

# 4. Plan history politikası

Current tracked plan:

```text
docs/PLAN-15.md
```

Bu yeni plan repo authority yapılacaksa:

```text
docs/PLAN-16.md
```

olarak yeni history entry oluştur.

PLAN-15’i overwrite etme.

Eski planların SHA/pin zinciri korunmalı.

---

# 5. Current producer identity doğru

001D current producer identity:

```text
001C producer identity’lerinden farklı
```

olarak test edilmiş.

Bu doğru.

001B/001C attempt’leri current 001D attempt gibi seçilemez.

---

# 6. Wrong-contract dispatch guard

Canlı gönderim öncesi:

```text
contract_identity_block()
```

aktif.

Beklenen current identity ile mismatch varsa:

```text
blocked_contract_identity
send_attempted = false
budget harcanmaz
read_page çağrılmaz
```

Bu mekanizma freeze’e kadar korunmalı.

---

# 7. Üretim zarfı bu aşamada değişmez

Şu anda test edilen hipotez:

```text
semantic-content-aware full-page contract
```

Bu nedenle aşağıdakileri aynı commit serisinde değiştirme:

```text
model
digest
runtime
num_ctx
num_predict
temperature
repeat_penalty
repeat_last_n
image resize
```

Aksi halde 001D’nin etkisi karışır.

---

# 8. V/VE causal invariant

Şart:

```text
generation_settings(V) == generation_settings(VE)
```

İzinli tek arm farkı:

```text
VE evidence
```

yani:

```text
overlay
observation table
evidence prompt section
extra evidence image
```

Sampling farkı yok.

---

# 9. Son test kanıtları

Current identity commit kayıtları:

```text
focused suite        101 passed
quick SEMREAD         119 passed
gates                 34/34
001C closure          45/45
check_tables          21 / 0 mismatch
```

External GitHub commit status:

```text
yok
```

Dolayısıyla authority:

```text
local pytest
eval tools
attempt artifacts
closure verifier
```

---

# 10. Acceptance bug dersini 001D’ye taşı

001B acceptance bonus koşusunda şu hata bulundu:

```text
comparison.vs_d satırı var
ama gerçek scorable measurement yok
→ measured=True
→ gate yanlış kapanabiliyor
```

Düzeltme:

```text
arms_with_measurement()
```

ve gerçek ölçüt:

```text
scorable_target_count > 0
```

001D dev-report aynı hatayı yeniden üretmemeli.

---

# 11. ŞİMDİKİ ASIL BLOCKER #1 — dev-report yok

Repo aramasında:

```text
eval/semread_001d_dev_report.py
```

henüz yok.

Bu sıradaki tek somut iştir.

---

# 12. Neden dev-report inference öncesi yazılmalı?

Round 1 sonuçları görüldükten sonra şunları değiştirmek bilimsel olarak problemli olur:

```text
hangi attempt eligible?
formal pass ne?
semantic-valid ne?
measurement var mı?
echo ne?
duplicate ne?
overclaim ne?
Round 1 gate ne?
```

Bu tanımlar sonuç görülmeden dondurulmalı.

---

# 13. P1 — 001D dev-report aracı

Yeni salt-okur araç:

```text
eval/semread_001d_dev_report.py
```

Görev:

```text
eligible current 001D attempts seç
formal metrics hesapla
semantic-content hesapla
gold scoring yap
echo/duplicate/overclaim ölç
Round 1 / Round 2 gate status üret
```

Canlı inference yapmaz.

---

# 14. Eligible attempt contract

Yalnız şu kimlikler current sayılır:

```text
experiment == semread-001d
schema_version == semread-candidates/3
reader_version == semread-candidate-reader/3
contract_version == semread-001d-run-contract/1
producer_identity == current producer identity
```

---

# 15. Historical fallback YOK

Yasak:

```text
001C pass reuse
001B pass reuse
old producer fallback
best available historical attempt
```

Current attempt yoksa:

```text
missing
```

raporlanmalı.

---

# 16. Dev-report ledger yaratmamalı

Şu anda:

```text
out/lab/semread-001d
```

ledger ilk gerçek dev çağrısında kurulacak şekilde tasarlanmış.

Dev-report salt-okur çalıştırıldığında:

```text
root yoksa all cells missing
```

diyebilmeli.

Rapor çalıştırmak:

```text
budget state yaratmamalı
attempt dizini yaratmamalı
ledger mutate etmemeli
```

---

# 17. Formal metrics

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

# 18. Semantic-content metrics

Tek kaynak helper’ları reuse et:

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
field fill distribution
evidence_only_count
```

Kopya semantic-content tanımı oluşturma.

---

# 19. `semantic_valid_output`

First-class metric:

```text
semantic_valid_output =
    formal_valid
    AND semantic_claim_count >= 1
```

001D’nin ana dev reliability metriği bu.

---

# 20. Empty response ayrımı

```json
{"items":[]}
```

parser açısından valid abstention olabilir.

Ama claim olduğu bilinen dev sayfada:

```text
formal_valid = true
semantic_valid_output = false
```

Bu ayrım açık tutulmalı.

---

# 21. Gold scoring metrics

Dev gold’a karşı:

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

# 22. Gerçek measurement gate

Şu yanlış:

```text
comparison row exists → measured
```

Doğru:

```text
at least one actual scorable target
```

Yani örneğin:

```text
scorable_target_count > 0
```

---

# 23. Report completion

`complete=True` olamaz eğer:

```text
eligible attempt yok
measurement yok
semantic-valid output yok
```

Marker text bulunması completion değildir.

---

# 24. VE echo v2

İki sınıf:

```text
empty_echo
contentful_observation_supported
```

### empty_echo

```text
observation region copied
semantic claim absent
```

Normal valid 001D output içinde olmamalı.

### contentful_observation_supported

```text
observation evidence used
semantic claim exists
```

Bu otomatik hata değildir.

Gold doğruluğu belirler.

---

# 25. Duplicate metrics

Ayrı ölç:

```text
exact duplicate
near-region duplicate
same semantic signature + same target
same callout text repeated
```

Parser silent dedupe yapmaz.

---

# 26. maxItems metric

```text
candidate_count == 32
```

ise:

```text
max_items_hit = true
```

Tek başına failure değil.

Fakat sürekli 32:

```text
degeneracy signal
```

---

# 27. Overclaim metrics

Semantic-content zorlaması hallucination’a yol açabilir.

Özel say:

```text
invented R/Ø
invented size
invented printed count
invented THRU
invented depth
unsupported physical meaning
```

Semantic field dolması tek başına başarı değildir.

---

# 28. Dev-report output

Round 1 sonrası üretilecek gerçek artifact:

```text
out/lab/semread-001d/dev-report.json
out/lab/semread-001d/dev-report.md
```

Ama attempt yokken aracı test etmek için:

```text
in-memory/temp fixture
```

kullan.

Production ledger yaratma.

---

# 29. P1 test matrisi

Zorunlu testler:

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
```

---

# 30. P1 acceptance

- [ ] 0 inference
- [ ] dev-report tool exists
- [ ] only current 001D attempts
- [ ] no historical fallback
- [ ] missing is first-class
- [ ] no ledger mutation
- [ ] formal metrics
- [ ] semantic metrics
- [ ] measurement gate
- [ ] semantic_valid_output
- [ ] echo v2
- [ ] duplicate metrics
- [ ] overclaim metrics
- [ ] tests green
- [ ] closure 45/45
- [ ] report/handoff aligned

---

# 31. ŞİMDİKİ ASIL BLOCKER #2 — 001D dev input yok

Current report/handoff açıkça:

```text
--dry-run --phase dev
planned_real_calls = 0
```

diyor.

Sebep:

```text
001D corpus PNGs not installed
```

Bu canlı inference öncesi gerçek operasyonel blocker.

---

# 32. Dev corpus

001D development için aynı dört development source kullanılabilir:

```text
dev-plate-pocket
dev-flange-book
dev-flange-elbow
dev-drawing-2
```

Bunlar final holdout değildir.

---

# 33. Dev input source-of-truth

Source-of-truth:

```text
repo source file
page/view selector
current preprocessing contract
```

olmalı.

Historical:

```text
out/lab/semread-001c/**
```

input source-of-truth olmamalı.

---

# 34. 001C prepared PNG’yi kör kopyalama

001C artifact’i historical evidence olabilir.

001D input pipeline:

```text
source
→ current deterministic preparation
→ prepared raw page
```

şeklinde kurulmalı.

Byte-identical çıkıyorsa hash ile kanıtla.

---

# 35. P2 — deterministic input materialization

4 dev page için:

```text
prepared raw page PNG
```

kur.

Kaydet:

```text
source path
source sha256
page index/view
prepared sha256
width
height
preprocessing_identity
```

---

# 36. V/VE raw page invariant

Aynı page’de:

```text
raw page bytes V == raw page bytes VE
```

zorunlu.

VE yalnız ekstra evidence alır.

---

# 37. VE artifacts

Ayrı hash’le:

```text
overlay image
observation table serialization
```

Raw page hashinden ayrı tutulmalı.

---

# 38. Input preparation inference değildir

Bunlar bütçe harcamaz:

```text
PDF render
PNG preparation
resize
overlay generation
observation serialization
hashing
prompt serialization
token measurement
```

---

# 39. Leakage yasağı

Input materialization:

```text
gold
expected answer
reference STEP
```

okumamalı.

Yalnız source + deterministic observations.

---

# 40. P2 acceptance

- [ ] 0 inference
- [ ] 4 dev pages prepared
- [ ] source hashes recorded
- [ ] prepared hashes recorded
- [ ] V/VE raw page identical
- [ ] VE evidence separately hashed
- [ ] no gold dependency
- [ ] preprocessing identity current
- [ ] rebuild deterministic
- [ ] budget still 0/12

---

# 41. Dry-run 0 artık kabul edilmez

Input prep sonrası:

```text
--dry-run --phase dev
```

Round 1 için:

```text
planned_real_calls = 4
```

vermek zorunda.

0 ise inference yok.

---

# 42. P3 — static preflight

Dev-report + inputs tamamlandıktan sonra:

```text
static preflight
```

kapanır.

0 inference.

---

# 43. Identity preflight

Her Round-1 job:

```text
experiment = semread-001d
schema = semread-candidates/3
reader = semread-candidate-reader/3
contract = semread-001d-run-contract/1
producer identity = current
preprocessing identity = current
```

---

# 44. Budget preflight

Round 1 öncesi:

```text
dev used = 0
dev cap  = 12
final used = 0
final cap  = 20
```

---

# 45. Runtime preflight

Kontrol:

```text
model tag exact
digest exact
runtime exact
```

Mismatch = block.

---

# 46. Shared settings preflight

Assert:

```text
generation_settings(V) == generation_settings(VE)
```

---

# 47. Prompt/context measurement

Dört Round-1 cell için model çağırmadan ölç:

```text
prompt bytes
prompt tokens
image bytes
observation rows
NUM_CTX
NUM_PREDICT
headroom
```

---

# 48. Context gate

Şart:

```text
prompt_tokens + NUM_PREDICT <= NUM_CTX
```

Tercihen safety margin ayrıca raporlanır.

---

# 49. Context fail olursa

Live call yok.

Önce:

```text
which cell
prompt tokens
required ctx
current ctx
deficit
```

kanıtla.

Kör `num_ctx` artışı yok.

---

# 50. Structured-output compatibility

`anyOf` bilinçli olarak eklenmedi.

Current schema’nın backend format yolu ile kabul edilebildiği sentetik/static testle kanıtlanmalı.

Semantic inference call harcanmamalı.

---

# 51. Dry-run manifest acceptance

Dört Round-1 job:

```text
page
arm
phase
experiment
schema
reader
contract
producer
preprocessing
input hash
generation signature
```

taşımalı.

---

# 52. P3 acceptance

- [ ] 0 inference
- [ ] planned_real_calls = 4
- [ ] inputs exist
- [ ] identities current
- [ ] hashes current
- [ ] budget 0/12
- [ ] runtime exact
- [ ] model/digest exact
- [ ] V==VE generation settings
- [ ] raw V/VE byte identity
- [ ] context headroom
- [ ] backend schema compatibility
- [ ] closure 45/45

---

# 53. P4 — pre-live test gate

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

# 54. Gates yeniden koşulmalı

Current identity commit:

```text
34/34
```

geçmiş.

Ama dev-report/input/preflight code değişeceği için live call öncesi tekrar:

```text
34/34
```

şart.

---

# 55. Acceptance tests ne zaman?

Eğer dev-report çalışması ortak evaluator/measurement helper’ını değiştirirse:

```text
relevant acceptance suite
```

yeniden koş.

Özellikle ölçüm gate’ine dokunulursa 001B acceptance regression önemli.

---

# 56. Full pytest Round 1 öncesi şart değil

Full suite maliyeti yüksek.

Pre-live için:

```text
focused
gates
closure
D regression
relevant acceptance
```

yeterli.

Full pytest primary 8 sonrası.

---

# 57. Round 1 — tam 4 canlı çağrı

Yalnız P1–P4 tamamen kapanınca:

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

# 58. Sequential dispatch

Round 1:

```text
sequential
```

koşmalı.

001C’de yaşanan queue/kill belirsizliğini tekrar etme.

---

# 59. Session hygiene

İlk call öncesi:

```text
active Ollama request yok
queue boş
correct model
digest exact
runtime exact
```

---

# 60. Budget reservation sırası

Her request:

```text
reserve budget
persist attempt manifest
persist input identity
persist producer identity
then send
```

Failure gönderildiyse call sayılır.

---

# 61. Round 1 formal gate

4/4:

```text
send_attempted = true
valid result
done_reason = stop
coordinate valid
references valid
leak clean
correct current identities
shared generation settings
```

---

# 62. Round 1 semantic gate

Her cell:

```text
semantic_claim_count >= 1
```

Aggregate:

```text
V >= 1 gold-matched semantic claim
VE >= 1 gold-matched semantic claim
V semantic field accuracy > 0
VE semantic field accuracy > 0
```

---

# 63. Round 1 primary metric

```text
semantic_valid_output_rate
```

hedef:

```text
4/4
```

Tanım:

```text
formal valid
AND semantic content
```

---

# 64. Neden 4/4?

001C’nin asıl failure’ı:

```text
semantic content 0/8
```

idi.

001D’nin tek hipotezi semantic-content contract.

Dolayısıyla bir Round-1 hücresi hâlâ semantic-empty ise contract hypothesis tam geçmemiş sayılır.

---

# 65. Gold-match aggregate zorunlu

Semantic-looking ama yanlış output olabilir.

Bu yüzden yalnız:

```text
semantic_claim_count > 0
```

yeterli değil.

Her arm’da en az bir gerçek gold match gerekir.

---

# 66. Overclaim guard

Özellikle:

```text
R/Ø
size
count
THRU
depth
physical
```

fabrication say.

No-guess ilkesi korunur.

---

# 67. Round 1 fail olursa

Yeni çağrı yapmadan:

```text
offline forensic diagnosis
```

yap.

---

# 68. Reserve budget

Dev:

```text
12
```

Dağılım:

```text
8 primary
4 one-revision requalification reserve
```

Reserve keyfi retry değil.

---

# 69. Tek revision hakkı

Round 1 geçmezse:

```text
ONE contract revision
```

izinli.

Revision önceden açıklanmalı.

Yasak:

```text
sampling sweep
model change
page-specific tweak
single bad cell patch
```

---

# 70. Requalification

Revision sonrası:

```text
same 4 Round-1 cells
```

tamamı yeni contract ile yeniden koşulur.

Tek-cell redo yok.

---

# 71. Round 1 ikinci kez fail

001D kapanır:

```text
Round 2 yok
holdout yok
final yok
budget increase yok
```

Yeni deney:

```text
SEMREAD-001E
```

---

# 72. Round 2

Round 1 pass sonrası contract kilitlenir.

Sonra:

```text
dev-flange-elbow V
dev-flange-elbow VE
dev-drawing-2 V
dev-drawing-2 VE
```

4 call.

---

# 73. Round 2 tuning yok

Round 2 sırasında:

```text
prompt
schema
parser
sampling
context
```

değişmez.

Failure result olarak kalır.

---

# 74. Primary 8 gate

Holdout’a geçmek için:

```text
formal valid 8/8
semantic-valid 8/8
stop 8/8
coordinate 8/8
refs 8/8
leak 8/8
shared settings 8/8
```

Semantic:

```text
V accuracy > 0
VE accuracy > 0
```

---

# 75. Degeneracy blockers

Holdout yok eğer:

```text
duplicate flood
all outputs maxItems
VE table-copy dominates
semantic claims mostly fabricated
one arm accuracy = 0
```

---

# 76. Primary 8 sonrası full pytest

Çalıştır:

```bash
.venv/bin/python -m pytest -q
```

Şart:

```text
0 fail
```

---

# 77. Full-suite kanıtı

Kaydet:

```text
HEAD
collected
passed
failed
skipped
runtime
```

Collection count değişirse açıklama.

---

# 78. External CI

Current HEAD için GitHub status yok.

Report açıkça:

```text
External CI: none
```

tutmalı.

---

# 79. Repo hygiene milestone

Her milestone sonrası:

```text
report.md
HERMES_SEMREAD_001D_HANDOFF.md
active PLAN
budget state
contract identity
```

aynı current facts’i göstermeli.

---

# 80. Report/handoff drift kontrolü

Şunlar birebir uyuşmalı:

```text
HEAD
active plan
schema
reader
contract
budget
latest test evidence
open gate
next single step
```

---

# 81. Holdout zamanı

Yalnız:

```text
Primary 8 pass
+
full pytest 0 fail
```

sonrası.

---

# 82. Holdout source

Repo examples artık unseen değil.

Kullanıcıdan tercihen:

```text
12–20 yeni technical drawing
```

al.

10 final page model görmeden seç.

---

# 83. Holdout eligibility

```text
repo history’de yok
001B/001C/001D dev’de yok
duplicate değil
SEMREAD-scope callout var
```

Hash + group identity.

---

# 84. Gold

V/VE output görülmeden hazırlanır.

Mevcut gold framework reuse edilir.

---

# 85. Freeze

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

# 86. Final 20

```text
10 page × V/VE = 20 calls
retry = 0
```

Post-freeze tuning yok.

---

# 87. Final metrics

Önce:

```text
formal_valid_output_rate
semantic_valid_output_rate
```

Sonra:

```text
localization
callout
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

# 88. Karar ağacı

## V + VE başarılı
Full-page 001D yaklaşımı final için anlamlı.

## yalnız V başarılı
VE evidence representation zararlı olabilir.

## yalnız VE başarılı
Deterministic observations kritik yardım sağlıyor.

## ikisi de başarısız
Full-page one-shot yaklaşım kapatılır.

001E farklı architecture:

```text
crop-first
detect→read
OCR-first
one-callout-per-query
typed subquestions
```

---

# 89. Şu anda YAPMA

```text
live call before dev-report
live call before inputs
live call while planned_real_calls=0
model change
sampling sweep
blind num_ctx increase
single-cell retry
budget increase
001C fallback
silent repair
holdout inference
CAD/planner detour
```

---

# 90. Commit planı

Current HEAD sonrası:

```text
1. semread-001d: dev-report formal + semantic + measurement gates
2. semread-001d: dev input materialization + raw-page identity
3. semread-001d: static preflight + context/dry-run=4
4. semread-001d: pre-live focused/gates/closure evidence
5. semread-001d: Round 1 four calls
6. semread-001d: Round 1 semantic report
7. optional ONE contract revision + four-cell requalification
8. semread-001d: Round 2 four calls
9. semread-001d: primary 8 report + full pytest
10. holdout intake/selection
11. gold
12. D baseline + clean clone
13. freeze
14. final 20
15. immutable final report
```

---

# 91. ŞİMDİKİ TEK SOMUT İŞ

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

# 92. İlk commit acceptance

- [ ] 0 inference
- [ ] dev-report exists
- [ ] only current 001D identity eligible
- [ ] historical fallback yok
- [ ] no attempt = missing
- [ ] formal metrics
- [ ] semantic metrics
- [ ] semantic helper reuse
- [ ] real measurement gate
- [ ] zero-row measured=false
- [ ] echo v2
- [ ] duplicate metrics
- [ ] overclaim metrics
- [ ] maxItems flag
- [ ] no ledger mutation
- [ ] tests green
- [ ] closure 45/45
- [ ] report/handoff aligned

---

# 93. Dev-report sonrası tek iş

Sonra:

```text
001D dev input/corpus PNG materialization
```

Bu tamamlanınca dry-run:

```text
planned_real_calls = 4
```

olmalı.

---

# 94. İlk live call absolute blockers

Bunlardan biri varsa inference YOK:

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
raw page mismatch
context headroom fail
gates fail
closure != 45/45
```

---

# 95. Son yön

Şu an producer contract hazır.

Bilimsel risk artık:

```text
sonuçları gördükten sonra evaluator/gate tanımlamak
```

Bu yüzden önce dev-report.

Operasyonel risk:

```text
input corpus kurulmadan inference’a geçmek
```

Bu yüzden ikinci adım input materialization.

Doğru kısa rota:

```text
dev-report
→ dev inputs
→ static preflight
→ Round 1 four calls
→ semantic proof
```
