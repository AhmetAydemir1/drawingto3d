# G12 ilerleme raporu — PLAN-24-G12-CORRECTNESS

Ana metrik (G11 baseline, değişmez payda): **GUIDED_CORRECT_STEP_RATE = 1/9** (correct: `plate-pocket-vector`).
Sayaçlar (§75/§76): correct 1 · wrong 5 · blocked 3 (üretilmedi) · scope-only 1 (geometri iddiası yok).

| faz | durum | not |
|---|---|---|
| G12.0 truth lock / baseline | **DONE** | pinler + G9 guard PASS + 540 passed + süreç sınırı |
| G12.1a false readiness (backend) | **DONE** | disposition sözleşmesi (şema 4) + `callout_coverage` + `set_disposition` + 631 passed |
| G12.1b coverage UI + runner v2 | **DONE** | üç adı konmuş karar + gerekçe/dayanak akışı + kapsam otoritesi backend'de; gerçek Chrome 10/10; koşucu v2 blanket-ignore'suz |
| G12.2 build strategy contract | **DONE** | örtük extrude kaldırıldı; açık strateji kararı + panel + kategoriler; taze Plate kabulü 10/10 |
| G12.3 view-scoped geometry foundation | bekliyor | view sahipliği + `GEOMETRY_VERSION 3→4` (PLAN-25 §45–§54) |
| G12.4 exact supported 2D constraints | bekliyor | desteklenen kısıtların tam uygulanması (PLAN-25 §55+) |
| G12.5 raster extrude recovery | bekliyor | raster yoldan profil + ölçü kurtarma |
| G12.6 axisymmetric / revolve | bekliyor | `compile_revolve_plan` gerçek geometri |
| G12.7 multi-view composite v1 | bekliyor | görünüş grafiği + özellik bağlama |
| G12.8 advanced bounded operation audit | bekliyor | capability-gap.json |
| G12.9 frozen manifest rerun | bekliyor | 9/9 + 1/1 scope-only |

> Not: PLAN-24'ün kalan faz adları PLAN-25 (kullanıcı girdisi `PLAN-21.md`, §45+) ile yeniden
> sıralandı; yukarıdaki satırlar artık YÜRÜRLÜKTEKİ planın numaralandırmasıdır.

## G12.0 kanıt demeti

