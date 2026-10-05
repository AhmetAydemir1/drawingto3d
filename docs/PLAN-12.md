# PLAN.md — drawingto3d
## SEMREAD-001B sonrası: output contract'ı düzelt → SEMREAD-001C ile gerçek semantic karşılaştırma → sonra ürüne dön

**Tarih:** 2026-10-05  
**Repo:** `AhmetAydemir1/drawingto3d`  
**Gözlenen `main` HEAD:** `cb4312c7a9833429a814002193a1b1b550521553`  
**SEMREAD-001B final inference HEAD:** `77e735281aae46b2e03c5e48491ccf5fd16b3a93`  
**001B freeze:** tamamlandı  
**001B canonical gold:** 10/10  
**001B clean-clone:** geçti  
**Son full pytest kanıtı:** 1188 passed, 0 fail, 1:10:16  
**Son SEMREAD kanıtı:** 179 passed  
**001B final V/VE inference:** 20/20 çağrı kullanıldı  
**001B sonucu:** D ölçüldü; V/VE semantic doğruluk karşılaştırması yapılamadı çünkü 20/20 V/VE hücresi geçerli aday üretmeden failure ile kapandı.

---

# 0. Yönetici özeti

SEMREAD-001B artık "hazırlık" aşamasında değildir.

Şu işler kapanmıştır:

```text
10/10 canonical gold
→ tüm reference'ların doğrulanması
→ full pytest
→ D reuse
→ acceptance snapshot
→ clean-clone reproducibility
→ FREEZE.json
→ P5 atomic freeze
→ V/VE preflight
→ 20 final V/VE çağrısı
→ immutable final report
```

001B'nin final sonucu önemlidir fakat şu değildir:

```text
"VLM semantic reader kötü"
```

Gerçek sonuç:

```text
V/VE output contract + generation envelope geçerli semantic aday üretmeye yetmedi.
```

Final 20 hücre:

```text
V:
  7 coordinate-contract failure
  3 truncated JSON

VE:
  8 truncated JSON
  1 no-guess/depth schema violation
  1 HTTP transport failure
```

Dolayısıyla:

```text
V valid semantic result = 0
VE valid semantic result = 0
```

ve gerçek araştırma sorusu:

```text
D vs V vs VE hangisi semantic olarak daha iyi?
```

henüz cevaplanmadı.

Bundan sonraki iş:

```text
001B sonucunu değiştirmeye çalışma
→ 001B'yi immutable tut
→ output contract v2 geliştir
→ eski 001B development sayfalarında contract'ı doğrula
→ yeni bağımsız holdout oluştur
→ SEMREAD-001C freeze
→ V/VE'yi tekrar ölç
→ semantic farkı ancak o zaman değerlendir
```

---

# 1. 001B raporundan kesin olarak bildiklerimiz

## 1.1 Deney altyapısı çalıştı

001B başarısız bir deney değildir.

Aşağıdakiler başarıyla çalıştı:

```text
budget ledger
attempt lifecycle
producer identity
evaluation identity
raw-page invariants
V/VE evidence isolation
leak audit
gold reproducibility
clean clone
freeze
failed-attempt preservation
immutable report
```

Bu altyapıyı çöpe atma.

Yeni sürüm bunun üzerinde kurulmalı.

---

# 2. Final matris sonucu

Final disposition:

```text
D  = 10 valid_reuse
V  = 10 failed_attempt
VE = 10 failed_attempt
```

Açık hücre:

```text
0
```

Bu yüzden:

```text
B05 = closed
```

Ama V/VE puanlanabilir semantic prediction üretmediği için:

```text
B06 = open
```

Bu doğru davranıştır.

B06'yı "kapatmak için" aynı frozen sonuçları üzerinde evaluator gevşetmek kesinlikle yasaktır.

---

# 3. D baseline'ın gerçek durumu

D kolu:

```text
126 candidate
6 matched
localization_match_rate ≈ 0.0923
semantic_field_accuracy = 0.5
target_binding_accuracy = 1.0
overclaim = 0.0
abstention ≈ 0.375
```

Sayfa bazında matched claim:

