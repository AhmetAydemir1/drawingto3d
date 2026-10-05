# PLAN.md — drawingto3d / SEMREAD-001D
## Semantic-content validator sonrası güncel uygulama planı

**Tarih:** 2026-10-05  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Gözlenen `main` HEAD:** `4777caf609aef0e775bed9a2681eb3948e0ca278`  
**Aktif deney:** `SEMREAD-001D`  
**Aktif tracked plan:** `docs/PLAN-14.md` (`a027cb4a…` revizyonu)  
**001D bütçe:** dev `0/12`, final `0/20`, toplam `0/32`  
**001C:** CLOSED / READ-ONLY HISTORICAL  
**001C closure:** `--verify 45/45`  
**External CI/status:** yok  
**Full pytest:** güncel 001D ağacı için henüz yeniden çalıştırılmadı

---

# 0. Yönetici özeti

Önceki plandaki ilk kritik iş artık tamam:

```text
semantic claim != evidence-only
```

ayrımı tek kaynak olarak kodlandı.

Repo artık:

```text
semantic_claim_flags
candidate_has_semantic_claim
evidence_flags
```

fonksiyonlarını taşıyor.

Wire parser:

```text
JSON
→ structural validation
→ semantic-content validation
→ references
```

sırasına geçti.

Semantic-empty candidate:

```text
schema_semantic_empty
```

ile reddediliyor.

Boş `items` ise gerçek abstention olarak geçerli kalıyor.

Bu değişiklik `0 inference` ile yapıldı.

Şimdi sıradaki darboğaz artık validator değil. Sıradaki zorunlu iş 001D producer identity oluşturmak:

```text
semread-candidates/3
semread-candidate-reader/3
semread-001d-run-contract/1
prompt v3
```

Bunlar tamamlanmadan canlı 001D çağrı YOK.

---

# 1. Güncel repo kanıtı

Tamamlanan 001D işleri:

```text
001C hygiene + closure
001D skeleton
budget predeclaration
semantic claim definition
evidence-only separation
semantic-empty wire rejection
D-path audit
root report experiment-neutral refactor
```

Test kanıtı:

```text
001D semantic-content tests  32 passed
focused suite               131 passed
quick SEMREAD               143 passed
001B evaluation              32 passed
gates                        34/34
001C closure verify          45/45
```

Inference:

```text
dev   0/12
final 0/20
```

---

# 2. Current identity problemi

Kod davranışı 001D yönüne değişmiş olsa da version identity henüz 001D değil.

Current:

```text
CANDIDATE_SCHEMA_VERSION = semread-candidates/2
CANDIDATE_READER_VERSION = semread-candidate-reader/2
CONTRACT_VERSION         = semread-001c-run-contract/1
```

Bu haliyle canlı çağrı yapmak yasak. Çünkü attempt 001D ledger altında yazılsa bile producer contract tarihsel olarak 001C kimliği taşır.

---

# 3. P1 — schema/reader v3

Bir sonraki commit:

```text
semread-candidates/3
semread-candidate-reader/3
```

bump'ını yapmalı.

`/3` anlamı açıkça:

```text
semantic-empty candidate invalid
semantic claim != evidence-only
prompt semantic-first
no-guess retained
```

olarak version notes'ta yazılmalı.

---

# 4. P1.1 — JSON Schema v3 modelin contract'ı görmeli

Parser'ın semantic-empty reddi var ama modelin gördüğü şema da bu yeni beklentiyi anlatmalı.

Candidate item description:

```text
A candidate must contain at least one semantic claim.
A region, representation, found-circle count, target binding,
observation id or uncertainty alone is not a semantic claim.
```

taşımalı.

Schema mümkün olduğunca model contract'ıyla parser contract'ını aynı yönde tutmalı.

---

# 5. JSON Schema anyOf kararı

Semantic claim zorunluluğunu JSON Schema `anyOf` ile tam encode etmek teorik olarak mümkün. Fakat structured-output backend'in karmaşık nested `anyOf` desteği kanıtlanmadan bunu production schema'ya ekleme.

