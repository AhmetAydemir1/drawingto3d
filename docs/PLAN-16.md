# PLAN.md — drawingto3d / SEMREAD-001D
## `001d/1` producer identity sonrası: dev-report → 001D dev input kurulumu → static preflight → Round 1 semantic proof

**Tarih:** 2026-10-05  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Gözlenen `main` HEAD:** `b2e12182a05c2e8f8176008de63d7a1cd87bd226`  
**Aktif deney:** `SEMREAD-001D`  
**Aktif tracked plan:** `docs/PLAN-15.md`  
**001D bütçe:** dev `0/12`, final `0/20`, toplam `0/32`  
**001C:** CLOSED / READ-ONLY HISTORICAL  
**001C closure:** `--verify 45/45`  
**External CI/status:** yok  
**Güncel açık kapı:** 001D dev-report + dev input/static preflight  
**İlk canlı inference:** henüz yapılmadı

---

# 0. Yönetici özeti

Önceki plandaki en kritik blocker artık kapanmış durumda:

```text
semread-candidates/3
semread-candidate-reader/3
semread-001d-run-contract/1
```

üçü de current.

Ayrıca:

```text
attempt manifest identity alanları
producer_identity
preprocessing_identity
dry-run identity checks
blocked_contract_identity
```

uygulanmış.

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

Bu noktada asıl açık iş artık producer identity değil.

Yeni açık kapı:

```text
1. 001D dev-report
2. 001D dev input/corpus PNG kurulumu
3. static preflight
4. first 4 Round-1 calls
```

Önemli güncel bulgu:

```text
dry-run planned_real_calls = 0
```

çünkü 001D corpus PNG'leri henüz kurulmamış.

Dolayısıyla canlı çağrıdan önce yalnız evaluator değil, **input materialization / corpus identity** de kapanmalı.

---

# 1. Güncel repo durumu

## 1.1 Producer identity işi tamamlandı

Current:

```text
CONTRACT_VERSION = semread-001d-run-contract/1
CANDIDATE_SCHEMA_VERSION = semread-candidates/3
CANDIDATE_READER_VERSION = semread-candidate-reader/3
```

Bu üç kimlik artık 001D'yi açıkça ayırıyor.

---

# 2. Current run-contract doğru

`semantic_run_contract.py` artık current docstring'de:

```text
SEMREAD-001D
semantic-content-aware full-page V/VE
```

diye tanımlanıyor.

001C history current contract içinde primary state değil; closure artifact'ta tutuluyor.

Bu doğru.

---

# 3. Attempt manifest güçlendi

Attempt manifest artık açıkça:

```text
experiment
schema_version
reader_version
contract_version
producer_identity
preprocessing_identity
```

taşıyor.

Bu alanlar final reproducibility için zorunlu.

---

# 4. Yanlış kimlikle gönderim bloklanıyor

`contract_identity_block()` ile:

```text
experiment = semread-001d
ama contract/schema/reader yanlış
```

ise gönderim:

```text
blocked_contract_identity
```

ile duruyor.

Önemli:

```text
send_attempted = false
budget harcanmaz
read_page çağrılmaz
```

Bu mekanizma korunmalı.

---

# 5. Producer identity ayrıldı

001D producer identity:

```text
001C producer identity'lerinden farklı
```

olarak test edilmiş.

Bu beklenen ve doğru.

001C attemptleri 001D current attempt gibi seçilemez.

---

# 6. Dry-run manifest başarılı

4 Round-1 hücresinin kimliği doğru kurulabiliyor:

```text
experiment = semread-001d
phase = dev
schema = /3
reader = /3
contract = 001d/1
```

Eski `001c/1` kimliği current manifest'e girmiyor.

---

# 7. Üretim zarfı değişmedi

Bu çok önemli.

001D'nin test ettiği değişken:

```text
semantic-content-aware prompt/schema/parser contract
```

olmalı.

Şu anda aynı anda model/sampling/context değiştirilmemiş.

Causal yorum açısından doğru.

---

# 8. V/VE invariantı korunuyor

Zorunlu:

```text
generation_settings(V) == generation_settings(VE)
```

İzinli tek fark:

```text
VE evidence
```

yani:

```text
overlay
observation table
evidence prompt section
image count
```

Bu invariant final freeze'e kadar korunmalı.

---

# 9. Test kanıtı

Son kimlik commit'inde kayıtlı:

```text
focused 101 passed
quick SEMREAD 119 passed
gates 34/34
001C closure 45/45
check_tables 21/0
```

001D inference:

```text
0
```

---

# 10. Acceptance bug fix de kapanmış durumda

001B acceptance bonus koşusunda:

```text
comparison.vs_d satırı var
ama gerçek scorable measurement yok
```

durumunda gate'in yanlış kapanabildiği bulundu.

Tek kaynak:

```text
arms_with_measurement()
```

ile düzeltildi.

Acceptance suite:

```text
27 passed
```

Bu ders 001D dev-report'a da uygulanmalı.

---

# 11. Şimdiki asıl blocker #1 — dev-report yok

Repo kontrolünde:

```text
eval/semread_001d_dev_report.py
```

henüz yok.

Bu normal; sıradaki iş bu.

Ama dev-report yalnız eski 001C aracının kopyası olmamalı.

001D'nin semantic-content contract'ını first-class ölçmeli.

---

# 12. Dev-report neden inference öncesi yazılmalı?

Çünkü Round 1 bittiğinde:

```text
hangi attempt seçilecek?
formal pass ne?
semantic-valid ne?
measurement var mı?
echo var mı?
duplicate var mı?
```

gibi kararlar önceden tanımlanmış olmalı.

Inference sonrası evaluator mantığı icat etmek yasak.

---

# 13. P1 — `eval/semread_001d_dev_report.py`

Yeni salt-okur araç oluştur.

Görevi:

```text
001D current attemptleri seç
formal state hesapla
semantic-content hesapla
gold ile ölç
echo / duplicate / overclaim raporla
Round 1 / Round 2 gates üret
```

Canlı inference yapmaz.

---

# 14. Attempt selection contract

Yalnız şu attempt'ler eligible:

```text
experiment == semread-001d
schema_version == semread-candidates/3
reader_version == semread-candidate-reader/3
contract_version == semread-001d-run-contract/1
producer_identity == current producer identity
```

Eski 001C/001B attempt'e fallback:

```text
YOK
```

---

# 15. Attempt yoksa ne olacak?

Current dev cell'de attempt yoksa:

```text
status = missing
```

veya eşdeğer first-class state.

Şunlar yasak:

```text
001C pass reuse
historical fallback
best-looking old attempt
```

---

# 16. Formal metrics

Her cell:

```text
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

taşımalı.

---

# 17. Semantic metrics

Tek kaynak helper reuse:

```text
semantic_claim_flags
candidate_has_semantic_claim
evidence_flags
```

Ölç:

```text
semantic_claim_count
semantic_candidate_count
semantic_candidate_rate
semantic field fill
evidence_only_count
```

Kopya semantic-content tanımı oluşturma.

---

# 18. Gold-scored metrics

Dev gold'a karşı:

```text
matched_claim_count
scorable_target_count
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

# 19. Measurement gate — 001B dersi

Şu:

```text
comparison object exists
```

ölçüm kanıtı değildir.

Gerçek measurement:

```text
scorable_target_count > 0
```

gibi objektif kriterle tanımlanmalı.

Mümkünse 001B'deki:

```text
arms_with_measurement()
```

mantığı ortaklaştır veya aynı source-of-truth prensibini kullan.

---

# 20. Dev report completion

Report:

```text
complete=true
```

diyemez eğer:

```text
eligible attempt yok
scorable measurement yok
semantic-valid candidate yok
```

Marker text var diye completion yok.

---

# 21. Semantic-valid tanımı

001D primary metric:

```text
semantic_valid_output
```

Tanım:

```text
formal valid
AND
semantic_claim_count >= 1
```

Bu first-class field olmalı.

---

# 22. Empty response

```text
items=[]
```

parser açısından valid abstention kalır.

Ama claim olduğu bilinen 4 dev page için:

```text
semantic_valid_output = false
```

olur.

Bu ayrım korunmalı.

---

# 23. VE echo v2

İki sınıf:

```text
empty_echo
contentful_observation_supported
```

### empty_echo

Observation region kopyalanmış, semantic claim yok.

001D parser bunu normal valid candidate olarak kabul etmemeli.

### contentful_observation_supported

Observation evidence kullanılmış ve semantic claim var.

Bu otomatik failure değildir.

Gold correctness karar verir.

---

# 24. Duplicate metrics

Ölç:

```text
exact duplicate
near-region duplicate
same semantic signature + same target
same callout text repeated
```

Parser silent dedupe yapmaz.

Evaluator sayar.

---

# 25. maxItems signal

```text
candidate_count == 32
```

ise:

```text
max_items_hit = true
```

Bu tek başına fail değildir.

Ama:

```text
multiple cells continuously maxItems
```

degeneracy warning.

---

# 26. Overclaim metrics

Semantic-content zorlaması hallucination üretebilir.

Ayrı say:

```text
invented size
invented count
invented form
invented THRU
invented depth
unsupported physical meaning
```

Semantic fill artışı tek başına başarı değil.

---

# 27. Dev report outputları

Önerilen:

```text
out/lab/semread-001d/dev-report.json
out/lab/semread-001d/dev-report.md
```

Ancak inference başlamadan önce `out/lab/semread-001d` kurulumu lifecycle politikasına göre yapılmalı.

Eğer ledger yalnız ilk attempt'te kuruluyorsa dev-report:

```text
root yok → all cells missing
```

şeklinde salt-okur çalışabilmeli.

Rapor aracı sırf çalıştı diye ledger yaratmamalı.

---

# 28. P1 testleri

En az:

```text
no attempt → missing
001C attempt → ignored
wrong producer → ignored
wrong contract → ignored
formal pass + semantic 0 → semantic_valid false
formal pass + semantic >0 → semantic_valid true
zero-row comparison → measured false
scorable row → measured true
empty echo classification
contentful observation classification
duplicate classification
maxItems flag
```

---

# 29. P1 acceptance

- [ ] 0 inference
- [ ] new dev-report tool
- [ ] current 001D identity only
- [ ] no fallback
- [ ] semantic helper reused
- [ ] formal metrics
- [ ] semantic metrics
- [ ] measurement gate
- [ ] echo v2
- [ ] duplicate metrics
- [ ] overclaim metrics
- [ ] no ledger mutation
- [ ] focused tests green
- [ ] report/handoff updated

---

# 30. Şimdiki asıl blocker #2 — dev input PNG'leri yok

Current report/handoff:

```text
dry-run planned_real_calls = 0
```

diyor.

Sebep:

```text
001D corpus page PNGs not installed
```

Bu first live call öncesi gerçek blocker.

---

# 31. 001D dev corpus ne olmalı?

001D development için aynı 4 dev source kullanılabilir:

```text
dev-plate-pocket
dev-flange-book
dev-flange-elbow
dev-drawing-2
```

Bunlar final holdout değildir.

Ama 001D input bytes:

```text
deterministic
versioned
hash-checked
```

olmalı.

---

# 32. Historical prepared PNG'yi kör reuse etme

001C out klasöründeki prepared image:

```text
READ-ONLY historical artifact
```

olabilir.

001D production input pipeline:

```text
source file
→ current preprocessing
→ 001D prepared input
```

şeklinde yeniden üretilebilir.

Ama byte identity bekleniyorsa bunu açıkça test et.

---

# 33. Source-of-truth

Dev corpus source-of-truth:

```text
repo examples/source file
+
page selector
+
preprocessing contract
```

olmalı.

Historical `out/lab/semread-001c` output'u source-of-truth yapma.

---

# 34. P2 — deterministic input materialization

Yeni veya mevcut corpus-builder ile 4 dev page için:

```text
prepared raw page PNG
```

oluştur.

Her page:

```text
source path
source_sha256
page index / view
prepared_sha256
width
height
preprocessing_identity
```

kaydet.

---

# 35. V/VE raw page invariant

Aynı page için:

```text
raw page bytes V == raw page bytes VE
```

zorunlu.

VE yalnız ek:

```text
overlay
observation table
```

alır.

---

# 36. 001D input root

Önerilen ayrım:

```text
out/lab/semread-001d/inputs/
```

veya mevcut lifecycle'ın canonical path'i.

Ama:

```text
attempt
budget
input preparation
```

sorumlulukları karışmamalı.

Input prep budget harcamaz.

---

# 37. Input preparation inference değildir

Aşağıdakiler inference sayılmaz:

```text
PDF render
PNG resize
deterministic overlay
observation serialization
hash
prompt serialization
token estimate
```

Ama VLM çağrısı yok.

---

# 38. Input materialization leakage check

Input builder:

```text
gold
expected semantic answer
reference STEP
```