```text
dev-plate-pocket      2/2
dev-flange-book       0/7
dev-flange-elbow      0/7
dev-drawing-2         0/6
frozen-exercise-51    0/10
frozen-exercise-12    4/14
frozen-exercise-17    0/3
frozen-exercise-13    0/7
frozen-enclosure      0/1
frozen-views-exercise 0/8
```

Bu baseline güçlü değildir.

Ama D'yi şu anda optimize etmeye başlama.

Önce V ve VE'nin **geçerli çıktı üretebildiği** bir deney kur.

Aksi halde:

```text
D'nin zayıflığını
V/VE output bug'ıyla
karşılaştırmış oluruz.
```

---

# 4. V kolunun ana problemi: coordinate contract

001B finalde V'nin 10 hücresinin:

```text
7 tanesi
```

normalize region yerine pixel coordinate üretti.

Örnek failure:

```text
x0=65
x1=489
```

ama runtime/Pydantic contract:

```text
0 <= coordinate <= 1
```

bekliyor.

## 4.1 Repo audit bulgusu

`Region` Pydantic modeli 0..1 doğruluyor.

Ama modele verilen manual JSON schema içindeki region alanı yalnız:

```json
{"type": "number"}
```

diyor.

Şunlar yok:

```text
minimum = 0
maximum = 1
```

V'nin ortak task prompt'unda da:

```text
source.region ve target.region normalized 0..1 olmalı
```

ifadesi açık değil.

VE ise observation table başlığında:

```text
region(x0,y0,x1,y1 normalized)
```

gördüğü için aynı pixel-coordinate failure'ını göstermedi.

Bu bir semantic model hatasından önce:

```text
interface specification bug
```

olarak ele alınmalı.

---

# 5. VE kolunun ana problemi: output budget

VE finalde:

```text
8/10 truncated JSON
```

üretti.

Frozen:

```text
num_predict = 2048
```

idi.

Rapor:

```text
done_reason = length
```

ile kesilmeyi gösteriyor.

001B final genelinde:

```text
11 / 20 V/VE hücresi
```

2048 output sınırına dayandı:

```text
V  = 3
VE = 8
```

Bu, VE evidence'ının semantic faydasından önce:

```text
evidence → daha uzun response → output ceiling
```

problemini yarattığını gösteriyor.

VE'nin daha kötü görünmesi şu anda:

```text
semantic evidence harmful
```

kanıtı değildir.

Şimdilik yalnız:

```text
bu output envelope altında evidence-induced truncation
```

kanıtıdır.

---

# 6. Üçüncü problem: failure taxonomy parse_error altında fazla birleşiyor

Mevcut reader:

```text
done_reason = length
```

olsa bile önce raw body'yi `parse_candidate_json()` ile ayrıştırmaya çalışıyor.

Dolayısıyla:

```text
truncated output
```

çoğu yerde:

```text
parse_error
```

olarak yüzeye çıkıyor.

Final forensic inceleme bunu ayırabildi ama normal evaluator raporu katmanı yeterince açıklayıcı değil.

Yeni contract'ta failure layer açık olmalı.

Önerilen sınıflar:

```text
transport_http
transport_timeout
transport_unreachable
empty_content
truncated_output
invalid_json
schema_coordinate
schema_no_guess
schema_enum
schema_unknown_key
reference_error
coverage_error
valid_result
```

`parse_error` üst kategori olabilir ama tek tanı olmamalı.

---

# 7. Dördüncü problem: VE evidence table gereksiz yük taşıyor olabilir

Mevcut `observation_table()`:

```text
tüm primitive'leri
```

row olarak ekliyor.

Primitive'in:

```text
region = None
text = None
value = None
```

olduğu durumda dahi satır bulunabiliyor.

Bu satır semantic reader'a pratik bilgi vermeden prompt'u büyütür.

Yeni sürümde ilk güvenli optimizasyon:

```text
spatial/textual evidence taşımayan row'u modele gönderme
```

olmalı.

Örnek neutral filter:

```text
keep if:
  region is not None
  OR text is not None
  OR value is not None
```

Bu gold kullanmaz.

Page-specific değildir.

Deterministic semantic meaning kullanmaz.

Dolayısıyla deney açısından güvenlidir.

---

# 8. Beşinci problem: model gereksiz default alanları yazıyor

`Candidate` Pydantic modelinde birçok alan default taşıyor.