Önerilen sıra:

```text
1. prompt + schema descriptions
2. parser strict semantic-empty validation
3. synthetic schema compatibility tests
4. backend format acceptance static/probe evidence
5. ancak gerekiyorsa anyOf
```

İlk v3 commit'i gereksiz schema karmaşıklığına dönüştürme.

---

# 6. P1.2 — Prompt v3

Yeni ortak V/VE task'ın ilk sıraları:

```text
First identify a printed semantic fact.
Only then create a candidate.
A region alone is not a candidate.
A machine observation row is not a semantic claim.
```

Ana kural:

```text
Do not emit a candidate unless it contains at least one semantic claim.
```

---

# 7. Prompt v3 — semantic claim definition

Prompt model açısından kısa ve mekanik olmalı.

Semantic claim örnekleri:

```text
printed callout text
R / Ø symbol
printed size
printed count
explicit THRU
explicit finite depth
physical meaning explicitly supported by drawing
```

Evidence-only:

```text
circle/arc representation
found circle count
target box
observation id
source region
uncertainty note
```

tek başına candidate üretmemeli.

---

# 8. Prompt v3 — no-guess anti-pressure

Semantic-content gate hallucination yaratabilir. Bu yüzden prompt aynı yerde şunu söylemeli:

```text
If you cannot read at least one semantic fact, emit no candidate for that feature.
Do not invent a semantic fact merely to satisfy the semantic-content requirement.
```

Bu cümle zorunlu.

---

# 9. Prompt v3 — VE echo yasağı

VE common task aynı kalır; evidence section ekstra.

VE section:

```text
Observations are evidence, not candidate seeds.
Do not create one candidate per observation row.
Use an observation only if it helps support a semantic claim.
```

demeli.

---

# 10. P2 — run-contract 001D/1

Schema/reader v3 commitinden hemen sonra:

```text
CONTRACT_VERSION = semread-001d-run-contract/1
```

olmalı.

Docstring current state'i 001D olarak anlatmalı; 001C history closure artifact'ında kalır.

---

# 11. 001D generation envelope

Başlangıçta 001C'nin kanıtlanmış shared envelope'u reuse edilir:

```text
model          qwen3-vl:8b-instruct
digest         0533d743...
runtime        0.32.1
num_ctx        22528
num_predict    8192
temperature    0.0
repeat_penalty 1.25
repeat_last_n  512
maxItems       32
image_max_side 1280
```

Identity 001D olur çünkü prompt/schema/parser semantics değişti.

---

# 12. Generation settings'e dokunma

001D hipotezi:

```text
semantic-content-aware contract
```

olmalı.

Aynı anda temperature/repeat penalty/context/predict/image resize değiştirme. Aksi halde semantic-content değişikliğinin etkisini ayıramayız.

---

# 13. V/VE causal invariant

Zorunlu:

```text
generation_settings(V) == generation_settings(VE)
```

Tek izin verilen fark:

```text
evidence_mode
overlay
observation table
evidence prompt section
image count
```

---

# 14. Producer identity

`producer_identity()` current producer sources'ı hash'lemeye devam etmeli. Version metadata ayrıca attempt manifestinde açıkça okunabilmeli.

---

# 15. Attempt manifest acceptance

İlk canlı call öncesi dry-run manifest:

```text
experiment = semread-001d
schema_version = semread-candidates/3
reader_version = semread-candidate-reader/3
contract_version = semread-001d-run-contract/1
phase = dev
```

taşımalı.

Bunlardan biri yanlışsa gönderim bloklanmalı.

---

# 16. 001C closure coupling testi

Version bump sonrası:

```text
eval/semread_001c_closure.py --verify
```

sonuç:

```text
45/45
```

olmalı.

Geçmezse canlı inference yok.

---

# 17. P3 — 001D dev metrics

Semantic helper artık var. 001D dev report bunu doğrudan reuse etmeli.