- `eval/audits/20261007-g12-baseline/run-01/git-facts.txt` — HEAD `cc36f8de…` beklenen.
- `…/frozen-evidence-sha256.txt` — G9/G11/G11R kanıtı + üç donmuş dosyanın sha256'sı (değişmedi).
- `…/plate-regression-verdict.json` — dondurulmuş evaluator **PASS** (9/9 kontrol; bbox [120.011, 80.002, 15.0]).
- `…/pytest-relevant.log` — ilgili süit **540 passed** (189.20 s).
- `…/pytest-g12-guards.log` — yeni pinler **9 passed**.
- `tests/test_g12_baseline_contract.py` — manifest 10/9/1 + rapor 1/9 + dosya bayt pinleri.
- `tests/test_g12_runner_boundary.py` — üretici beyaz listesi, env/argv/girdi referans denetimi,
  ürün kaynağında vaka/referans sabiti taraması (§83/§84'ün G12.0 sürümü).
- `eval/g12_runner/{producer_input,produce_case,evaluate_case}.py` — §8 süreç ayrımı.

## G12.1a kanıt demeti

- `eval/audits/20261007-g12-decision-coverage/README.md` — kapsam, kasıtlı davranış değişikliği, sınırlar.
- `…/pytest-g12.1a.log` — 276 passed; geniş regresyon 630 passed (callout/guided/plate/g11/g12/view).
- `tests/test_callout_coverage.py` — §17 matrisinin saf katmanı (12 test): claim/blok/dayanak/eski kayıt.
- `tests/test_guided_disposition.py` — komut + kayıt yolu (19 test): `set_disposition`, eski düğmelerin yeni
  anlamı, toplu karar, undo/revizyon, export/import, legacy kilidi.
- Ürün: `callout_models` (şema 4 + disposition alanları), `callout_compile` (adı konmuş dışlama),
  `callout_readiness` (`callout_coverage` + `coverage_issues`), `guided` (`set_disposition` + toplu kurallar),
  `callout_review` (paket + import aksiyonu).

## G12.1b kanıt demeti (UI kapsam sözleşmesi + koşucu v2)

- `eval/audits/20261007-g12-decision-coverage/browser/README.md` — gerçek Chrome kabulü, senaryo A–E;
  `browser-acceptance.log` + `g12-disposition-steps.json` **10/10 PASS** (kararlar gerçek fare/klavye).
- `…/pytest-g12.1b-focused.log` — §28 odak kümesi **78 passed / 6.57 s**; genişletilmiş küme (yeni
  dosyalar dahil) **198 passed / 8.07 s**; ikisi de EXIT=0.
- `…/pytest-broad.log` — §98 geniş regresyon `pytest -q tests -k "not semread"`: **1527 passed · 0 failed ·
  339 deselected · 1504.78 s (25:04) · EXIT=0** (07.10.2026 18:34→18:59; §5: tek yetkili sayı).
- `tests/test_guided_disposition_ui.py` — §20'nin sekiz davranışı gerçek `guided.js` üzerinde (saplama DOM):
  desteklenmeyen çözülmez/zıplanmaz, `not_model_input` ve geçerli `redundant` çözer, geçersiz dayanak
  ve eski kayıt çözülmez, “Sonraki eksik” bloklara uğrar, özet backend sayılarından, checklist seçer.
- `tests/test_g12_recipe_v2.py` — koşucu v2: şema doğrulaması, blanket alanların reddi (`ignore_rest`,
  `bulk_remaining`, `ignore_all_unhandled`), toplu kararın açık ID listesi şartı, gerekçe/dayanak
  zorunluluğu, referans/STEP yolu yasağı, “kalanları kendiliğinden kapatmama” koşum kanıtı.
- Ürün: `guided.py` (public state `coverage`), `callout_readiness.py` (§18 kategorı kopyası),
  `guided.html`/`guided.js` (üç karar, gerekçe, dayanak, özet; `rowResolved` + liste kovadan),
  `eval/g12_runner/recipe_v2.py`, `eval/g12_runner/g12_runner.py`.
- Tarihsel kanıt değişmedi: G9/G11 klasörleri ve `eval/guided_10_*` dosyalarına dokunulmadı; ana metrik
  paydası hâlâ **1/9** (bu tur karar değil, sözleşme turu).

## G12.2 kanıt demeti (açık üretim biçimi)

- `eval/audits/20261007-g12-strategy-plate/README.md` — taze Plate kabulü **10/10 PASS**:
  callout incelemesi (reçete 9 satır + reçete dışı 36 satır tek tek adıyla) → kapsam kapanır →
  strateji yokken üretim reddedilir → `extrude_profile` onayı (sunucu anahtarı/sürümü sabitler) →
  üretim → STEP reopen → **dondurulmuş evaluator 9/9 PASS**; parça 120 × 80 × 15, 4 delik, 1 cep.
- `src/drawingto3d/build_strategy.py` — öneri + tazeleme + soru cümlesi (saf modül, referanssız).
- `guided.py` — `Decisions.build_strategy`, `set_strategy` komutu, `/save` sahte strateji reddi,
  `make_plan` = ortak bağlam + explicit dispatch (`compile_extrude_plan` / `compile_revolve_plan` /
  `compile_multiview_plan`); **örtük extrude yok**, daire profili açık onayla ekstrüde edilir.
- Readiness kategorileri: `missing_build_strategy`, `stale_build_strategy`, `unsupported_build_strategy`;
  panel + kontrol listesi maddesi (§41/§42).
- Gerçek Chrome (UX değişti, §97/8): `browser/` — hazırlık listesi strateji maddesi, dört seçenek
  (döndürme/çok görünüş seçilemez), karar yokken üretim kapalı, kaydetme gövdesi yalnız
  `{token, revision, kind}`, karar sonrası tıklamayla üretim → **7/7 PASS**.
- Testler: `tests/test_build_strategy.py` (11) · `tests/test_guided_strategy_ui.py` (5) · ilgili süit
  **401 passed (129,80 s)**; geniş `pytest -q tests -k "not semread"` → **1543 passed, 339 deselected,
  1637,22 s (27:17), EXIT=0** — `eval/audits/20261007-g12-strategy-plate/pytest-broad.log`
  (1527 → 1543: +11 build_strategy, +5 strateji UI).

## G12R (bağımsız inceleme düzeltme turu, PLAN-25'ten sonra / G12.3'ten önce)

İnceleme: `eval/audits/20261007-guided-g12-2-independent-review` (HEAD `f8d32f4`); beş bulgu, hepsi
düzeltildi. Kural: önce başarısız regresyon, sonra generic düzeltme.

- **G12R-01** strateji eşitliği artık **değer** bazlı (`model_dump(mode="json")`): tarayıcının
  `10.0 → 10` turu aynı karar sayılır, normal kayıtlar onaydan sonra reddedilmez; değişen tür ya da
  uydurulmuş `strategy_key` yine reddedilir. `tests/test_g12r_review_fixes.py`.
- **G12R-02** kapsam onayı **sunucunun yazdığı pine** bağlı: satırın kendi okuması (transcription
  revizyonu + bölge) ve dayanağın onaylandığı içerik (değer anlık görüntüsü / callout revizyonu).
  Metin, bölge ya da dayanak değişince onay düşer; yeni kategori `stale_scope_claim` («Kapsam
  kararını yeniden ver»). Şema **4 → 5** (`duplicate_pin`); şema-4 onayları pinsiz → yeniden onay
  ister (satırın kararı silinmez, PLAN-24 §11 durur). İçe aktarmada pin istemciden alınmaz.
- **G12R-03** kabul betiği artık "kalan" satırı kapatmaz: reçete dışı satırlar **yazılı** listeden
  (`NON_MODEL_RECIPE`, 24 satır, her biri kendi gerekçesiyle) karara bağlanır; listede olmayan satır
  kabulü **durdurur**. `_reason_for` varsayılanı kaldırıldı; eski betik tarihsel kayıt olarak durur.
- **G12R-04** `produce_case.py` varsayılanı kaynak-only **G12 sürücüsü**; tarihsel G11 koşucusu G12
  üretici yolunda reddedilir (çıkış 4, dosya yazılmaz). Varsayılan gerçek komut sahte uygulamayla
  uçtan uca test edilir (yalnız guided uçları; kayıt yalnız tur dizinine).
- **G12R-05** v2 reçete dolu `profile_actions`/`view_decisions`/`dimension_bindings`/`feature_links`
  alanlarını oturum açılmadan reddeder; `strategy_decision` uçtan uca uygulanır
  (`/api/guided/strategy`, yalnız `kind`); `notes` katı model dosyası adı taşıyamaz.

Kanıt demeti: `eval/audits/20261007-g12r-strategy-plate/` — taze Plate kabulü **11/11 PASS**
(dondurulmuş evaluator **9/9**, parça 120 × 80 × 15 · 4 delik · 1 cep), gerçek Chrome **11/11 PASS**
(R-01: C/D; R-02: C2 değer ayağı, E okuma ayağı, F yeniden onay), ilgili süit **615 passed /
212,84 s / EXIT=0** (incelemenin kendi komutu; 589 → +26) ve geniş regresyon
**1569 passed / 339 deselected / 26:54 / EXIT=0** (`pytest-broad.log`; 1543 → 1569).
Eski G12.2 kanıt dizini ve tarihsel G9/G11 kanıtları değişmedi; ana metrik hâlâ **1/9**.

## G12.3 — view-scoped geometry foundation (PLAN-25 §45–§54) ✓

Ölçülen şey görünüşün kendisidir: adaylar oturumla **bir kez** yazılır (§46), her kontur/daire sahibi
`view_id`'yi taşır (§48; belirsiz sınır → `None`, en yakın komşu tahmini yok), rol kararı kullanıcının ve
sunucunun damgasıyladır (§47), `GEOMETRY_VERSION 3 → 4` (§49) ve hedef/strateji parmak izi hem satır
sahiplerini hem onaylı rolleri içerir (§50) — rol ya da sahiplik değişince eski onay güncelliğini yitirir.
Kapı: `view_scope_conflict` — seçilen kontur onaylı ana görünüşün dışındaysa, izometrik adayın içindeyse
ya da rol damgası eski bir geometri sürümündense üretim **başlamaz** (§52). Sahipsiz kontur çatışma
değildir (ilişki kurulmamıştır, çapraz değildir) — mevcut tek görünüşlü yollar bozulmadan çalışır.

UI (§51/§52): görünüş paneli + rol seçimi (`/api/guided/view`, istemci sürüm uydurmaz), tuval üstünde
aday kutuları ve etiketleri, ana görünüş onaylıyken kontur/daire menülerinin daralması ve "Tüm
geometrileri göster" kaçışı.

Kanıt: `eval/audits/20261008-g12-3-view-scope/` — gerçek Chrome **7/7** (adaylar, roller, menü kapsamı,
yeniden yüklemede kalıcılık + yeniden segment yok), ilgili süit **628 passed / 235,04 s / EXIT=0**,
G12R Plate kabulü v4 altında **11/11**, R-01/R-02 gerçek Chrome yeniden kontrolü nihai kodla **11/11** ve
genüş regresyon **1582 passed / 339 deselected / 27:17 / EXIT=0** (`pytest-broad.log`; 1569 → +13). Bu fazda inşa doğruluğu
iddiası yoktur (§54). Eski kanıt dizinleri, dondurulmuş manifest ve `eval/metrics.py` değişmedi; ana
metrik hâlâ **1/9**. Sıradaki faz: **G12.4 — exact supported 2D constraints** (§55–§60).

## G12.4 — exact supported 2D constraints (PLAN-25 §55–§60) ✓

Basılı ölçü artık koordinatı *belirler*: tek bir küresel ölçek uydurulmaz (§56), her çözülen koordinat
kendi kökenini yapısal taşır (§57: bağ kimliği, basılı değer, birim, geometri hedefleri, denklem türü ve
basılı kaydın kimliği), çözüm durumları ortalamasız raporlanır (§58), yetersiz belirlenmiş taslak yalnız
açık izleme onayıyla üretilir ve **N/M denetimi** yazılır (§59).

Kanıt: `eval/audits/20261008-g12-4-constraints/` — ürün yolundan geçen **5 P4 senaryosu** (60 × 40
dikdörtgen tam; 30/6 mm merkez aralığı tam; Ø6 delik tam; çelişen genişlik adlarıyla reddedilir ve STEP
üretilmez; yetersiz taslakta N=1/M=11 ve izleme onayı olmadan başlamaz), ilgili süit **678 passed / 4:06**,
G12R Plate kabulü **11/11**, geniş regresyon **1590 passed / 339 deselected / 29:31 / EXIT=0**
(`pytest-broad.log`; 1582 → +8). `p4-rectangle.step` (20173 bayt) +
`p4-geometry.json` + `p4-provenance.json` kalıcı kanıt. Eski kanıt dizinleri, dondurulmuş manifest ve
`eval/metrics.py` değişmedi; ana metrik hâlâ **1/9**. Sıradaki faz: **G12.5 — raster extrude recovery**
(§61–§64).

## G12.5 — raster extrude recovery (PLAN-25 §61–§64) — WIP (ara durum)

Ölçüme dayalı iki jenerik kural zincir kapamayı düzeltti (§64; örnek-başına tolerans ayarı YOK):
`RASTER_JOIN_TOLERANCE_PX` 20→40 (gerçek ekler 1,6–37 px) + yeni `CORNER_JOIN_REACH_PX=48`
(köşe/yay kuralları yalnız paylaşılan mürekkep eriminde; kapı gap ve meet mesafesine uygulanır,
kapanış varyantları dahil); `guided._trace` `mid_join_px` zincirin kendi zarfına çekildi — iki
aşama aynı zarfta (28,6 px'te kapanan sentetik teli iz eskiden 20'lik yarı-çapla atıyordu).
Exercise_51 izinde >100 px sahte sıçrama **222→0** (en büyük 1965,7→53,8), ≥48 px adım 318→20,
ölü uç 223→211.

Kanıt: `eval/audits/20261007-g12-raster-profile/` — §61 sınıflandırma (10 vaka, yalnız kaynak;
`cluster-classification.json`), §63 denetim (`contour-audit.json`: 5 raster vaka × en büyük 12
profil, 11 alan), `reference-metrics.log` (referans künyeler + G11 üretim karşılaştırması:
51 → %94, flange → %93 hacim farkı, ikisi de pass False — §65 P5 tabanı), iz + tarama
önce/sonra logları; yeni testler `tests/test_g12_raster_profile.py` **4/4** + `tests/test_advise.py`
**2/2** (RED→GREEN); ilgili süit **741 passed / 19:48 / EXIT=0**; geniş regresyon
**1596 passed / 339 deselected / 28:59 / EXIT=0**. Profiller 16/26/19/24 →
48/64/31/33/44 → (yay düzeltmesi sonrası) 60/77/47/45/65; tüm wire'larda kapalı 50→74, >100 px
ek 17→4.

**Yay-yürüyüş yönü (aynı gün).** İzin "hangi uçtan girildi?" kıstası 90°'lik pencereden **en
yakın uç** karşılaştırmasına çevrildi (§23-C14 sözleşmesi korunur: süpürmenin işaretini giriş
ucu belirler); zincirin `b` ucundan girdiği ≤90°'lik yaylar artık ayna değil gerçek yayı çiziyor
(Exercise_51 g445: hayalet uç [2260,216] menüden düştü, outline_23 join_max 278,77→38,23 px;
vektör tarafta g151'in ~186 px hayalet uzantısı düştü, reading çerçevesi devreye girdi ve
`resolve_claim`'in reading dalı eksen kararını (x/y) da üretir oldu — çapraz satır kapısıyla
(karşı bileşen ≤ span/2; plate akışı 9 öneri) — flange kalınlığı 20,0 korundu; yeni testler
`tests/test_advise.py`).
Kalan: **eklerdeki küçük örtüşme sınıfı** (5 kontur dürüst-kapalı-değil; eski "kapalı" halleri
42–187 px zorlama-taşımayla geliyordu) + **zincir kalitesi** (kendi içinde kesişen konturlar) +
§65 P5 kapısı açık. Manifest/metrics/tarihsel kanıtlar değişmedi; ana metrik hâlâ **1/9**.

**§65 P5 hedef analizi (aynı gün, ek tur).** Beş uygun aday referanslarıyla ölçüldü
(.venv-cad: yüz dökümü + eksen dilimleri + siluet render'ları; kanıt
`eval/audits/20261007-g12-raster-profile/p5-evidence/`, analiz `p5-analysis.md`). Hedef seçildi:
**exercise-13-raster** — taban plakası + tek yükseltilmiş göbek (Ø100/Ø60, her yana 10 taşma;
z ±60) + 5 delik (2 payanda Ø25 z-ekseni, 2 plaka Ø25 y-ekseni); G11'de tamamen bloke (STEP
üretilemedi); §61 gerekçesi zaten bu okuma ("taban konturu + göbek dairesi aynı cephe
görünüşünde"). Gereken üretim op'ları **mevcut** GeneralPlan sözlüğünde (`ExtrudeOp`, `FuseOp`,
`CutOp`; `compile_general` beş op'u da `geo.*` çağrısına çeviriyor). Kalan boşluklar: (a) ön izde
düzeltme sonrası kalan self-intersection sınıfı, (b) daire tespiti — ex13'te 4 daire (2 üst-Ø25 +
1 ön-Ø25 gerçek; **g251 = "Ø60.00" glyph sahtesi**) ve eksik R50/Ø60/üst-Ø25, (c) `Decisions` +
`compile_extrude_plan` genişletmesi (yükseltilmiş seviye + XZ-düzlemli kesim), (d) source-only
üretim + evaluator PASS kabulü. Reçete tamamlanınca §65 koşulur; o güne kadar PASS iddiası yok.

## Kural hatırlatması (her faz sonu, §96)

Case/file/hash dallanması yok · evaluator değeri producer'a kopyalanmaz · gerçek ölçü "gereksiz" diye
işaretlenmez · implicit extrude/revolve yok · tolerans geçirmek için genişletilmez · tarihsel kanıt
değiştirilmez · manifest değişmez · tekil örnek tek regresyon olamaz.