Model output'unda bu alanların hepsinin tekrar tekrar yazılması zorunlu değil.

Örneğin unknown alanlar:

```text
physical
termination
depth
uncertainty
provenance
representation
```

bazı adaylarda hiç gönderilmeden deterministic default'la doldurulabilir.

Yeni prompt açıkça söylemeli:

> Do not emit optional fields whose value would only be the schema default/unknown. Omit them.

Parser:

```text
missing optional field
→ existing deterministic default
```

yolunu zaten desteklemeli.

Bu davranış unit testle bağlanmalı.

Ama modelden bilinen semantic alan silinmemeli.

---

# 9. Altıncı problem: no-guess violation

`frozen-exercise-51 / VE`:

```text
yazılı olmayan depth
```

üretti.

Bu iyi bir negatif testtir.

Validator doğru şekilde reddetti.

Validator'ı gevşetme.

Yeni prompt'ta kural daha kısa ve daha mekanik yazılmalı:

```text
Depth is allowed ONLY when an explicit printed depth value/symbol is visible.
Geometry size, pixel distance, section thickness or observation measurements are NOT depth evidence.
```

Ayrıca schema description:

```text
depth.state=known only for explicitly printed depth
```

demeli.

Bu değişiklik generic olmalı.

Ex51 adı prompt'a/test production path'ına girmemeli.

---

# 10. HTTP failure

Bir VE hücresi:

```text
dev-drawing-2 / VE
```

HTTP transport failure yaşadı.

Bu tek örnekten:

```text
retry gerekli
```

veya:

```text
model stabil değil
```

sonucu çıkarma.

Önce yeni dev sürümünde:

```text
HTTP status
provider detail
request size
image bytes
prompt bytes
prompt_eval_count
num_ctx
num_predict
memory/runtime state
```

kayıtları yüzeye çıkar.

Final bilimsel run'da otomatik retry ancak **önceden yazılı politika** varsa kullanılmalı.

Öneri:

```text
001C final first-shot reliability:
retry = 0
```

Ürün runtime retry politikası daha sonra ayrı ölçülsün.

---

# 11. 001B'ye bundan sonra dokunma

001B:

```text
CLOSED AS RECORDED
```

kabul edilmeli.

Şunları değiştirme:

```text
001B FREEZE.json
001B final report
001B selected attempts
001B failed attempts
001B budget ledger
001B evaluator identity
001B match policy
001B gold
```

Hata düzeltmeleri:

```text
yeni contract/version
```

altında yapılmalı.

Eski rapor kötü görünse bile overwrite yok.

---

# 12. Yeni deney adı: SEMREAD-001C

Önerilen yeni sürüm:

```text
SEMREAD-001C
```

Neden 001B-R2 değil?

Çünkü:

```text
001B frozen sonuçları görüldü
→ prompt/output değişikliği doğrudan bu failures'a göre yapılacak
→ aynı frozen set artık unbiased final holdout değildir
```

Dolayısıyla 001B corpus:

```text
development + regression
```

olabilir.

Yeni final iddia için:

```text
new independent holdout
```

gerekir.

---

# 13. 001C version bump

Değişiklikler output'u etkilediği için en az:

```text
CANDIDATE_SCHEMA_VERSION
CANDIDATE_READER_VERSION
CONTRACT_VERSION
producer_identity
preprocessing/prompt identity
```

değişmeli.

Örnek:

```text
semread-candidates/2
semread-candidate-reader/2
semread-001c-run-contract/1
```

Evaluator semantics değişmiyorsa:

```text
semread-001b-match/2
```

yeniden kullanılabilir.

Ama yeni experiment kimliği:

```text
001C
```

olmalı.

---

# 14. P0 — 001B immutable snapshot doğrulaması

İlk iş code değiştirmek değil.

Önce:

```text
HEAD
001B final report hash
001B FREEZE.json hash
gold identity
evaluation identity
selected attempts
budget ledger
```

bir "001B closure manifest" içine kaydet.

Ama mevcut dosyaları yeniden yazma.

Acceptance:

```text
001B historical artifacts verifiably unchanged
```

---

# 15. P1 — Region contract v2

## 15.1 JSON schema

Region property:

```json
{
  "type": "number",
  "minimum": 0.0,
  "maximum": 1.0
}
```

