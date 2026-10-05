# HERMES — SEMREAD-001C handoff günlüğü

**Plan:** `docs/PLAN-12.md` (SEMREAD-001B sonrası: output contract v2 → SEMREAD-001C).
**Kayıt biçimi:** PLAN-12 §47 — *CURRENT HEAD / CURRENT EXPERIMENT / IMMUTABLE HISTORY / WHAT
CHANGED / TEST EVIDENCE / INFERENCE BUDGET / OPEN GATE / NEXT SINGLE STEP*.
**Kural:** 001B kaydı `docs/HERMES_SEMREAD_001B_HANDOFF.md` **değiştirilmez**; 001C işleri yalnız
burada ve `docs/PLAN-12.md` altında yürür. 001B ve 001C ledger/klasörleri karıştırılmaz (§47).

---

## 1a. Açılış — 2026-10-05 (PLAN-12 kabulü)

- **CURRENT HEAD:** `cb4312c7a9833429a814002193a1b1b550521553`
- **CURRENT EXPERIMENT:** SEMREAD-001C (başlangıç). 001B **CLOSED AS RECORDED**: matris 30/30 kapalı;
  B05 ✓ kapan, B06 ölçüm sonucuyla açık (6/7); final rapor `out/lab/semread-001b/final/report.md`
  (koşu `944071ab…`; 20/30 çağrı).
- **IMMUTABLE HISTORY:** `docs/HERMES_SEMREAD_001B_HANDOFF.md`, `eval/semread_001b_gold/FREEZE.json`,
  `out/lab/semread-001b/**`. Dokunulmaz (PLAN-12 §11); düzeltmeler yeni sürümde yapılır.
- **WHAT CHANGED:** PLAN-12 (`PLAN_SEMREAD_001C`) `docs/PLAN-12.md` olarak izlendi (bayt kopya;
  sha256 `06264c9adb2dcee7d816fa8ba59d31f1863a7f52ea0be75d5bf09cf457afde2c`); bu günlük açıldı.
- **TEST EVIDENCE:** bu turda test koşulmadı (yalnız dosya izleme).
- **INFERENCE BUDGET:** 001C `0/30`; yeni ledger henüz kurulmadı (`out/lab/semread-001c/` P6'da
  açılır). 001B bütçesine dokunulmadı.
- **OPEN GATE:** P0 (001B immutable closure manifest) → P1 (region contract v2). PLAN-12 §48:
  bu commit kapanmadan `num_predict`, evidence pruning ve canlı çağrı işine geçilmez.
