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