olmalı.

Description:

```text
Normalized page coordinates in [0,1].
(0,0)=top-left, (1,1)=bottom-right.
Never use pixel coordinates.
```

hem:

```text
source.region
source.callout_region
target.region
```

için aynı contract'tan gelmeli.

Kopya literal oluşturma.

## 15.2 Prompt

Common V/VE task'a açıkça ekle:

```text
All regions use normalized page coordinates:
x0,y0,x1,y1 in [0,1].
Top-left is (0,0), bottom-right is (1,1).
Never return pixel coordinates.
Example only for coordinate format:
{"x0":0.10,"y0":0.20,"x1":0.30,"y1":0.40}
```

Örnek semantic answer içermemeli.

Yalnız coordinate convention göstermeli.

## 15.3 Unit tests

Yeni testler:

```text
schema minimum/maximum exists
V prompt explicitly says normalized
VE prompt uses same common instruction
pixel example rejected by schema/Pydantic
normalized example accepted
prompt contains no gold/page-specific value
```

---

# 16. P2 — Compact output contract

Amaç:

```text
model output token sayısını azalt
```

semantic bilgi kaybetmeden.

## 16.1 Optional-default omission

Prompt:

```text
Omit optional fields that would only contain default unknown/not_stated values.
```

Test:

```text
minimal candidate body
→ parse
→ omitted fields get deterministic defaults
```

## 16.2 Harness-owned provenance

Araştır:

```text
provenance.kind
provenance.method
```

modelden gerçekten istenmeli mi?

Bunlar harness tarafından zaten biliniyorsa:

```text
model output contract'tan çıkar
→ parse sonrası deterministic inject
```

tercih edilir.

Modelin kendi model adını tekrar yazması bilgi üretmez.

Bu değişiklik candidate schema v2 gerektirir.

## 16.3 Constant image identity

`source.image_id` modelden tekrar isteniyor.

Tek page source id:

```text
image-1
```

harness tarafından zaten biliniyorsa v2'de:

```text
wire response'tan kaldırıp deterministic inject
```

seçeneğini değerlendir.

Ancak VE overlay atfı gerçekten gerekiyorsa:

```text
evidence_image_id
```

ayrı düşün.

Bu optimizasyonu ancak unit/integration testleri basitleştiriyorsa yap.

P1/P2'yi gereksiz mimari rewrite'a dönüştürme.

---

# 17. P3 — VE evidence compression

İlk güvenli kural:

```text
no region + no text + no value
→ do not serialize observation row
```

Kaynak Observations değişmez.

Yalnız VLM evidence serialization küçülür.

Record:

```text
raw observation count
sent observation count
dropped empty-evidence count
prompt bytes
```

## Acceptance

Her development page için:

```text
deterministic filter
stable ordering
stable hash
no gold dependency
```

---

# 18. P4 — Truncation first-class failure

`read_page()` sırası değişmeli.

Mevcut:

```text
answer
→ determine done_reason
→ parse anyway
```

Yeni:

```text
answer
→ inspect done_reason
→ if length:
     failure_kind = truncated_output
     preserve raw
     DO NOT call semantic parser as if complete
→ else parse
```

`done_reason=stop` + metadata complete:

```text
parse eligible
```

Unknown metadata:

```text
fail closed / diagnostic state
```

olmalı.

## Tests

```text
valid JSON + done_reason=length -> truncated_output
broken JSON + stop -> invalid_json
out-of-range normalized field -> schema_coordinate
no-guess violation -> schema_no_guess
```

---

# 19. P5 — Generation envelope ölçümü

`num_predict` değerini körlemesine 4096 yapma.

Önce development ölç.

## 19.1 Ölçülecekler

Her call:

```text
prompt bytes
prompt_eval_count
eval_count
num_ctx
num_predict
done_reason
response bytes
latency
image bytes
observation rows
```

## 19.2 Candidate settings

Başlangıç:

```text
num_predict = 3072 veya 4096
```

ama acceptance yalnız sayıya göre değil:

```text
done_reason == stop
```

ile.

Context headroom:

```text
prompt + output sınırda olmamalı
```

Hedef:

```text
max successful eval_count <= 0.8 * num_predict
```

mümkünse.