Yeni salt-okur araç:

```text
eval/semread_001d_dev_report.py
```

veya versioned ortak rapor katmanı.

Kopya semantic logic yok.

---

# 18. Dev report formal metrics

Her cell:

```text
attempt state
parse valid
done_reason
coordinate valid
reference valid
leak clean
shared settings
producer identity
candidate count
```

---

# 19. Dev report semantic metrics

Her cell:

```text
semantic_claim_count
semantic_candidate_rate
semantic claim fields
evidence_only_count
gold matched claims
field accuracy
abstention
overclaim
```

---

# 20. Echo metriği v2

VE için iki tür:

### empty_echo

```text
observation region echoed
semantic claim yok
```

001D parser yüzünden normal valid result içinde olmamalı.

### contentful_observation_supported

```text
observation region matched
AND semantic claim exists
```

Bu otomatik hata değildir. Gold doğruluğu belirler.

---

# 21. Duplicate metriği v2

Ayrı say:

```text
exact region duplicate
near region duplicate
same semantic signature + same target
same callout repeated
```

Parser dedupe etmez; raporlar.

---

# 22. maxItems metriği

```text
candidate_count == 32
```

ise `max_items_hit = true` raporlanmalı. Bu doğrudan failure değildir ama sürekli 32 degeneracy warning olur.

---

# 23. P4 — static preflight

0 inference.

Kontrol:

```text
schema /3
reader /3
run-contract 001d/1
budget dev 0/12
budget final 0/20
001D attempt root
producer identity
evaluation identity
V==VE settings
prompt identity
model tag/digest/runtime
context headroom
001C closure verify
```

---

# 24. Prompt-size preflight

Round 1 dört cell için model çağırmadan prompt serialize et ve context ölç.

001C'de context sorunları yaşandığı için:

```text
prompt + num_predict <= num_ctx
```

headroom kontrolü zorunlu.

---

# 25. Context policy

001D semantic prompt uzayacak. Aynı `22528/8192` otomatik güvenli varsayılmamalı.

İlk çözüm num_ctx artırmak değil; static measurement.

Sığmıyorsa live call yok ve plan revizyonu gerekir.

---

# 26. P5 — ilk inference öncesi tests

Zorunlu:

```text
test_semread_001d_semantic_content.py
candidate tests
candidate reader tests
001d skeleton
identity/lifecycle
001d dev report tests
relevant gates
001C closure verify
```

---

# 27. Gates

Son kanıt:

```text
34/34
~16:54
```

v3 identity değişikliklerinden sonra tekrar koşulmalı.

İlk inference öncesi 34/34 yeniden şart.

---

# 28. D regression

4 dev page D kolunu offline doğrula.

Amaç:

```text
wire semantic-empty rule D'yi etkilemiyor
```

kanıtı.

---

# 29. Full pytest zamanlaması

İlk 4 call öncesi full suite zorunlu değil.

İlk çağrı öncesi:

```text
focused + gates + closure + D regression
```

yeterli.

Primary 8 tamamlandığında full pytest zorunlu.

---

# 30. Dev budget — kilitli

```text
dev max = 12
final max = 20
total = 32
```

Artış yok.

---

# 31. Round 1

İlk 4 gerçek call:

```text
dev-plate-pocket V
dev-plate-pocket VE
dev-flange-book V
dev-flange-book VE
```

Sıralı tercih edilir; Ollama queue/memory etkisini azaltır.

---

# 32. Round 1 formal gate

Her cell 4/4:

```text
state = pass
done_reason = stop
coordinate valid
refs valid
leak clean
shared settings
current 001D producer identity
```

---

# 33. Round 1 semantic gate

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

# 34. Semantic-valid output rate

Yeni ana metric:

```text
semantic_valid_output = formal valid AND semantic_claim_count >= 1
```

Round 1 gate: 4/4.

---

# 35. Overclaim gate

Ayrıca:

```text
invented size
invented count
invented THRU
invented depth
unsupported physical interpretation
```

ayrı raporla.

Semantic-content artışı hallucination artışı olursa başarı sayma.

---

# 36. Round 1 failure policy

Round 1 geçmezse önce 0-inference offline diagnosis.

Reserve 4 call var ama yalnız:

```text
ONE contract revision
```

izinli.

Sonra aynı 4 Round-1 cell yeni contract ile tekrar koşulur.

Tek hücre cherry-pick redo yok.

---

# 37. Reserve kullanım kuralı

Reserve şu işler için kullanılamaz:

```text
bir tane daha deneyelim
sadece V'yi tekrar koş
sadece kötü hücreyi kurtar
sampling taraması
hyperparameter search
```

Yalnız tek hipotez + tam 4-cell requalification.

---

# 38. Round 1 ikinci kez başarısızsa

001D kapanır:

```text
Round 2 yok
holdout yok
final yok
budget artışı yok
```

Yeni experiment gerekir.

---

# 39. Round 2

Round 1 geçerse contract kilitlenir.

Sonra:

```text
dev-flange-elbow V
dev-flange-elbow VE
dev-drawing-2 V
dev-drawing-2 VE
```

4 call.

---

# 40. Round 2'de tuning yok

Round 2 sırasında prompt/schema/generation/parser semantics değişmez.

Failure 001D sonucu olarak kalır.

---

# 41. Primary 8 acceptance

Holdout'a geçmek için:

```text
formal valid 8/8
semantic-valid 8/8
stop 8/8
coordinate 8/8
refs 8/8
leak clean 8/8
shared settings 8/8
```

Semantic aggregate:

```text
V field accuracy > 0
VE field accuracy > 0
```

---

# 42. Degeneracy blockers

Holdout yok eğer:

```text
all outputs maxItems
all VE candidates observation echoes
duplicate flood dominates
semantic claims mostly fabricated
one arm semantic claim rate = 0
```

---

# 43. Primary 8 sonrası full pytest

Şart:

```bash
.venv/bin/python -m pytest -q
```

Kayıt:

```text
passed
failed
runtime
collection count
```

0 fail.

---

# 44. CI

Current HEAD için external status yok.

Raporda açıkça:

```text
External CI: none
Acceptance evidence: local pytest + eval artifacts
```

yaz.

CI kurmak holdout'u geciktiren yan proje olmasın.

---

# 45. Repo hijyeni

Her milestone sonrası:

```text
docs/PLAN-14.md veya yeni PLAN history
HERMES_SEMREAD_001D_HANDOFF.md
report.md
budget state
run contract
```

aynı current facts'i taşımalı.

---

# 46. Plan history

Tracked plan değiştikçe yeni sha handoff/report'ta güncellenmeli. Eski revision git history'de kalmalı.

---

# 47. 001C immutable invariant

001D hiçbir adım `out/lab/semread-001c/**` yazmamalı.

Closure verify bozulursa inference block.

---

# 48. Holdout girişi

Primary 8 + full pytest geçmeden yeni çizimlerde inference yapma.

Tercih:

```text
12–20 yeni çizim
```

Bunlardan deterministic selection ile 10 final page.

---

# 49. Holdout eligibility

```text
repo history'de yok
001B/001C/001D dev'de yok
duplicate değil
technical drawing
SEMREAD scope callout içeriyor
```

Hash + group id.

---

