# PLAN.md — drawingto3d / SEMREAD-001C

## Dev 8/8 sonrası güncel plan

**Tarih:** 2026-10-05  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Gözlenen `main` HEAD:** `1f5977ae35068c18aee476fb8d8ef512cf66e4a4`  
**001B:** immutable kapanmış deney  
**001C dev fazı:** 8/8 geçerli hücre  
**001C dev çağrı:** 24/24 kullanıldı  
**001C final çağrı:** 0/20  
**Final holdout:** henüz yok  
**Son full pytest kanıtı:** 1188 passed, 0 fail — son 001C envelope değişikliklerinden önce

---

# 1. Şu an neredeyiz?

SEMREAD-001C'nin P0–P6 işleri tamamlandı:

```text
001B immutable closure
→ region contract v2
→ compact wire response
→ evidence serialization pruning
→ truncation/failure taxonomy
→ ayrı 001C ledger
→ ölçülmüş generation envelope
→ dev 8/8 valid output
```

Dev kapısı:

```text
V 4/4 valid
VE 4/4 valid
stop 8/8
coordinate 8/8
refs 8/8
leak clean 8/8
valid_output_rate = 1.0
```

Ama final freeze'e doğrudan geçilmeyecek.

İki açık bilimsel borç var:

```text
1. V ve VE aynı generation settings ile çalışmıyor.
2. 8/8 output-valid sonuç henüz semantic olarak dev gold'a karşı puanlanmadı.
```

---

# 2. Kritik deney tasarımı problemi

Güncel run contract:

```text
num_ctx = 22528
num_predict = 8192
temperature = 0.0
repeat_last_n = 512
repeat_penalty V = 1.4
repeat_penalty VE = 1.25
```

SEMREAD'in V/VE sorusu:

```text
VE evidence, V'ye göre semantic okumayı iyileştiriyor mu?
```

Bu soruda:

```text
model
digest
runtime
task
schema
raw image
generation settings
```

aynı olmalı.

Tek fark:

```text
VE evidence
```

olmalı.

Bu yüzden arm-specific repeat penalty final experiment için kabul edilemez.

---

# 3. İlk iş — OFFLINE dev semantic evaluation

**Canlı model çağrısı yok.**

Mevcut seçili valid attempt'leri existing dev gold ile değerlendir:

```text
dev-plate-pocket
dev-flange-book
dev-flange-elbow
dev-drawing-2
```

Kollar:

```text
D
V
VE
```

Metrikler:

```text
candidate_count
matched_count
localization
representation
physical
form
size
count_printed
termination
depth
target_binding
overclaim
abstention
false_positive
unscorable_extra
ambiguous
```

Özellikle:

```text
plate-VE = 41 aday
bazı V/VE hücreleri = 1 aday
```

analiz edilmeli.

Amaç:

```text
parse-valid output semantic olarak tamamen degenerate mı?
```

sorusuna cevap vermek.

Inference:

```text
0
```

---

# 4. Shared generation envelope

Finalde:

```text
generation_settings(V) == generation_settings(VE)
```

zorunlu.

Arm-specific repeat penalty kaldırılmalı.

Mevcut gözlem:

```text
1.25 → V elbow tekrar döngüsü
1.4  → VE plate output aşırı bastırılıyor
```

Bunu farklı sampling ile değil structural output contract ile çöz.

---

# 5. Structural anti-loop

Ortak prompt:

```text
Emit at most one candidate for the same visible callout→target pair.
Do not repeat a candidate with a new candidate_id.
When all supported visible callouts are reported, close the items array.
```

Ortak schema:

```text
items.maxItems = 32
```

başlangıç adayı.

Gerekçe:

```text
dev gold'a geniş headroom
8192 output içinde bounded response
64-item tekrar loop'unu durdurma
```

Bu pilot limiti; ürünün nihai kapasitesi değil.

Parser strict kalır.

Yasak:

```text
silent dedupe
truncated JSON repair
pixel auto-normalization
```

---

# 6. Shared repeat penalty

Structural cap sonrası ortak başlangıç:

```text
repeat_penalty = 1.25
repeat_last_n = 512
```