## 19.3 num_ctx

8192 yetersizse:

```text
12288 / 16384
```

dev'de ölç.

M1/16GB hedefinde:

```text
latency
memory stability
HTTP failures
```

birlikte değerlendirilir.

En büyük context'i otomatik seçme.

En küçük güvenilir envelope'u seç.

---

# 20. P6 — Dev inference bütçesi

001C için yeni budget ledger.

Öneri:

```text
development max = 10
final max       = 20
total max       = 30
```

Eski 001B ledger resetlenmez.

Yeni dizin:

```text
out/lab/semread-001c/
```

## Dev sequence

İlk iki temsilci sayfa:

```text
dev-plate-pocket
dev-flange-book
```

V + VE:

```text
4 calls
```

Gate geçerse diğer iki 001B dev page:

```text
dev-flange-elbow
dev-drawing-2
```

V + VE:

```text
+4 calls = 8
```

Kalan 2 dev call:

```text
yalnız blocker diagnosis
```

için reserve.

---

# 21. Dev acceptance gate

Final holdout oluşturmadan önce tüm 8 development cells:

```text
valid_result
```

olmalı.

Minimum:

```text
V 4/4 parse-valid
VE 4/4 parse-valid
done_reason=stop 8/8
coordinate contract valid 8/8
reference checks valid
no leakage
no page-specific code
```

Semantic accuracy'nın yüksek olması bu gate'in şartı değildir.

Önce:

```text
transport + output contract works
```

kanıtlanmalı.

---

# 22. Contract testlerinde frozen sonuç kullanımı

001B frozen pages artık görülmüş durumdadır.

Bunlar:

```text
regression
diagnostic
manual inspection
```

için kullanılabilir.

Ama:

```text
"unseen final holdout"
```

diye raporlanamaz.

Özellikle:

```text
ex51 no-depth failure
V pixel failure
VE truncation failure
```

yeni testlerin gerekçesi olabilir.

Fakat test fixture:

```text
page_id special-case
```

olmamalı.

---

# 23. P7 — Yeni 001C holdout

Final semantic karşılaştırma için yeni unseen corpus seç.

Minimum 10 sayfa önerisi:

```text
4 vector/PDF
6 raster
```

Her biri farklı parça grubu.

İçerik çeşitliliği:

```text
Ø
R
count prefix
THRU
finite depth
unknown termination
multi-view
rotated dimension
crowded leaders
low-resolution raster
clean vector text
```

Aynı kaynak kitabın komşu exercise'larını aşırı kullanma.

Mümkünse farklı kaynaklar.

---

# 24. 001C gold politikası

001B'den öğrenilen validasyon altyapısını reuse et:

```text
tracked spec
vision_checked
source evidence
target reason
independent corroboration
cycle detection
stable identity
atomic freeze
```

Ama yeni gold:

```text
001B resultlerine göre seçilmemeli
```

Örneğin sırf modelin iyi okuyacağı sayfaları toplamak yasak.

---

# 25. Human review iyileştirmesi

001B gold:

```text
annotator=agent
review_status=provisional
```

idi.

001C'de mümkünse:

```text
en az final holdout claim'lerinin kritik bir alt kümesi
```

insan tarafından ikinci kez kontrol edilmeli.

Örnek:

```text
all depth/THRU claims
all rotated R/Ø
all ambiguous leader bindings
```

Review metadata:

```text
reviewer
review status
disagreement
resolution
```

taşımalı.

Bu ürün accuracy certification değildir ama gold riskini azaltır.

---

# 26. P8 — 001C freeze

Freeze öncesi:

```text
dev contract fixed
new holdout gold complete
D baseline captured
V/VE to_run
budget final 0/20
orphan 0
raw image invariant
leak audit
model/digest/runtime exact
generation envelope proven on dev
```

Freeze bağlaması:

```text
schema v2
reader v2
run-contract v1
prompt hash
schema hash
model/digest
runtime
num_ctx
num_predict
evidence serialization identity
preprocessing identity
gold identity
match policy
```

---

# 27. P9 — 001C final run

Final:

```text
10 pages × V/VE = 20 calls
```

Retry:

```text
none
```

first-shot experiment olarak.

Her cell:

```text
valid_result
truncated_output
transport_*
schema_*
reference_error
```