okumamalı.

Yalnız:

```text
source page
deterministic observations for VE
```

kullanmalı.

---

# 39. Input artifact acceptance

Her dev page:

```text
raw_page_sha256
V raw sha
VE raw sha
```

aynı.

VE overlay ayrı hash.

Observation table deterministic hash.

---

# 40. P2 acceptance

- [ ] 0 inference
- [ ] 4 dev pages installed
- [ ] source hashes
- [ ] prepared hashes
- [ ] V/VE raw bytes identical
- [ ] no gold access
- [ ] preprocessing identity current
- [ ] deterministic rebuild
- [ ] dry-run planned_real_calls = 4 for Round 1
- [ ] budget still 0/12

---

# 41. Dry-run 0 artık kabul edilmemeli

Şu an:

```text
planned_real_calls = 0
```

bilinen eksik input nedeniyle.

P2 sonrası Round-1 dry-run:

```text
planned_real_calls = 4
```

olmalı.

Aksi halde live dispatch yok.

---

# 42. P3 — static preflight

Dev-report ve inputs hazır olduktan sonra:

```text
static preflight
```

kapanmalı.

0 inference.

---

# 43. Static identity checks

Kontrol:

```text
experiment = semread-001d
schema = /3
reader = /3
contract = 001d/1
producer identity current
preprocessing identity current
evaluation identity current
```

---

# 44. Budget checks

```text
dev used = 0
dev cap = 12
final used = 0
final cap = 20
```

Round 1 öncesi exactly böyle.

---

# 45. Model checks

Local runtime:

```text
model tag exact
digest exact
runtime exact
```

Mismatch:

```text
block
```

---

# 46. Shared generation settings

Static:

```text
generation_settings(V) == generation_settings(VE)
```

assert.

---

# 47. Prompt serialization

4 Round-1 jobs için:

```text
prompt bytes
prompt token estimate / actual tokenizer count if available
image bytes
observation row count
```

kaydet.

---

# 48. Context headroom

Her job:

```text
prompt_tokens + NUM_PREDICT <= NUM_CTX
```

olmalı.

Tercihen safety headroom raporla.

---

# 49. Context gate fail olursa

Live call yok.

Önce:

```text
hangi cell
prompt kaç token
headroom ne kadar negatif
```

yaz.

Sonra contract revision kararı.

Ama current evidence olmadan `num_ctx` artırma yok.

---

# 50. Structured-output schema compatibility

`anyOf` eklenmedi.

Doğru.

Current schema'nın backend structured-output formatında kabul edildiğini static/synthetic testle kanıtla.

Live semantic call harcama.

---

# 51. Dry-run manifest

Her Round-1 cell:

```text
page id
arm
phase=dev
experiment
schema
reader
contract
producer
preprocessing
input hash
generation settings hash/signature
```

göstermeli.

---

# 52. P3 acceptance

- [ ] 0 inference
- [ ] 4 planned calls
- [ ] input exists
- [ ] correct identities
- [ ] correct hashes
- [ ] budget 0/12
- [ ] model exact
- [ ] digest exact
- [ ] runtime exact
- [ ] V==VE settings
- [ ] V/VE raw identity
- [ ] context headroom
- [ ] schema backend-compatible
- [ ] closure 45/45

---

# 53. P4 — pre-live test gate

Static preflight sonrası:

```text
focused 001D tests
dev-report tests
identity tests
candidate/reader tests
lifecycle tests
gates
001C closure
D regression
```

koş.

---

# 54. Gates

Current identity committe:

```text
34/34
```

geçti.

Dev-report + input/preflight kodu eklendiği için ilk live call öncesi tekrar:

```text
34/34
```

geçmeli.

---

# 55. Acceptance tests

Dev-report evaluator/acceptance logic'e dokunuyorsa:

```text
relevant acceptance tests
```

yeniden koş.

001B acceptance suite full 27 test pahalı (~32 dk), ama measurement gate ortak logic değişirse değerli.

---

# 56. Full pytest henüz değil

Round 1 öncesi full suite ~70 dk gereksiz.

Pre-live için:

```text
focused
gates
closure
D regression
relevant acceptance
```

yeterli.

---

# 57. Round 1 — ilk live inference

Yalnız P1–P4 kapandıktan sonra.

Exactly:

```text
dev-plate-pocket V
dev-plate-pocket VE
dev-flange-book V
dev-flange-book VE
```