Bunun nedeni VE'nin zengin output rejimini korumasıdır.

Ama 8 dev hücre yeniden doğrulanmadan freeze edilmez.

---

# 7. Dev budget final düzeltmesi

Mevcut:

```text
24/24 used
```

Causal requalification için çağrıdan ÖNCE tek seferlik:

```text
dev ceiling = 32
```

tanımla.

Yeni 8 call:

```text
4 dev page × V/VE
```

Sonra dev tuning biter.

32 sonrası geçmezse:

```text
001C final yok
yeni experiment version
```

Call-call bütçe artırma yok.

---

# 8. Shared-envelope requalification

Aynı 4 dev page × V/VE:

```text
8 calls
```

Gate:

```text
valid_result 8/8
done_reason=stop 8/8
coordinate valid 8/8
refs valid 8/8
leak clean 8/8
shared num_ctx
shared num_predict
shared temperature
shared repeat_penalty
shared repeat_last_n
shared schema
shared task
```

İzin verilen arm farkı yalnız:

```text
evidence_mode
overlay
observation table
evidence prompt section
image count
```

Otomatik invariant testi:

```text
generation_settings(V) == generation_settings(VE)
```

---

# 9. Requalification sonrası semantic sanity

Yeni 8 attempt yeniden dev gold'a karşı puanlanır.

Freeze blocker örnekleri:

```text
V 4/4 items=[]
VE 4/4 items=[]
duplicate flood
sürekli maxItems'e dayanma
formal valid ama localization tamamen 0
```

Post-hoc accuracy threshold uydurma yok.

Amaç yalnız semantic reader'ın gerçekten bilgi üretmesi.

---

# 10. Full pytest milestone

001C sırasında:

```text
semantic_candidates.py
semantic_candidate_reader.py
semantic_run_contract.py
llama.py
budget/lifecycle
tests
```

değişti.

Son full pytest bu değişikliklerden önce.

Shared envelope finalize olunca:

```bash
.venv/bin/python -m pytest -q
```

çalıştır.

Şart:

```text
0 fail
```

Test sayısı 1188 olmak zorunda değil.

---

# 11. Fast test katmanı

Full suite yaklaşık 70 dakika.

Geliştirme için küçük gruplar:

```text
semantic-contract-fast
semantic-integration
slow-reproducibility
full
```

yararlı.

Hedef:

```text
fast semantic feedback < 2–3 min
```

Ama test refactor finali geciktirmemeli.

---

# 12. P7 — yeni bağımsız holdout

Repo içindeki mevcut examples artık görülmüş veridir.

Yeni final unseen holdout için dışarıdan yeni çizimler gerekli.

Tercih:

```text
12–20 yeni teknik çizim
```

al.

Bunlardan 10 final page model çalıştırılmadan önce seçilir.

---

# 13. Holdout eligibility

```text
repo tarihinde yok
001B/001C sırasında görülmemiş
duplicate export değil
engineering drawing
SEMREAD scope callout içeriyor
```

Her source:

```text
source_sha256
group_id
```

ile kaydedilir.

---

# 14. Holdout selection

Mümkünse:

```text
10 page
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
crowded leader
multi-view
low-res raster
clean vector text
```

Model çıktısına göre page seçmek yasak.

---

# 15. Source diversity

Mümkünse:

```text
max 2 page per source/book/style family
```

Yeterli veri yoksa sapma açıkça raporlanır.

---

# 16. Holdout gold

001B gold altyapısı reuse:

```text
tracked spec
vision_checked
source evidence
target reason
target_box_norm / observation
independent corroboration
cycle detection
stable identity
atomic regeneration
```

Gold, V/VE output görülmeden hazırlanır.

---

# 17. Human review

Kritik subset mümkünse ikinci gözden geçer:

```text
THRU
depth
rotated R/Ø
leader crossing
multi-view ownership
```

Review metadata kaydedilir.

---

# 18. D baseline

Yeni holdout için D:

```text
V/VE finalden önce
```

çalıştırılır ve dondurulur.

D sonucuna bakıp page selection değiştirilmez.

---

# 19. Freeze preflight

Freeze öncesi:

```text
shared settings verified
8/8 dev shared-envelope valid
dev semantic sanity report
full pytest 0 fail
10 final pages selected
10 gold complete
D baseline complete
V/VE final calls = 0
orphan = 0
raw V/VE image invariant
leak audit
model exact
digest exact
runtime exact
```

---

# 20. Freeze causal invariant

FREEZE.json ortak V/VE ayarlarını bağlamalı:

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
task
candidate schema
maxItems
```

Arm difference whitelist:

```text
V:
  raw page

VE:
  same raw page
  overlay
  observation table
```

---

# 21. Context preflight

Final holdout'ta model çağırmadan:

```text
prompt serialize
token/byte measure
```

yap.

Eğer:

```text
prompt + max output > num_ctx
```

freeze blocked.

Holdout'ta canlı call ile envelope öğrenmek yok.

---

# 22. Final budget

```text
20 calls
10 V
10 VE
retry = 0
```

Transport failure final sonucun parçasıdır.

---

# 23. Final execution

Request öncesi:

```text
budget reserve
input identity
producer identity
request manifest
```

persist.

Disposition:

```text
valid_result
truncated_output
transport_http
transport_timeout
invalid_json
schema_coordinate
schema_no_guess
schema_error
reference_error
failed_gate
```

---

# 24. Final evaluation

Önce:

```text
valid_output_rate
```

Sonra semantic metrics:

```text
localization
representation
physical
form
size
count_printed
termination
depth
target_binding
overclaim
abstention
false_positive
```

Kollar:

```text
D
V
VE
```

---

# 25. VE vs V causal yorum

Yalnız final artifact'larda generation settings exact-equal ise:

```text
VE - V
```

evidence etkisi olarak yorumlanabilir.

Aksi halde:

```text
confounded
```

yazılır.

---

# 26. Latency / cost

Final raporda V/VE ayrı:

```text
median latency
max/p90 latency
prompt tokens
eval tokens
candidate count
```

Semantic gain tek karar kriteri değildir.

---

# 27. Dev 41-candidate analizi

`plate-VE = 41` için:

```text
gold match
false positive
unscorable extra
duplicate/near duplicate
observation-driven noise
```

say.

Bu structural cap kararının gerekçesidir.

---

# 28. V'nin 1-candidate sonuçları

Bazı V hücreleri 1 aday üretti.

Offline semantic eval şu ayrımı yapmalı:

```text
repeat penalty fazla bastırıyor
vs
raw page gerçekten zor
```

---

# 29. Evidence serialization

Mevcut pruning korunur.

Final öncesi yeni ranking/chunking ekleme.

---

# 30. Timeout / queue

```text
MODEL < CASE < RUN
```

korunur.

Aktif request elle öldürülmez.

Ollama server-side üretim devam edip queue yaratabilir.

---

# 31. Final session hygiene

Final öncesi:

```text
aktif request yok
queue boş
gerekirse ollama stop
fresh load
model digest verify
```

Final sırasında ad-hoc restart/retry yok.

---

# 32. CI

Gözlenen HEAD için external CI status yok.

Freeze milestone'da local:

```text
focused semantic tests
full pytest
```

kanıtı zorunlu.

---

# 33. Documentation debt

`semantic_run_contract.py` tarihsel revizyon açıklaması güncel 7 envelope revizyonunu tam yansıtmıyor.

Freeze öncesi current/historical facts ayrılmalı.

Functional blocker değil.

---

# 34. Plan authority

Bu `PLAN.md` aktif plan olacaksa:

```text
docs/PLAN-12.md
```

history olarak korunur.

Eski plan silinmez.

---

# 35. Commit sırası

```text
1. offline dev semantic evaluation
2. shared generation invariant
3. maxItems + duplicate rule
4. dev budget ceiling 32
5. 8-cell shared-envelope requalification
6. semantic sanity + full pytest
7. holdout intake manifest
8. holdout selection freeze
9. canonical gold
10. D baseline + clean clone
11. P8 freeze
12. final 20 V/VE
13. final semantic report
```

---

# 36. YAPMA listesi

```text
arm-specific repeat_penalty ile final freeze
8/8 parse-valid diye semantic quality varsayma
001B frozen'u yeni unseen final sayma
holdout'u model output'una göre seçme
silent duplicate dedupe
truncated JSON repair
pixel auto-normalize
call-call budget increase
final sırasında hyperparameter tuning
failed final attempt delete
retry until good
001B history overwrite
```

---

# 37. ŞİMDİKİ TEK GÖREV

**Canlı model çağrısı yok.**

```text
8 selected valid 001C dev attempt
→ existing dev gold
→ offline D/V/VE semantic evaluation
```

Üret:

```text
dev-semantic-report.json
dev-semantic-report.md
```

---

# 38. İlk görev acceptance

- [ ] 0 inference
- [ ] 4 dev page
- [ ] D/V/VE same evaluator
- [ ] selected valid V/VE attempts
- [ ] no frozen tuning
- [ ] page metrics
- [ ] field metrics
- [ ] candidate count distribution
- [ ] plate-VE 41-candidate analysis
- [ ] V 1-candidate analysis
- [ ] evaluation identity
- [ ] next shared-envelope hypothesis

---

# 39. Shared-envelope acceptance

- [ ] arm-specific repeat penalty removed
- [ ] V/VE settings equality test
- [ ] common repeat_penalty
- [ ] common repeat_last_n
- [ ] common num_ctx
- [ ] common num_predict
- [ ] common temperature
- [ ] common schema
- [ ] common task
- [ ] bounded items
- [ ] duplicate rule
- [ ] no page-specific branch
- [ ] focused tests pass

---

# 40. Requalification acceptance

- [ ] dev ceiling declared before calls
- [ ] exactly 8 calls
- [ ] V 4/4 valid
- [ ] VE 4/4 valid
- [ ] stop 8/8
- [ ] coordinate 8/8
- [ ] refs 8/8
- [ ] leakage 0
- [ ] shared settings 8/8
- [ ] no manual kill
- [ ] bounded candidate count
- [ ] semantic sanity regenerated
- [ ] no more tuning

---

# 41. Holdout acceptance

- [ ] new external files
- [ ] source hashes
- [ ] duplicate/group audit
- [ ] 10 pages selected before inference
- [ ] selection rules
- [ ] diversity
- [ ] semantic coverage
- [ ] gold without V/VE output
- [ ] raster vision checked
- [ ] independent corroboration
- [ ] review subset if available
- [ ] stable gold identity

---

# 42. Freeze acceptance

- [ ] shared causal invariant
- [ ] dev 8/8 requalified
- [ ] dev semantic sanity
- [ ] full pytest 0 fail
- [ ] holdout 10/10
- [ ] D baseline
- [ ] final budget 0/20
- [ ] model/digest/runtime exact
- [ ] prompt static preflight
- [ ] context headroom
- [ ] raw image equality
- [ ] leak clean
- [ ] clean clone
- [ ] atomic FREEZE.json

---

# 43. Final measurement acceptance

- [ ] 20 calls
- [ ] 10 V
- [ ] 10 VE
- [ ] no retry
- [ ] no deleted failure
- [ ] valid-output rate
- [ ] failure taxonomy
- [ ] D/V/VE localization
- [ ] D/V/VE field metrics
- [ ] V vs D
- [ ] VE vs V
- [ ] VE vs D
- [ ] latency/token cost
- [ ] causal invariant verified
- [ ] immutable report

---

# 44. Ürüne dönüş

001C final raporu:

```text
valid-output reliability
field-level semantic quality
causal evidence contribution
```

verdiğinde benchmark genişletmeyi durdur.

Sonra:

```text
semantic claim graph
→ constraints
→ multi-view feature identity
→ typed CAD planning
→ deterministic CAD
→ STEP
→ feature-level audit
→ user correction
```

ürün hattına dön.

---

# 45. Son karar

Repo yönü genel olarak doğru.

001C dev fazında gerçek ilerleme var:

```text
8/8 valid output
```

Ama bu henüz:

```text
final experiment ready
```

demek değil.

Finalden önce:

```text
semantic sanity
+
V/VE shared generation settings
```

kapanmalı.

## Bir sonraki tek somut iş

```text
OFFLINE DEV SEMANTIC EVALUATION
```

**0 model çağrısı.**