gibi açık disposition almalı.

Generic:

```text
parse_error
```

tek başına final tanı olmamalı.

---

# 28. P10 — Gerçek semantic evaluation

Bu kez V/VE valid result üretiyorsa:

```text
D vs V
V vs VE
VE vs D
```

alan bazında ölç.

Öncelikli metrics:

```text
localization
form R/Ø
size
count_printed
termination
depth
target_binding
physical
overclaim
abstention
```

Tek aggregate accuracy karar mekanizması olmasın.

---

# 29. Karar ağacı

## V belirgin şekilde D'den iyiyse

Raw local VLM semantic reader ürün yolu için güçlü aday.

## VE, V'den anlamlı iyi ise

Deterministic observations semantic VLM'ye yardımcı oluyor.

Mimari:

```text
deterministic observe
→ evidence
→ local VLM semantic resolver
→ deterministic validator
```

## VE yine daha kötü ama valid ise

Evidence kalite/kalabalık sorununu analiz et.

```text
observation precision
overlay clutter
table size
wrong anchors
```

## D bazı alanlarda en iyiyse

Hibrit merge policy sonraki deney konusu olur.

001C içinde post-hoc merge yapma.

---

# 30. D baseline geliştirmesi ne zaman?

001C semantic karşılaştırma tamamlanmadan:

```text
D production reader tuning
```

yapma.

Sonra D'nin açık problemleri:

```text
localization 9.23%
physical abstention
termination/depth abstention
many unscorable extras
false positives
```

alan bazında ele alınır.

---

# 31. Test suite performansı

Repo health iyi ama test feedback çok yavaş.

Kayıt:

```text
full pytest ≈ 70 dakika
SEMREAD 179 ≈ 51 dakika
```

Bu geliştirici döngüsünü yavaşlatıyor.

Ama contract fix'ten önce büyük test altyapı rewrite yapma.

## Sonraki küçük iyileştirme

Tests:

```text
unit-fast
integration
slow-reproducibility
```

olarak marker'lanabilir.

Hedef:

```text
fast semantic unit suite < 2-3 min
```

Milestone:

```text
full suite
```

korunur.

CI varsa:

```text
PR: fast
nightly/milestone: full
```

---

# 32. Hangi testler her değişiklikte koşulmalı?

P1–P4:

```text
test_semantic_candidates
candidate reader unit tests
identity tests
lifecycle tests
run-contract tests
```

Inference yok.

P5–P6:

```text
aynı unit set
+
1-2 dev live calls
```

P8 freeze:

```text
SEMREAD full
full pytest
clean-clone
```

Final run sırasında code değiştirme.

---

# 33. Ürün hedefini unutma

SEMREAD yalnız semantic-reading laboratuvarıdır.

Ürün hedefi hâlâ:

```text
drawing
→ semantic claims
→ constraints
→ solved geometry
→ typed CAD plan
→ deterministic CAD
→ STEP
→ feature verification
→ user correction
```

001C sonunda semantic direction seçildiğinde benchmark expansion'ı bırakıp ürün hattına dön.

---

# 34. Constraint katmanına dönüş şartı

Aşağıdakiler sağlanınca semantic research yeterli kabul edilebilir:

```text
valid-output rate high
localization measured
field-level semantic metrics available
major failure classes known
abstention works
```

Mükemmel accuracy bekleme.

Sonra:

```text
semantic claim -> typed constraint
```

entegrasyonuna geç.

---

# 35. Kullanıcı düzeltme döngüsü

Ürün semantic reader:

```text
callout text
target
meaning
confidence
uncertainty
```

göstermeli.

Belirsiz hedef:

```text
guess
```

yerine soru üretmeli.

Örnek:

```text
"Ø10 hangi daireye ait?"
```

Kullanıcı kararı revision identity'ye girmeli.

---

# 36. CAD planner konusu

Şu anda planner rewrite yapma.

Semantic output güvenilir olduktan sonra:

```text
claim graph
→ constraints
→ typed operation grammar
```

üzerinden ilerle.

Local LLM planner varsa:

```text
proposal
```

üretsin.

Compiler contract ve validator deterministic kalsın.

---

# 37. STEP doğrulama

Valid solid:

```text
başarı değildir
```