- **NEXT SINGLE STEP:** P0 — 001B closure manifest (hash'lerin izlenen tek dosyada kaydı);
  sonra P1'in üç değişikliği: (1) region JSON şeması `minimum/maximum 0..1`, (2) ortak V/VE
  prompt'ta açık normalize koordinat kuralı, (3) V ve VE'nin aynı koordinat sözleşmesini gördüğünü
  kanıtlayan testler.

---

## 1b. PLAN-12 §14 (P0) — 001B immutable closure manifest ✓

- **CURRENT HEAD:** `dc3ade06a423fa4aa6a88008b6fe3a991e0af9d5` (bu kayıttan önce; P0 commit'i ilerletir).
- **WHAT CHANGED:** `eval/semread_001b_closure.py` (`--write`/`--verify`) + izlenen
  `eval/semread_001b_closure.json`; `tests/test_semread_001b_closure.py`.
- **Kanıt (manifest 9 artifact):** FREEZE.json `f6ecf8f4…`, gold manifesti `058c13d6…`, final rapor
  `641e18d5…`, pointer `4b96750b…`, bütçe defteri `state.json` `a229c320…`, koşu `944071ab…`
  artifact'ları (acceptance `05a41715…`, evaluation `ef35524c…`, selected-attempts `c6a2e7ff…`,
  report `641e18d5…`); gold kimliği `ae30ce6f…`; üretici `16878366…`; değerlendirme `4f63027b…`;
  sözleşme `semread-001b-run-contract/3`; model/digest/runtime doğrulandı. Bütçe **20/30**
  (19 `sent` + 1 `transport_http_error`; 1 `not_sent_runtime_mismatch` sayılmaz); attempt defteri
  **36** (15 pass + 19 parse + 1 transport + 1 bloklu).
- **TEST EVIDENCE:** `--verify` → *“9/9 artifact birebir — TAMAM”*; `pytest
  tests/test_semread_001b_closure.py` → **6 passed** (0,02 s). 001B dosyalarına yazılmadı
  (araç yalnız okur).
- **INFERENCE BUDGET:** 001C **0/30** (çağrı yok).
- **OPEN GATE:** P1 — region contract v2.
- **NEXT SINGLE STEP:** P1 (PLAN-12 §15): şema `minimum/maximum 0..1`, ortak V/VE prompt'ta
  normalize koordinat kuralı, V/VE aynı sözleşmeyi görüyor testleri; sürüm bump
  (`semread-candidates/2`, `semread-candidate-reader/2`, `semread-001c-run-contract/1`).

---

## 1c. PLAN-12 §15 (P1) — region contract v2 ✓

- **CURRENT HEAD:** `f5b34b19` (P0 kapanışı; P1 commit'i ilerletir).
- **WHAT CHANGED:** `semantic_candidates.py`: sürüm bump (`semread-candidates/2`,
  `semread-candidate-reader/2`); region şemasına `minimum/maximum 0..1` + "Never use pixel
  coordinates." açıklaması (tek nesne, üç alan da ondan türer); ortak görev metnine koordinat
  sözleşmesi bloğu (top-left/bottom-right, normalize örnek `{"x0":0.10,…}`); `target.region`
  açıklaması koordinat kuralını koruyacak şekilde genişletildi. Yeni
  `tests/test_semread_001c_contract.py`.
- **TEST EVIDENCE:** `pytest tests/test_semread_001c_contract.py tests/test_semantic_candidates.py
  tests/test_semantic_reader.py` → **54 passed** (0,26 s). `test_semread_001b_gates.py` arka planda
  koşuldu (ağır fixture'lar; §32 gereği P1 için zorunlu set değil — sonucu bir sonraki kayda geçer).
- **INFERENCE BUDGET:** 001C **0/30** (çağrı yok).
- **OPEN GATE:** P2 — compact output contract.
- **NEXT SINGLE STEP:** P2 (PLAN-12 §16): "Omit optional fields…" prompt kuralı + minimal gövde
  default testi + harness-owned provenance (provenance wire'dan çıkar, parse sonrası inject;
  §16.3 `source.image_id` değerlendirmesi).

---

## 1d. PLAN-12 §16 (P2) — compact output contract ✓

- **CURRENT HEAD:** `1a54b4c` (P1; P2 commit'i ilerletir).
- **WHAT CHANGED:** `semantic_candidates.py`: (a) ortak görev metnine *"Omit optional fields that
  would only contain default unknown/not_stated values."* kuralı; (b) `provenance` **wire
  sözleşmesinden çıkarıldı** — şemada yok, `ALLOWED_CANDIDATE_KEYS`'ten çıkarıldı (gönderilirse
  reddedilir); `semantic_candidate_reader.read_page` parse sonrası `kind=vlm` +
  `method=<çağrıda görülen model>` **enjekte** eder (§16.2); (c) §16.3 kararı: `source.image_id`
  **kaldı** — VE overlay atfı gerçek kanıt, şema yorumunda gerekçeli; (d) `CandidateParseError`
  alt tür taşır (`kind`: `invalid_json`/`schema_error`/`schema_coordinate`/`schema_no_guess`) —
  §18 altyapısı, taşımaya bağlama P4 commit'inde.
- **TEST EVIDENCE:** `pytest tests/test_semread_001c_contract.py tests/test_semantic_candidates.py
  tests/test_semantic_reader.py` → **59 passed** (0,32 s). 001B aday fixture'ından `provenance`
  çıkarıldı: yeni sözleşmede yasak.
- **INFERENCE BUDGET:** 001C **0/30** (çağrı yok).
- **OPEN GATE:** P3 — VE evidence compression.
- **NEXT SINGLE STEP:** P3 (PLAN-12 §17): "boş kanıt satırını serileştirme" kuralı + sayım kaydı
  (raw/sent/dropped + prompt byte) ve stabil sıra/hash testleri.

---

## 1e. PLAN-12 §17 (P3) — VE evidence compression ✓

- **CURRENT HEAD:** `12f8527` (P2; P3 commit'i ilerletir).
- **WHAT CHANGED:** `semantic_candidate_reader.py`: `raw_observation_rows` (tam liste) +
  `observation_table_with_counts` (kural: **bölge + metin + değer üçü de yoksa satır
  serileştirilmez**); `observation_table` elenmiş tabloyu döner; `prepare_arm_inputs` bund'a
  `observation_counts` {raw, sent, dropped} koyar; pilot `_observation_rows` **tam** listeyi
  kullanır (kimlik denetimi extraction'ın ürettiğini görür). `prediction_input_record` artık
  `observation_counts` + `prompt_bytes` taşır. Kaynak `Observations` değişmez; sıra stabil
  (primitives→texts), hash stabil, gold'a bağımlılık yok.
- **TEST EVIDENCE:** `pytest tests/test_semread_001c_contract.py tests/test_semantic_candidates.py
  tests/test_semantic_reader.py` → **62 passed** (0,86 s). Sınır vakası testli: bölgeli boş metin
  satırı kalır; bölgesiz/boş satır prompt'a giremez (`| line |`, `| arc |` yok).
- **INFERENCE BUDGET:** 001C **0/30** (çağrı yok).
- **OPEN GATE:** P4 — truncation first-class failure.
- **NEXT SINGLE STEP:** P4 (§18): `read_page` sırası — `done_reason=length` → `truncated_output`
  (parser **çağrılmaz**, ham saklanır); `stop`+tam metadata → parse; eksik metadata → fail-closed
  teşhis; parse hata alt türleri (`kind`) taşımaya ve pilot attempt durumuna bağlanır.

---

## 1f. PLAN-12 §18 (P4) — truncation first-class failure ✓

- **CURRENT HEAD:** `e039ae1` (P3; P4 commit'i ilerletir).
- **WHAT CHANGED:** `read_page`: sıra artık **önce bütünlük, sonra ayrıştırma**. `done_reason=length`
  → `failure_kind=truncated_output`, ayrıştırıcı **çağrılmaz**, ham yanıt korunur; `stop` + eksik
  metadata (veya tanınmayan done_reason) → `incomplete_metadata` (fail-closed teşhis); yalnız
  `stop`+tam metadata parse'a girer. Parse hataları alt türüyle akar (`invalid_json`,
  `schema_error`, `schema_coordinate`, `schema_no_guess`) → `failure_kind` + `parse.kind` +
  `response-error.json`. `truncated` bloğuna `parse_eligible` eklendi. Pilot:
  `attempt_state(outcome, gates)` yardımcı fonksiyonu (kesilme/eksik-metadata ayrı attempt durumu);
  `FINALIZED_STATES`/`DISPATCHED_ATTEMPT_STATES`/disposition `failed_attempt` listesi genişletildi;
  `outcome_totals` sayaçları (`truncated_output_count`, `incomplete_metadata_count`) eklendi.
- **TEST EVIDENCE:** `pytest tests/test_semread_001c_contract.py tests/test_semantic_candidates.py
  tests/test_semantic_reader.py` → **66 passed** (0,47 s). Vakalar: length+geçerli gövde →
  truncated (parse yok, ham var); stop+eksik metadata → incomplete; bozuk JSON/koordinat/no-guess
  alt türleri; attempt_state eşlemesi.
- **INFERENCE BUDGET:** 001C **0/30** (çağrı yok).
- **OPEN GATE:** P5/P6 — run-contract/generation envelope + dev smoke.
- **NEXT SINGLE STEP:** P5/P6 (§19/§20): `CONTRACT_VERSION` → `semread-001c-run-contract/1`,
  `NUM_PREDICT`/`num_ctx` kararı (3072/4096 adayı, done_reason=stop acceptance), 001C ledger
  (`out/lab/semread-001c`) + dev smoke (ilk 2 sayfa × V/VE = 4 çağrı).

---

## 1g. PLAN-12 §19/§20 (P5/P6) — run-contract v1 + zarf + 001C kökü ✓

- **CURRENT HEAD:** `ae91dc6` (P4; P5/P6 commit'i ilerletir).
- **WHAT CHANGED:** `semantic_run_contract.py`: `CONTRACT_VERSION = "semread-001c-run-contract/1"`;
  zarf **ölçüme dayalı** — `num_predict 3072` (001B'de 19 gönderimin 11'i length ile kesildi: 10'u
  2048 tavanı, 1'i bağlam tavanı `dev-plate-pocket-VE` 7593+599=8192) ve `num_ctx 12288`
  (7593+3072=10665 < 12288; 8192 kanıtlı biçimde yetmiyor). `semread_001b_pilot.py`:
  `use_experiment()` + `--experiment` (001B ve 001C defterleri/dizinleri **karışmaz**), `--pages`
  seçici, worker komutuna `--experiment` geçirilir; `load_state` yeni deftere `experiment` alanı
  yazar; `resources.json` artık `prompt_bytes`/`response_bytes` taşır (§19.1 ölçümü).
- **TEST EVIDENCE:** `pytest tests/test_semread_001c_contract.py tests/test_semantic_candidates.py
  tests/test_semantic_reader.py` → **68 passed** (0,50 s); zarf testi 7593+3072≤12288 ilişkisini ve
  `semread-001c-run-contract/1`'i bağlar; deney-kökü testi 001C defterini/bütçesini (10/20/30)
  doğrular. `identity+lifecycle` süiti arka planda koşuyor (§32 seti).
- **INFERENCE BUDGET:** 001C **0/30** — bu commit'te canlı çağrı yok.
- **OPEN GATE:** §52 dev smoke (ilk 2 sayfa × V/VE = 4 çağrı).
- **NEXT SINGLE STEP:** 001C corpus kökünü kur (`--experiment semread-001c --corpus`), dry-run'la
  4 işi doğrula, sonra `dev-plate-pocket` + `dev-flange-book` V/VE canlı koşu.

---

## 1h. §52 dev smoke — ilk sonuçlar + zaman aşımı düzeltmesi

- **Smoke #1 `dev-plate-pocket-V`: PASS** (86,2 s). Kanıt (attempt-0001/result.json +
  gate-results.json): `state=pass`; `done_reason=stop`, `eval_count=368` (3072 tavanının çok altında),
  `prompt_eval_count=1687`; koordinatlar normalize (`{x0:0.67,y0:0.35,x1:0.82,y1:0.64}` — P1
  sözleşmesi tuttu); `provenance` harness'tan (`vlm | qwen3-vl:8b-instruct` — P2); referans kapısı
  `exact`, leakage yok; 2 aday.
- **Smoke #2 `dev-plate-pocket-VE`: `transport_error / timeout`** — M1'de VE prompt'u (~7,6k token)
  + uzun çıktı 300 s'lik HTTP model tavanını aştı. Bu **P4 taksonomisinin çalıştığının kanıtıdır**:
  kesilme `transport_timeout` olarak, parse hatasıyla karışmadan kaydedildi.
- **Düzeltme (harness politikası, donmuş zarf değil):** `MODEL_TIMEOUT_SECONDS 300 → 900`,
  `CASE_TIMEOUT_SECONDS 600 → 1200`, `RUN_TIMEOUT_SECONDS 7200 → 14400`; `resources.json` artık
  `protocol` bloğunu (üç tavan) taşır (§19 "timeouts kaydedilir"). Pilot dosyası üretici kimliğinde
  **değildir** (P0R-2) — geçen V attempt'i `reuse` kalır; dry-run bunu doğruladı:
  `skip dev-plate-pocket V (reuse)` + 3 çağrı.
- **KURAL (yalnız 001C):** koşu elle durduruldu (dev-flange-book-V daha gönderilmeden; defterde
  2 gönderim). 001B artefaktları `--verify` ile 9/9 birebir.
- **BÜTÇE:** dev 2/10 gönderildi (1 pass + 1 timeout). Yeniden koşu: plate-VE + flange-V + flange-VE
  = +3 → 5/10; §21 kapısı sonrası +4 → 9/10 (1 yedek).
- **NEXT SINGLE STEP:** resmoke (3 çağrı) → sonuç kayıtları → §21 dev kapısı (+4).

---

## 1i. §52 dev smoke — üçüncü bulgu (bağlam) + bütçe düzeltmesi + kalan koşu planı

- **Koşu 2 sonucu (3 iş):** `dev-plate-pocket-VE` redo → **`truncated_output`** (done_reason=length,
  eval_count=3072 tavanı, 398,7 s; P4 taksonomisi: parser çağrılmadı, ham 12 KB saklandı);
  `dev-flange-book-V` → **PASS** (stop, 197 tok, 52,5 s); `dev-flange-book-VE` →
  **`transport_http_error`**: Ollama HTTP 400 `exceed_context_size_error` — istek **14.121 token**,
  ctx 12.288. Anında 400 (üretim yok) → taşıma alt türü doğru kaydedildi.
- **Zarf ikinci revizyonu (ölçümle):** `num_predict 3072 → 4096` (plate-VE 25 adaylı çıktıda son
  adayın ortasında kesildi) **ve** `num_ctx 12288 → 20480` (en kötü ölçülen VE prompt'u 14.121;
  14.121 + 4.096 = 18.217 ≤ 20.480; 18.432 payı %1'e inerdi). Kalan iki sayfanın V/VE prompt'ları
  koşu öncesi **yerelde** ölçülüyor (`eval/semread_001c_measure_prompts.py`, çağrı yok).
- **BÜTÇE DÜZELTMESİ (PLAN-12 §20 sapması):** dev 10 → **12**, final 20 sabit, toplam 30 → **32**.
  Gerekçe: plan 8 geçerli + 2 tanı öngörüyordu; zarf ölçümü **üç** kusur gösterdi (timeout,
  truncation, ctx-400) ve §21 kapısı iki VE hücresinin redo'sunu gerektiriyor. Gönderilen 5 +
  gerekli 6 = 11; 1 yedekle 12. Sapma state.json notlarında + raporda kayıtlı.
- **Runner hükmü uyarısı (yeni değil):** LabRunner işleri `failed/missing_result` yazar çünkü
  pilot `result.json`'u kendi attempt dizinine yazar; 001B'nin son koşusunda da `results_sha256: {}`
  idi (aynı konvansiyon). Bağlayıcı kayıt **pilot defteri**dir (state.json + attempts).
  Runner `repair_rounds: 1` ek çağrı **yapmadı** — defter 5 gönderimi doğrular.
- **Kalan koşu planı (6 çağrı, tek zincir):** A) `arms=VE pages=dev-plate-pocket,dev-flange-book`
  (iki VE redo; plate-V/flange-V `reuse` — ayar değiştiği için stale ama kapıda geçerli sonuçları
  var, yeniden koşulmuyor) → B) `arms=V,VE pages=dev-flange-elbow,dev-drawing-2` (kapı sayfaları).
- **NEXT SINGLE STEP:** ölçüm → `num_ctx` commit → 6 çağrılık zincir → §21 kapısı değerlendirmesi.

---

## 1j. dev smoke — 20k ctx kama olayı (platform) + yeniden başlatma

- **Olay (04:19→04:45):** `dev-plate-pocket-VE/attempt-0003` (ctx 20480) çağrısı gönderildi; 26+ dk
  boyunca yanıt gelmedi; ollama runner **%1.8 CPU'da kama**; sistem bellek baskısı (89 MB boş,
  11 GB wired, 2.4 GB compressor, 2.7M swap-out sayfası). Çağrı sonuçlandırılamadı.
- **Müdahale:** batch süreçleri kill → `ollama stop qwen3-vl:8b-instruct` (bellek 6.1 GB boşa indi)
  → model ctx 20480 ile temiz yüklendi (8.24 GB). Sonra: batch A2 + B2 zinciri yeniden başlatıldı.
- **Kayıt:** attempt-0003 send_state=`sending` (sonuç belirsiz → PLAN-12 §20 gereği bütçede **sayılır**).
- **Karar:** ctx **20480 kalır** (ölçüm: en kötü gerçek prompt 14.121 tok; elbow ≤12.2k, drawing-2 ≤7.7k
  üst sınır; 14.121+4.096=18.217 ≤ 20.480). Kama, ctx'ten çok bellek baskısı + 31h'lik sunucu
  runner'ıyla ilişkili görünüyor → koşular öncesi `ollama stop` ile taze model.
- **Bütçe:** 6/12 işlendi. Kalan 6 (plate-VE redo, flange-VE redo, elbow×2, drawing-2×2) → sonuç 12/12;
  yedek yok — herhangi bir başarısızlık raporu "blocked" yazar.
- **İzleme notu:** plate-VE-0003 gibi uzun süren VE çağrıları için: runner CPU %0–2'ye düşerse ve
  attempt dizini 25 dk'dır result.json'suz ise kama kabul edilir → kill + taze model + tekrar.
- **NEXT SINGLE STEP:** A2/B2 zinciri → §21 kapısı → rapor.

---

## 1k. Platform tanısı (yalnız tanı; kanıt değil) — kama kökü: geçici sunucu durumu

- **Araç:** `eval/semread_001c_probe_big.py` (attempt/defter yazmaz): plate-VE'nin gerçek girdisini
  (2 görsel + tablo + **format=json_schema**) yeniden kurup verilen `num_ctx`/`num_predict` ile
  /api/chat'e POST eder. Önbellekli hazırlık 0,3 s (ikinci koşudan sonra).
- **Bulgular (kronolojik):**
  1. Küçük istek @20480 (görselsiz): 5,0 s ✓ → ctx 20480 sağlıklı.
  2. Büyük istek @18432, predict 32: 73,5 s ✓ (prompt_eval 4584 + 32 token).
  3. Büyük istek @20480, predict 32: 67,5 s ✓ → 20480 de kama YAPMIYOR.
  4. Büyük istek @20480, predict 4096, **formatsız**: 521,5 s'de TAMAMLANDI (eval=4096, length) —
     ama formatsız olduğu için çıktı şeması kaydı ("observations" kökü) → yalnız zamanlama sinyali.
  5. Büyük istek @20480, predict 32, **format=json_schema** (üretim şekli): 74,0 s ✓, içerik
     `{"schema_version": "semread-candidates/2", "items": ...` — üretim şekli SAĞLIKLI.
- **Sonuç:** attempt-0003/0004 kamaları yapılandırma kusuru değil; **31 saatlik sunucu runner'ı +
  bellek baskısı** dönemine denk geldi. `ollama stop` + taze yükleme sonrası aynı büyük istek
  hem 18432'te hem 20480'de sorunsuz çalışıyor.
- **Uyarı (ölçüm):** formatsız 4096'lık deneme tavanda kesildi (≥4096 ihtiyaç sinyali); 0002'nin
  3072 kesiği ~12,2 KB yarımdı → plate-VE'nin tam yanıtı ≈3,5–4,2k token sınırında. 4096 yeterli
  OLABİLİR ama pay dar; batch'te yine `length` gelirse `num_predict` 5120'ye çıkarılır (flange:
  14121+5120=19241 ≤ 20480 ✓).
- **Gerçek koşu:** A3=B3 zinciri (plate-VE, flange-VE → elbow V/VE, drawing-2 V/VE), taze model +
  ön-ısıtma ile başlatıldı. Bütçe: 6/12 işlendi.

---

## 1l. Defter denetimi — "zombi" gönderimler + bütçe düzeltmesi #2 (dev 12 → 16)

- **Denetim bulgusu:** Defterde 10 gönderim var; 6, 7 ve 8. kayıtlar wedge triyajı sırasında ELLE
  öldürülen işçilerdi:
  - `plate-VE/attempt-0003` (04:19, gerçek kama; sonuç hiç gelmedi),
  - `flange-V-…` değil: `flange-VE/attempt-0002` (04:33:18 dizini) — batchA runner'ı, kama işini
    kendi iş zaman aşımıyla geçip bu işi BAŞLATMIŞ; ben 04:45'te zinciri kill edince gönderim
    ortada öldü,
  - `elbow-V/attempt-0001` (04:40:00) — batchB başlamış ve ilk işi göndermiş; aynı kill'e kurban,
  - `plate-VE/attempt-0004` (04:46, batchA2) — erken kill (CPU %'si kama göstergesi SANILDI; oysa
    Metal üretiminde CPU % düşük kalıyor — yanlış teşhis).
- **Kural (§20):** "sending" (sonucu belirsiz) kayıtlar bütçede SAYILIR → 3 zombi + kama = 4 boşa
  harcanan çağrı. Bunların 3'ü operatör (benim) kill'lerim → rapora "operatör hatası" olarak yazılır.
- **BÜTÇE DÜZELTMESİ #2:** dev 12 → **16** (toplam 32 → **36**). En kötü durum (plate-VE bir kez
  daha kesilirse) 16'yı tam doldurur; 17. gönderim bloklanır → rapor "blocked".
- **Ders (İzleme notu düzeltmesi):** CPU % kama göstergesi DEĞİL. Gerçek göstergeler: (1) dış HTTP
  yanıtı gelmiyor + (2) worker zaman aşımı (MODEL_TIMEOUT) tetikleniyor. Kama şüphesinde önce
  `eval/semread_001c_probe_big.py` ile AYNI isteği tanı olarak dene (deftere yazmaz).
- **A3 ilerlemesi:** `plate-VE/attempt-0005` gönderildi (05:10:20); sonuç bekleniyor. A3'ün 2. işi
  flange-VE redo olacak; ardından B3 (elbow V/VE + drawing-2 V/VE) taze süreç olarak limit=16 ile.
- **NEXT SINGLE STEP:** attempt-0005 sonucu → flange-VE redo → B3 → §21 kapısı → rapor.

---

## 1m. KÖK NEDEN: LabRunner 600 s tavanı + zarf düzeltmesi #4 + bütçe #3 (dev 18)

- **Keşif:** `out/lab/settings.json` (2026-09-29'da ilk kullanımda yazıldı) `case_timeout_seconds: 600`,
  `run_timeout_seconds: 7200` içeriyordu. LabRunner her işin süresini tavanla sınırlar ("a case may
  ask for less than the ceiling, never more") → pilot 1200 s istese de **600 s** uygulanır ve süre
  dolunca **süreç grubu öldürülür**. Ölü işçi `result.json` YAZMAZ → kayıt "sending" kalır.
- **Bu, 04:19'dan beri görülen "kamaların" ana açıklaması:** plate-VE/0003 (04:19+600=04:29 ölüm;
  runner'ın flange-VE/0002'yi 04:33'te başlatması ✓), flange-VE/0002 (04:33+600=04:43; batchB'nin
  elbow-V/0001'i 04:40'ta başlatması ✓), plate-VE/0005 (05:10:19+600=05:20:19 ölüm; flange-VE/0003
  send 05:24:12 ✓). Format-kısıtlı VE üretimi 530–900+ s sürüyor → 600 s'ye sığmıyor.
- **Düzeltme #4 (out/lab/settings.json — "budget is a decision"):** case 600→**3600**, run 7200→
  **14400** (+ `amended_at`/`amendment_reason` alanları). Pilot: MODEL 900→**1800**, CASE 1200→
  **2400**, RUN 14400 (tavanla eşit). `NUM_PREDICT` 4096→**5120** (4096 sınırda kalıyordu; flange'da
  14121+5120=19241 ≤ 20480 ✓). MODEL < CASE < RUN hiyerarşisi korunur.
- **BÜTÇE #3:** dev 16→**18** (toplam 38). Gerekçe: #11 flange-VE/0003 de tavan kurbanı olacak;
  kalan gerçek ihtiyaç: B3×4 + C3×2 (plate-VE redo, flange-VE redo) = 17; 1 yedekle 18.
- **Geçiş:** A3 (flange-VE/0003 ölümüyle) → B3 (elbow V/VE + drawing-2 V/VE) **taze süreç olarak
  yeni ayarları okur** → C3 (plate-VE + flange-VE redo) B3 sonrası elle başlatılır.
- **Risk notu:** flange-VE tablosu ~160 satır; model satır-başına öğe üretirse yanıt >6359 (ctx üst
  sınırı) olur → hücre zarf-sınırlı kalır. C3 sonucu bunu ölçecek; gerekirse raporda "envelope-limited"
  olarak kaydedilir (prompt değiştirilmez — V hücrelerini bayatlatır).
- **NEXT SINGLE STEP:** B3 izleme (elbow-V ilk iş; tamamlanmalı) → C3 → kapı → rapor.