4 call.

---

# 58. Dispatch sequential

Round 1:

```text
sequential
```

koş.

001C'deki queue/kill belirsizliğini tekrar etme.

---

# 59. Pre-dispatch session hygiene

Kontrol:

```text
Ollama active request yok
queue boş
correct model loaded
digest exact
runtime exact
```

---

# 60. Budget reservation

Her call öncesi:

```text
reserve budget
persist attempt manifest
persist input identity
persist producer identity
```

sonra request.

Failure da call sayılır.

---

# 61. Round 1 formal gate

4/4:

```text
send attempted
valid response
done_reason = stop
coordinate valid
refs valid
leak clean
correct contract
shared settings
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
V field accuracy > 0
VE field accuracy > 0
```

---

# 63. Semantic-valid output rate

Round 1:

```text
semantic_valid_output_rate = 4/4
```

gate.

Bu:

```text
formal valid
AND semantic content
```

---

# 64. Why 4/4 semantic content?

001C'nin ana failure'ı:

```text
0/8 semantic content
```

idi.

001D'nin hypothesis'i doğrudan bunu düzeltmek.

İlk round'da herhangi bir hücre yine evidence-only/empty kalıyorsa contract hypothesis eksik.

---

# 65. Gold match aggregate neden ayrıca gerekli?

Model semantic-looking şey üretebilir ama hepsi yanlış olabilir.

Bu nedenle:

```text
semantic_claim_count > 0
```

tek başına yeterli değil.

Her arm'da en az bir actual gold match istenir.

---

# 66. Overclaim guard

Özellikle:

```text
size
count
R/Ø
THRU
depth
physical
```

hallucination say.

No-guess contract korunmalı.

---

# 67. Round 1 başarısızsa

Yeni call YOK.

Önce dev-report + raw output forensic analysis.

---

# 68. Reserve policy

001D dev budget:

```text
12
```

Dağılım:

```text
8 primary
4 diagnostic/requalification
```

Reserve keyfi retry değildir.

---

# 69. Tek revision hakkı

Round 1 fail ise:

```text
ONE contract revision
```

izinli.

Önceden yazılı hypothesis.

Örnek:

```text
prompt task decomposition clarification
```

ama:

```text
sampling sweep
model change
page-specific fix
```

değil.

---

# 70. Requalification

Revision sonrası:

```text
same 4 Round-1 cells
```

tamamı yeniden.

Tek kötü cell redo yok.

---

# 71. İkinci Round-1 de fail ise

001D kapanır.

```text
Round 2 yok
holdout yok
final yok
budget increase yok
```

001E gerekir.

---

# 72. Round 2

Round 1 pass ve contract freeze sonrası:

```text
dev-flange-elbow V
dev-flange-elbow VE
dev-drawing-2 V
dev-drawing-2 VE
```

4 call.

---

# 73. Round 2 tuning yok

Round 2 sonucu neyse kaydedilir.

Prompt/schema/settings değişmez.

---

# 74. Primary 8 gate

Holdout'a geçmek için:

```text
formal valid 8/8
semantic valid 8/8
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
all maxItems
VE table-copy dominates
semantic claims mostly fabricated
one arm semantic accuracy = 0
```

---

# 76. Full pytest

Primary 8 sonrası:

```bash
.venv/bin/python -m pytest -q
```

zorunlu.

0 fail.

---

# 77. Full test kayıt formatı

Kaydet:

```text
HEAD
collection count
passed
failed
skipped
runtime
```

Collection loss varsa açıklama.

---

# 78. External CI

Current HEAD için external commit status yok.

Report:

```text
External CI: none
```

demeye devam etmeli.

Local evidence authority.

---

# 79. Repo hygiene

Her milestone sonrası:

```text
report.md
HERMES_SEMREAD_001D_HANDOFF.md
active PLAN
budget state
```

aynı facts.

---

# 80. PLAN history

Current tracked:

```text
PLAN-15
```

Bu yeni plan repo authority yapılacaksa:

```text
PLAN-16
```

yeni history entry olarak daha doğru.

PLAN-15 rewrite etme.

---

# 81. Current root report

Kök report experiment-neutral living document olarak kalmalı.

001D current üstte.

001C sadece HISTORICAL.

---

# 82. Handoff next-step formatı

Her milestone:

```text
CURRENT HEAD
CURRENT EXPERIMENT
IMMUTABLE HISTORY
WHAT CHANGED
TEST EVIDENCE
INFERENCE BUDGET
OPEN GATE
NEXT SINGLE STEP
```

---

# 83. 001C invariant

Milestone'larda:

```text
closure verify 45/45
```

korunmalı.

001C lab'a write yok.

---

# 84. Holdout zamanı

Yalnız:

```text
Primary 8 pass
+
full pytest 0 fail
```

sonrası.

---

# 85. Holdout kaynağı

Repo examples unseen değil.

Tercih:

```text
12–20 yeni technical drawing
```

kullanıcıdan alınır.

10 final page model görmeden seçilir.

---

# 86. Final holdout eligibility

```text
repo history'de yok
001B/001C/001D dev'de yok
duplicate değil
SEMREAD scope claim var
```

Hash/group identity.

---

# 87. Holdout gold

Model output görülmeden hazırlanır.

Existing gold framework reuse.

---

# 88. Freeze

Freeze bağlamalı:

```text
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

# 89. Final inference

```text
10 pages × V/VE = 20
retry = 0
```

No post-freeze tuning.

---

# 90. Final metrics

Önce:

```text
formal_valid_output_rate
semantic_valid_output_rate
```

Sonra field metrics.

---

# 91. 001D karar ağacı

## V + VE semantic başarılı

Final experiment mantıklı.

## V başarılı, VE değil

Evidence formatı zarar veriyor olabilir.

## VE başarılı, V değil

Observations kritik yardım sağlıyor.

## İkisi de başarısız

Full-page single-shot yaklaşım kapatılır.

001E farklı architecture:

```text
crop-first
detect→read
OCR-first
one-callout-per-query
typed subquestions
```

---

# 92. Şu anda YAPMA

```text
live call before dev-report
live call before input install
live call while dry-run says 0
sampling tuning
model change
num_ctx blind increase
single-cell retry
budget increase
001C fallback
silent repair
holdout work
CAD/planner detour
```

---

# 93. Commit planı

Current HEAD sonrası:

```text
1. semread-001d: dev-report formal + semantic + measurement gates
2. semread-001d: dev input materialization + raw-page identity
3. semread-001d: static preflight + context/dry-run 4 calls
4. semread-001d: pre-live test evidence
5. semread-001d: Round 1 four calls
6. semread-001d: Round 1 semantic report
7. optional ONE revision + 4-cell requalification
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

# 94. ŞİMDİKİ TEK SOMUT İŞ

**0 inference.**

İlk iş:

```text
eval/semread_001d_dev_report.py
```

ve testleri.

Bu araç current 001D attempt yokken bile:

```text
all dev cells = missing
measurement = false
semantic_valid = false
```

diye dürüstçe raporlamalı.

---

# 95. İlk commit acceptance

- [ ] 0 inference
- [ ] dev-report exists
- [ ] only current 001D identity eligible
- [ ] 001B/001C fallback yok
- [ ] no attempt = missing
- [ ] formal metrics
- [ ] semantic metrics
- [ ] semantic helper reused
- [ ] real measurement gate
- [ ] zero-row comparison measured=false
- [ ] echo v2
- [ ] duplicates
- [ ] overclaim
- [ ] maxItems flag
- [ ] no ledger mutation
- [ ] tests green
- [ ] closure 45/45
- [ ] report/handoff aligned

---

# 96. Sonraki tek iş

Dev-report kapandıktan sonra:

```text
001D dev input/corpus PNG materialization
```

gelir.

Ama dev-report tamamlanmadan input prep ile evaluator geliştirmeyi paralelleştirme.

---

# 97. İlk live call için absolute blockers

Aşağıdakilerden biri varsa inference yok:

```text
dev-report missing
dev inputs missing
dry-run planned_real_calls != 4
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

# 98. Son yön

Şu an producer contract doğru.

Bir sonraki bilimsel risk:

```text
ölçüm başladıktan sonra evaluator/gate tanımını değiştirmek
```

Bu yüzden önce dev-report.

Bir sonraki operasyonel risk:

```text
input corpus kurulmadan canlı çağrıya geçmek
```

Bu yüzden dev-report sonrası input materialization.

Doğru kısa rota:

```text
dev-report
→ dev inputs
→ static preflight
→ 4-call Round 1
→ semantic proof
```