Gelecekte:

```text
feature count
diameter
position
depth
pocket
profile
pattern
```

yeniden açılmış STEP üzerinde doğrulanmalı.

Reference STEP yalnız evaluator.

---

# 38. Yasaklar

Yeni agent şunları yapmamalı:

```text
001B report overwrite
001B budget reset
001B failed attempts delete
001B frozen pages'i yeni holdout diye sunma
pixel output'u parser içinde sessiz normalize etme
truncated JSON'u repair edip valid sayma
no-guess validator'ı gevşetme
page-specific prompt
page-specific coordinate transform
ex51-specific depth hack
final sonuç görülünce threshold değiştirme
```

Özellikle:

```text
pixel coordinates / width-height yapıp kabul et
```

production parser repair'i olarak eklenmemeli.

Model contract doğru öğretilmeli.

---

# 39. Neden parser auto-repair yok?

V'nin pixel coordinate'ları kolayca normalize edilebilir gibi görünüyor.

Ama bunu parser'da otomatik yapmak:

```text
model contract violation
```

ile:

```text
correct model response
```

arasındaki farkı gizler.

Ayrıca modelin hangi image resolution'ına göre pixel yazdığı belirsiz olabilir:

```text
source image
prepared 1280 image
overlay
```

Bu nedenle v2:

```text
prompt/schema doğru
parser strict
```

kalmalı.

---

# 40. Evidence table için güvenli optimizasyon sırası

Sıra:

```text
1. empty rows drop
2. optional response fields omit
3. prompt wording shorten
4. measure
5. only then num_predict increase
6. only if still needed more complex chunking
```

İlk çözüm olarak:

```text
quadrant chunking
multi-call pagination
observation ranking
```

yapma.

Bunlar deney tasarımını fazla değiştirir.

---

# 41. Eğer 4096 yine yetmezse

Önce output neden uzun bak.

Eğer:

```text
candidate count gerçekten yüksek
```

ise iki seçenek:

### A. Compact wire schema

Model yalnız:

```text
id
callout
form
size
count
termination
depth
target region
source region
```

gönderir.

Defaults/provenance harness tarafından eklenir.

### B. Deterministic pagination

Her iki arm için aynı sayfa bölme politikasını kullan.

Ama bu:

```text
SEMREAD-001D
```

gibi ayrı tasarım değişikliği sayılabilir.

001C'de mümkünse tek-call koru.

---

# 42. HTTP gözlemleme

`llama.py` zaten:

```text
http_status
transport_seconds
request hash
response bytes
done_reason
```

kayıtlayabiliyor.

Yeni report writer bu kanıtı özetlemeli.

Ama 001B evaluator/report'u geriye dönük değiştirme.

001C report formatında ekle:

```text
transport failures by status
truncation count
schema failure subtype
```

---

# 43. 001C report acceptance

Final report şu soruların hepsini cevaplamalı:

```text
kaç inference?
kaç valid result?
kaç transport fail?
kaç truncation?
kaç schema fail?
D/V/VE semantic metrics?
V vs D net gain?
VE vs V net gain?
evidence latency cost?
```

Bu kez:

```text
valid-output-rate
```

birinci sınıf metric olsun.

---

# 44. Başarı kriterleri

## Contract success

```text
dev V valid_result = 4/4
dev VE valid_result = 4/4
truncation = 0/8
pixel coordinate violation = 0/8
```

## Final experiment success

Başarı:

```text
V/VE'nin D'yi yenmesi
```

değil.

Başarı:

```text
semantic comparison yapılabilecek kadar valid V/VE prediction
```

üretmek.

İdeal final:

```text
valid output >= 90%
```

Hedef olabilir.

Ama failures dürüstçe sayılır.

---

# 45. Commit planı

Önerilen küçük commits:

```text
1. semread-001b: immutable closure manifest
2. semread-001c: candidate region contract v2
3. semread-001c: compact optional output + tests
4. semread-001c: evidence table empty-row pruning
5. semread-001c: truncation first-class failure
6. semread-001c: run-contract/generation envelope v1
7. semread-001c: dev smoke V/VE
8. semread-001c: dev 4-page validation
9. semread-001c: new holdout corpus + gold
10. semread-001c: clean-clone + freeze
11. semread-001c: final V/VE
12. semread-001c: final evaluation
```