# 50. Holdout diversity

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
rotated callout
crowded leaders
multi-view
low resolution
clean vector
```

---

# 51. Holdout gold

V/VE output görülmeden.

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

# 52. D baseline

Holdout D, V/VE finalden önce deterministic çalışır. Page selection D sonucuna göre değiştirilmez.

---

# 53. Freeze blockers

```text
schema /3
reader /3
001d-run-contract/1
primary 8 dev pass
semantic sanity
full pytest 0 fail
holdout 10/10
D baseline
final 0/20
model/digest/runtime
context preflight
V/VE raw page invariant
shared settings
leak audit
clean clone
001C closure verify
```

---

# 54. Final inference

```text
10 page × V/VE = 20
retry = 0
```

Finalde prompt tune/schema change/sampling change/parser repair yasak.

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

# 57. Latency / resource

V ve VE ayrı:

```text
prompt tokens
eval tokens
latency
candidate count
semantic candidate count
maxItems hit
```

---

# 58. Karar ağacı

## V ve VE ikisi de semantic olarak faydalı
001D final'e değer.

## V iyi, VE kötü
Evidence representation zararlı olabilir.

## VE iyi, V kötü
Deterministic observation evidence kritik olabilir.

## İkisi de yine semantic üretmiyor
Full-page single-shot architecture uygun değil.

Sonraki experiment:

```text
crop-first
detect→read
OCR-first
one-callout-per-query
typed subquestions
```

---

# 59. 001D içinde yapma

```text
crop pipeline
multi-stage reader
OCR-first rewrite
new model family search
sampling sweep
automatic coordinate repair
semantic-empty candidate repair
silent dedupe
retry-until-pass
budget increase
```

---

# 60. Commit planı

Current HEAD sonrası:

```text
1. schema/reader /3 + prompt v3
2. 001d run-contract /1 + producer identity
3. 001d dev-report echo/duplicate metrics
4. static preflight + identity/closure/gates evidence
5. Round 1 four live calls
6. Round 1 semantic evaluation
7. optional ONE contract revision + full four-call requalification
8. Round 2 four live calls
9. primary dev report + full pytest
10. holdout intake/selection
11. holdout gold
12. D baseline + clean clone
13. freeze
14. final 20
15. immutable final report
```

---

# 61. ŞİMDİKİ TEK SOMUT İŞ

**Inference YOK.**

Bir sonraki commit:

```text
semread-candidates/3
semread-candidate-reader/3
prompt v3
```

olmalı.

İçerik:

```text
semantic-first instructions
region-alone-is-not-candidate
observation-row-is-not-claim
no one-row-one-candidate
if no semantic fact → omit candidate
do not invent fact to satisfy gate
```

---

# 62. Bu commit acceptance

- [ ] 0 inference
- [ ] schema version /3
- [ ] reader version /3
- [ ] prompt semantic-first
- [ ] prompt evidence-only ayrımını anlatıyor
- [ ] prompt no-guess anti-pressure içeriyor
- [ ] V ve VE common task byte-identical
- [ ] VE farkı yalnız evidence section
- [ ] parser semantic-empty strict kalıyor
- [ ] empty `items` valid abstention
- [ ] no page-specific text
- [ ] no gold value
- [ ] focused tests green
- [ ] 001C closure 45/45

---

# 63. Sonraki commit acceptance — run-contract

- [ ] `semread-001d-run-contract/1`
- [ ] current docstring 001D
- [ ] shared envelope unchanged
- [ ] V==VE settings
- [ ] model/digest/runtime unchanged
- [ ] producer identity changed
- [ ] dry-run manifest says semread-001d
- [ ] budget remains 0/12 + 0/20
- [ ] closure 45/45

---

# 64. İlk canlı çağrı için absolute blockers

Aşağıdakilerden biri varsa canlı inference YOK:

```text
schema != /3
reader != /3
contract != 001d/1
prompt v3 missing
budget != 0/12
001C closure != 45/45
gates != 34/34
V/VE settings differ
model digest mismatch
runtime mismatch
context preflight fails
manifest identity wrong
```

---

# 65. Son yön

Semantic validator artık yapıldı.

Şimdi doğru rota:

```text
semantic contract'ı modelin gördüğü prompt/schema kimliğine taşı
→ 001D producer identity'yi ayır
→ inference öncesi statik kanıt
→ yalnız sonra 4-call Round 1
```

Kısa rota:

```text
/3 prompt+schema
→ 001d/1 contract
→ dev report
→ preflight
→ 4 live calls
→ semantic evaluation
```