---

# 46. Her committe kanıt

Commit message / handoff:

```text
what changed
why
test command
pass/fail
live inference count
budget
producer identity
contract version
next gate
```

Live call varsa:

```text
done_reason
eval_count
num_predict
prompt_eval_count
latency
```

da yaz.

---

# 47. Handoff formatı

Her agent turu:

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

001B ile 001C verilerini aynı klasörde/ledger'da karıştırma.

---

# 48. Bir sonraki tek somut iş

**Inference çağırma.**

İlk code işi:

```text
SEMREAD-001C output contract v2
```

ve yalnız şu üç değişiklik:

```text
1. region JSON schema minimum/maximum 0..1
2. common V/VE prompt'ta explicit normalized coordinate rule
3. tests proving V and VE see the same coordinate convention
```

Sonra unit tests.

Bu commit kapanmadan:

```text
num_predict
evidence pruning
live call
```

işine geçme.

---

# 49. P1 acceptance checklist

- [x] `semread-candidates/2`
- [x] region min=0 max=1 schema
- [x] explicit normalized coordinate instruction
- [x] top-left/bottom-right convention
- [x] generic normalized example
- [x] no pixel example
- [x] V prompt test
- [x] VE common prompt test
- [x] out-of-range negative test
- [x] no gold/page-specific text
- [x] zero inference

---

# 50. P2/P3 acceptance checklist

- [x] optional unknown fields may be omitted
- [x] defaults deterministic
- [x] provenance ownership decided
- [x] empty observation rows pruned
- [x] row ordering deterministic
- [x] evidence serialization identity stable
- [x] prompt byte count recorded
- [x] zero inference

---

# 51. P4/P5 acceptance checklist

- [x] truncation is separate failure kind
- [x] done_reason length never semantic-valid
- [x] transport subtype preserved
- [x] schema subtype preserved
- [ ] candidate output headroom measured
- [ ] selected num_predict justified
- [ ] selected num_ctx justified
- [ ] M1/16GB stability observed

---

# 52. Dev live checklist

- [ ] new 001C ledger
- [ ] 001B ledger untouched
- [ ] first 2 pages V/VE = 4 calls
- [ ] all 4 valid
- [ ] then remaining 2 dev pages = +4 calls
- [ ] total 8 valid
- [ ] done_reason stop 8/8
- [ ] no pixel coordinates
- [ ] no truncation
- [ ] no leakage
- [ ] max 2 calls reserved

---

# 53. 001C final checklist

- [ ] independent final corpus
- [ ] no frozen tuning leakage
- [ ] gold complete
- [ ] provisional/human-review status explicit
- [ ] clean clone
- [ ] stable identity
- [ ] freeze
- [ ] D baseline
- [ ] V/VE raw invariant
- [ ] 20 final calls
- [ ] no post-hoc retry
- [ ] failure subtypes
- [ ] valid-output rate
- [ ] field metrics
- [ ] immutable report

---

# 54. Son karar

001B'yi başarısız sayıp çöpe atma.

001B'nin en değerli sonucu:

```text
semantic model kalitesini ölçmeden önce
wire contract ve generation envelope'un
deneyi boğduğunu göstermesi
```

oldu.

Bu aslında doğru bir araştırma sonucu.

Şimdi yapılacak yanlış hamle:

```text
aynı frozen set üzerinde
promptu düzelt
tokenı artır
tekrar koş
ve yeni sonucu unbiased benchmark diye raporla
```

olur.

Doğru hamle:

```text
001B immutable
→ contract v2
→ 001B dev/regression
→ yeni 001C holdout
→ freeze
→ gerçek semantic comparison
```

---

# 55. Ürün yönü

001C'de geçerli semantic comparison alındıktan sonra laboratuvarı daha fazla büyütme.

Kazanan yönü seç:

```text
D
V
VE
veya ölçülmüş hibrit
```

Sonra ana ürüne dön:

```text
semantic claims
→ constraints
→ geometry
→ typed CAD plan
→ deterministic CAD
→ STEP
→ feature validation
→ user correction
```

## Şimdi yapılacak tek iş

```text
SEMREAD-001C region/output contract v2
```

**Canlı model çağrısı yok.**
