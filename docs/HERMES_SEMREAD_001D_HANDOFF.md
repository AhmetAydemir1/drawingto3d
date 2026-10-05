# HERMES — SEMREAD-001D handoff günlüğü

**Plan:** `docs/PLAN-15.md` — SEMREAD-001D ("`/3` prompt/schema sonrası: producer identity →
dev-report → static preflight → Round 1 semantic proof"). PLAN_LATEST olarak izlenir (bayt kopya,
sha256 `909e46cb67aac205b0e270861a364ad79e69eaa2a1b74aa8cf2a4d572109144e`). PLAN-15 §48: **yeni
history entry** — PLAN-14 son izlenen revizyonuyla (`39cf9b84…`; önceki revizyonlar `a027cb4a…`,
`f2d249b7…`) geçmiş olarak korunur; PLAN-13 + PLAN-12 + kök PLAN.md history olarak korunur.
**Kayıt biçimi:** PLAN-12 §47 — *CURRENT HEAD / CURRENT EXPERIMENT / IMMUTABLE HISTORY / WHAT
CHANGED / TEST EVIDENCE / INFERENCE BUDGET / OPEN GATE / NEXT SINGLE STEP*.
**Kural:** 001C kaydı `docs/HERMES_SEMREAD_001C_HANDOFF.md` ve `out/lab/semread-001c/**`
**değiştirilmez** (001C READ-ONLY HISTORICAL; closure: `eval/semread_001c_closure.json` —
`--verify` 45/45). 001D işleri yalnız burada + PLAN-15 altında yürür; ledger'lar karıştırılmaz.

---

## 1a. Açılış — 2026-10-05 (PLAN-14 kabulü; 001C immutable kapanış sonrası)

- **CURRENT HEAD:** `b884dae` (bu kayıttan önce; skeleton commit'i ilerletir)
- **CURRENT EXPERIMENT:** SEMREAD-001D (başlangıç). 001C **CLOSED — READ-ONLY HISTORICAL**:
  §8 resmî kapı 7/8 (elbow-VE `schema_coordinate`; tek koordinat ihlali
  `c32.callout_region.y1 = 1.05`), paylaşımlı ayar 8/8, stop 8/8, içerik 0/8; bütçe dev 32/32 +
  final 0/20; karar: yeni experiment version (PLAN-13 §7 → PLAN-14). Kayıt: 001C handoff §1t +
  `report.md` Kapanış bölümü.
- **IMMUTABLE HISTORY:** `docs/HERMES_SEMREAD_001C_HANDOFF.md`, `docs/PLAN-13.md`,
  `eval/semread_001b_gold/FREEZE.json`, `eval/semread_001c_closure.{py,json}`,
  `out/lab/semread-001c/**`. Dokunulmaz; düzeltme yeni sürümde (PLAN-14 §9/§39).
- **WHAT CHANGED:** PLAN-14 `docs/PLAN-14.md` olarak izlendi (bayt kopya, yukarıdaki sha256);
  bu günlük açıldı; pilot bütçe tavanları 001D'nin deklare bütçesine geçirildi (dev **12** =
  8 primary + 4 tanı rezervi, final **20**, toplam **32** — PLAN-14 §24); kök `report.md`
  aktif-plan pointer'ı PLAN-14'e çevrildi; `tests/test_semread_001d_skeleton.py` eklendi.
- **TEST EVIDENCE:** skeleton **4 passed**; odak süiti (skeleton + closure + 001c contract +
  reader/candidates + dev-semantik + 001b closure) **99 passed**; hızlı SEMREAD süitleri
  (lifecycle/identity/gold-manifest/reference/probe) **143 passed**; gates bütçe-caps alt kümesi
  **5/5**; gates dosyası tamamı (34 test) **34 passed** (990 s / 16:30 — ağır BLAS/numpy
  ön-işlemeli test; süre önceden de böyle, bütçe değişiminden bağımsız); 001C closure
  `--verify` **45/45**.
- **INFERENCE BUDGET:** 001D dev **0/12**, final **0/20** (toplam **0/32**); ledger
  `out/lab/semread-001d/` ilk dev çağrısında kurulur (§41#8). 001C bütçesine dokunulmadı
  (32/32 kapalı, READ-ONLY).
- **OPEN GATE:** §41#4 — semantic-content validator.
- **NEXT SINGLE STEP:** §41#4: §13 tanımıyla `semantic_content_count` ölçen deterministic
  validator (yalnız `source.region` taşıyan aday içeriksiz; gözlem-satırı kopyası da sayılmaz —
  §13/§20) + odak testler; şema/sözleşme v3 bu adımın devamıdır (§17–§22).

---

## 1b. §47 semantic-content sözleşmesi — tek kaynak tanım + wire reddi (0 inference) — 2026-10-05

- **CURRENT HEAD:** `074cc40` (bu kayıttan önce; bu commit §47 işini taşır)
- **CURRENT EXPERIMENT:** SEMREAD-001D. **Aktif plan revize izlendi:** `docs/PLAN-14.md` artık
  "Skeleton sonrası güncel plan" revizyonu (bayt kopya, sha256
  `a027cb4aa8e27cd2ed732f9b9e3f247cf8b00013a8d2c52bb3bf948788cbc22f`; önceki revizyon `f2d249b7…`
  git history'de; skeleton test pin'i güncellendi). 001C **CLOSED / READ-ONLY** — closure
  `--verify` bu commit'te tekrar koşuldu: **45/45**.
- **IMMUTABLE HISTORY:** değişmedi — `docs/HERMES_SEMREAD_001C_HANDOFF.md`, `docs/PLAN-13.md`,
  `eval/semread_001b_gold/FREEZE.json`, `eval/semread_001c_closure.{py,json}`, `out/lab/semread-001c/**`.
- **WHAT CHANGED:** §47'nin tek işi (0 inference):
  1. **Semantik-içerik tanımı tek kaynak** (`semantic_candidates.py`): `semantic_claim_flags` /
     `candidate_has_semantic_claim` / `evidence_flags` + kapalı listeler `SEMANTIC_CLAIM_SOURCES` /
     `EVIDENCE_SOURCES`. Tanım hem `Candidate` nesnesiyle hem kayıtlı `response-parsed.json`
     sözlüğüyle çalışır (dev raporu/final değerlendirici aynı fonksiyonu reuse edecek — kopya
     mantık yok). Ayrım: representation / found_circles / target.state / observation_id /
     source.region / uncertainty **tek başına** adayı geçerli saymaz (§3).
  2. **Wire reddi:** `parse_candidate_json` sırası **JSON → yapısal → semantik** oldu; yalnız
     kanıt/bölge alanları taşıyan aday `schema_semantic_empty` alt türüyle reddedilir (sessiz
     tamir yok — tek içeriksiz aday yanıtın tümünü düşürür); boş `items` **geçerli abstention**
     kalır (§5/§7).
  3. **D yolu audit'i (§6):** `semantic_deterministic` wire parser'a **girmez** — `Candidate`'ı
     doğrudan kurar; kural global Pydantic validator değildir, D çıktı yolu etkilenmez (testle
     bağlı: D kaynağında parser yok, V/VE okuyucusunda var; kanıt-only aday model düzeyinde
     kurulmaya devam eder).
  4. 001C contract testlerinden **üç kabul fixture'ı** tek semantic claim taşır hale getirildi
     (claimsiz gövde yalnız yapısal ret yollarında — ret sırası değişmedi); yeni odak dosyası:
     `tests/test_semread_001d_semantic_content.py` (negatif matris §8'in altısı da, pozitif
     matris §9'un dokuzu da, sıra/abstention/D auditi/taşıma sınırı dahil).
  5. Kök `report.md` **experiment-neutral yaşam belgesine** döndü (PLAN-14 §2-A seçildi):
     "§0 Aktif deney — SEMREAD-001D" + 001C kaydı HISTORICAL etiketiyle; plan sha'sı güncel.
  Prompt/schema/run-contract bump'ı §47 gereği **bir sonraki commit'te** (`/3` + `/3` + `001d/1`).
- **TEST EVIDENCE:** yeni odak dosyası **32 passed**; odak süiti (yeni + skeleton + closure + 001c
  contract + candidates/reader + dev-semantik + 001b closure) **131 passed**; hızlı SEMREAD
  süitleri (lifecycle/identity/gold-manifest/reference/probe) **143 passed**; 001b değerlendirme
  süiti **32 passed**; gates dosyası tamamı **34 passed** (1014.85 s ≈ 16:54 — ağır BLAS
  ön-işlemeli test; süre sınıfı önceki koşuyla aynı, değişiklikten bağımsız); 001C closure
  `--verify` **45/45**.
- **INFERENCE BUDGET:** 001D dev **0/12**, final **0/20** (toplam **0/32**) — değişmedi; bu commit
  **0 inference** (yalnız saf fonksiyonlar + taşıma taklidi; ledger kurulmadı).
- **OPEN GATE:** §46#3 — prompt v3 + schema/reader `/3` (semantic-content + no-guess görev metni),
  ardından §46#4 run-contract `001d/1` kimliği (attempt manifestinde `experiment = semread-001d`).
- **NEXT SINGLE STEP:** §10/§12: `semread-candidates/3` + `semread-candidate-reader/3` bump'ı ve
  prompt v3 (ana kural: "Do not emit a candidate unless it contains at least one semantic claim" +
  no-guess cümlesi); §11: bump sonrası 001C closure `--verify` hâlâ 45/45 olmalı — geçmezse
  inference yok.

---

## 1c. §61 schema/reader `/3` + prompt v3 (0 inference) — 2026-10-05

- **CURRENT HEAD:** `4777caf` (bu kayıttan önce; bu commit §61 işini taşır)
- **CURRENT EXPERIMENT:** SEMREAD-001D. **Aktif plan revize izlendi:** `docs/PLAN-14.md` artık
  "semantic-content validator sonrası güncel uygulama planı" revizyonu (bayt kopya, sha256
  `39cf9b8483f5cbfa03e0683cebcea4dba7d47dc68a0867b8da76057e7aaf088d`; önceki revizyonlar
  `a027cb4a…`, `f2d249b7…` git history'de; skeleton test pin'i güncellendi). 001C
  **CLOSED / READ-ONLY** — closure `--verify` bu commit'te tekrar koşuldu: **45/45**.
- **IMMUTABLE HISTORY:** değişmedi — `docs/HERMES_SEMREAD_001C_HANDOFF.md`, `docs/PLAN-13.md`,
  `eval/semread_001b_gold/FREEZE.json`, `eval/semread_001c_closure.{py,json}`, `out/lab/semread-001c/**`.
- **WHAT CHANGED:** §61'in tek işi (0 inference; yalnız saf fonksiyonlar + şema/prompt/parser):
  1. **Sürüm kimliği `/3` (§3):** `semread-candidates/3` + `semread-candidate-reader/3`. `/3`
     version notes'ta açıkça yazılı: semantic-empty aday geçersiz · semantic claim ≠ evidence-only ·
     prompt semantic-first · no-guess korunur. Parser sürüm uyuşmazlığını (`/2` gövdesi)
     `schema_error` ile reddeder; semantik-içerik reddi (`schema_semantic_empty`) ve boş `items`
     abstention'ı aynen sürer.
  2. **Şema modelin sözleşmesini görüyor (§4):** candidate item açıklaması tek kaynak sabitten gelir
     (`SEMANTIC_CONTENT_REQUIREMENT`): "A candidate must contain at least one semantic claim. A
     region, representation, found-circle count, target binding, observation id or uncertainty alone
     is not a semantic claim." Kanıt-yalnız alanlar (source.region / callout_region / target.region,
     representation.kind, count.found_circles, target.observation_id, target.state, uncertainty) tek
     literalden (`EVIDENCE_ONLY_NOTE`) işaretlenir — şema ile parser aynı yönü gösterir.
  3. **`anyOf` YOK (§5):** semantic zorunluluğu JSON Schema `anyOf` ile encode etmek bilinçli olarak
     ertelendi (backend desteği kanıtlanmadan production şeması büyütülmez); önerilen sıra §5'te:
     prompt+description → parser → sentetik uyumluluk testleri → backend kabul kanıtı → ancak gerekirse.
  4. **Prompt v3 (§6/§7/§8/§9):** ortak V/VE görev metni semantic-first — "First identify a printed
     semantic fact. Only then create a candidate. / A region alone is not a candidate. / A machine
     observation row is not a semantic claim. / Do not emit a candidate unless it contains at least
     one semantic claim."; ardından semantik claim örnekleri ve **evidence-only** kapalı listesi;
     zorunlu no-guess anti-pressure cümleleri ("If you cannot read at least one semantic fact, emit no
     candidate for that feature." / "Do not invent a semantic fact merely to satisfy the
     semantic-content requirement."); 001B no-guess kuralı ("Never guess." + "A field you cannot read
     must not delete the fields you did read.") geri çekilmedi. VE farkı **yalnız kanıt bölümü**:
     "Observations are evidence, not candidate seeds. / Do not create one candidate per observation
     row. / Use an observation only if it helps support a semantic claim." (± §7'nin V/VE ayrımı).
  5. Yeni odak dosyası `tests/test_semread_001d_prompt_v3.py` (12 test): sürüm kimliği + `/2` reddi,
     item açıklaması, kanıt-yalnız işaretleri, `anyOf`/`oneOf` yokluğu, semantic-first sırası,
     claim/evidence ayrımı, no-guess cümleleri, anti-loop kuralları, VE yasağı, **iki kol farkının
     yalnız kanıt bölümü olması**, sayfaya özel/gold metin yokluğu, parser katılığı. 001C contract
     testindeki sürüm assertion'ı `/3`'e güncellendi (ret sırası değişmedi).
  6. Kök `report.md` §0 güncellendi (kod current `/3`; sıradaki iş `001d/1` kimliği).
- **TEST EVIDENCE:** yeni odak dosyası **12 passed**; odak süiti (prompt-v3 + semantic-content +
  skeleton + 001c closure + 001c contract + candidates + 001c dev-semantik + 001b closure)
  **121 passed**; hızlı SEMREAD süitleri (lifecycle + identity + gold-manifest + reference +
  `test_semread_001b`) **119 passed** (001b değerlendirme süiti `test_semread_001b.py` **32 passed**);
  gates dosyası tamamı **34 passed** (1049.34 s ≈ 17:29 — ağır BLAS ön-işlemeli test, süre sınıfı
  önceki koşularla aynı); 001C closure `--verify` **45/45**; `eval/check_tables.py`
  **21 satır / 0 tutmuyor**.
- **§28/§29 — D regresyon kanıtı (0 inference):** `eval/semread_001c_dev_semantic_eval.py`
  **salt-okur** koşuldu (`--write` yok; deftere/`out/lab/semread-001c/**`'a yazılmadı; VLM zinciri
  import edilmedi). Sonuç dondurulmuş 001C kaydıyla (`out/lab/semread-001c/dev-semantic-report.json`)
  programatik karşılaştırıldı: **12 hücrenin 12'si içerik düzeyinde birebir aynı** — `fill`, `flags`,
  `partition`, `duplicates`, `gates`, `summary`, `result_sha256`, `parsed_sha256` ve attempt
  `producer_identity` dahil. Tek fark V/VE hücrelerinde `dev_report_chosen` / `matches_dev_report`
  işaretleri (eski kayıt seçimi sabitlenmeden önce yazılmıştı; şimdi donmuş `dev-report.json`
  seçimiyle **tutarlı**: `matches_dev_report = true`). D kolu metrikleri 001C kaydıyla aynı:
  53 aday / 53 içerikli, 2 eşleşen, yerelleştirme %9.1, alan doğruluğu %66.7, hedef bağlama %100,
  overclaim %0, FP 9, unscorable 42; aday dağılımı (min 7 / medyan 14.5 / max 17 / toplam 53) aynı
  ⇒ **wire semantik-içerik kuralı ve `/3` kimliği D yolunu etkilemiyor** (§28).
- **INFERENCE BUDGET:** 001D dev **0/12**, final **0/20** (toplam **0/32**) — değişmedi; bu commit
  **0 inference** (ledger kurulmadı, canlı çağrı yok).
- **OPEN GATE:** §60#2 / §63 — `semread-001d-run-contract/1` kimliği + producer identity.
- **NEXT SINGLE STEP:** §10/§63: `CONTRACT_VERSION = semread-001d-run-contract/1`, docstring current
  durumu 001D anlatır (001C closure artifact'ında kalır); paylaşılan envelope **değişmez**
  (model/digest/runtime/ayarlar), producer identity değişir, dry-run manifest
  `experiment = semread-001d` + `/3` + `/3` + `001d/1` der; bütçe 0/12 + 0/20 kalır; closure
  `--verify` hâlâ 45/45 olmalı.

---

## 1d. 001B acceptance bonus koşusu — ölçümsüz kapanabilen rapor kapısı (bulundu + düzeltildi)

- **CURRENT HEAD:** `e879369` (§61 commit'i; bu kayıttan önce)
- **CURRENT EXPERIMENT:** SEMREAD-001D — bu kayıt **0 inference** (yalnız kapı/ölçüm tanımı).
- **NE OLDU:** §62'nin zorunlu listesinde olmayan `tests/test_semread_001b_acceptance.py` bonus
  olarak koşuldu: **1 failed / 25 passed** (1965.18 s ≈ 32:45). Tek kırmızı:
  `test_the_report_carries_every_required_section_on_the_real_payload` satır 213
  (`checks["measured"] == bool(payload["aggregates"])`) — sol taraf `True`, sağ taraf `bool({})`.
- **KÖK NEDEN (iki katman, ikisi de kanıtlandı):**
  1. **Beklenen durum; `/3` bump'ının sonucu değil.** Pilot kökü `out/lab/semread-001b`; oradaki
     35 attempt manifestinin **tamamı** `candidate_schema = semread-candidates/1` (üretici kimliği
     `16878366a1ab…`). Yeniden seçim `manifest.candidate_schema == CANDIDATE_SCHEMA_VERSION`
     istediği için `/2`'den beri hiçbir attempt seçilemez: bugünkü probe `final_matrix()`de
     30 hücrenin **0'ında** attempt gösteriyor (`not_run 10 / failed_attempt 20`,
     `vlm:to_run 20`, `d:to_run 10`). Yani `aggregates` boş — PLAN-14 §19'un "güncel kimlik yoksa
     `missing/failed` raporla" durumu.
  2. **Gerçek kusur (düzeltildi):** `aggregates` boşken `comparison.vs_d` yine satır taşır (ölçüm
     yoksa satırlar **sıfır** taşır). `report_evidence` bu yüzden `measured = True` diyordu; işaretler
     tam olunca `complete = True` oluyor, yani **B06 ölçümsüz kapanabiliyordu**. Testin 213.
     satırdaki varsayımı bu kusuru yakaladı.
- **DÜZELTME:** `eval/semread_001b_pilot.py` — tek kaynak `arms_with_measurement(payload)` (ölçüt:
  en az bir `scorable_target_count > 0`); `report_evidence.measured` artık
  `bool(aggregates) or bool(arms_with_measurement(...))`; `acceptance_rows` (B06) de aynı fonksiyonu
  kullanıyor (kopya ölçüt yok). Sonuç: ölçümsüz hâlde `measured=False` → `complete=False` → B06 açık.
- **YENİ PİN TESTİ:** `tests/test_semread_001b_acceptance.py::test_a_zero_row_vs_d_without_measurement_cannot_close_the_gate`
  — sıfır satırlı `vs_d` ölçüm sayılmaz; puanlanmış kol varsa `measured=True`.
- **KAPSAM:** yalnız rapor/ölçüm kapısı tanımı; prompt · şema · parser · run-contract · bütçe
  değişmedi. 001B lab'ı (`out/lab/semread-001b/**`) ve 001C lab'ı **yazılmadı** (test monkeypatch'li,
  `git status` yalnız bu iki dosyayı gösterir).
- **TEST EVIDENCE:** yeni pin + komşu kapı testi **2 passed** (0.28 s); etkilenebilecek hızlı SEMREAD
  süitleri (lifecycle/identity/gold-manifest/reference/`test_semread_001b`) yeniden koşuldu:
  **119 passed**; `check_tables` **21 satır / 0 tutmuyor**. Daha önce kırmızı olan testin **tek başına**
  yeniden koşusu harness tarafından 813 s'de öldürüldü (log 0 byte — kanıt üretmedi, "geçti" iddiası
  yok); yerine süiti tamamı koşuldu → **§1e: 27 passed**.
- **INFERENCE BUDGET:** 001D dev **0/12**, final **0/20** (toplam **0/32**) — değişmedi.
- **OPEN GATE:** §60#2 / §63 — run-contract `001d/1` + producer identity.
- **NEXT SINGLE STEP:** §10/§63 (değişmedi): run-contract `001d/1` kimliği + producer identity; §62'nin
  kanıt listesi bu düzeltmeyle birlikte "focused + gates + closure + D regresyonu" olarak eksiksiz.

---

## 1e. 001B acceptance süiti — düzeltme sonrası yeşil (0 inference) — 2026-10-05

- **CURRENT HEAD:** `0c0ecc4` (§1d düzeltmesi; bu kayıttan önce)
- **TEST EVIDENCE:** `tests/test_semread_001b_acceptance.py` tamamı **27 passed** (1908.28 s ≈ 31:48).
  Süit düzeltme öncesi **1 failed / 25 passed** vermişti; kırmızı olan test
  (`test_the_report_carries_every_required_section_on_the_real_payload`) artık yeşil: ölçümsüz hâlde
  `measured=False` → `complete=False` ve `bool(payload["aggregates"])` ile tutarlı. 27 = 26 mevcut
  test + §1d'de eklenen pin testi.
- **NOT:** §1d'de başlatılan **tek başına** yeniden koşu harness tarafından 813 s'de öldürüldü
  (exit -15, log 0 byte) ve kanıt üretmedi; yerine süiti tamamı koşuldu (yukarıdaki sayı). Ölçüm
  değişikliği yalnız rapor/kapı tanımında olduğu için prompt · şema · parser · run-contract kimliği ve
  001D bütçesi etkilenmedi.
- **INFERENCE BUDGET:** 001D dev **0/12**, final **0/20** (toplam **0/32**) — değişmedi; 0 inference.
- **OPEN GATE:** §60#2 / §63 — `semread-001d-run-contract/1` + producer identity.
- **NEXT SINGLE STEP:** §10/§63 (değişmedi): run-contract `001d/1` kimliği + producer identity; ardından
  §17–§22 dev rapor katmanı ve §23–§25 static preflight → Round 1 (4 çağrı).

---

## 1f. §60/§61 — run-contract `001d/1` + producer identity (0 inference) — 2026-10-05

- **CURRENT HEAD:** `7d9b0c7` (bu kayıttan önce; bu commit §60/§61 kimlik işini taşır)
- **CURRENT EXPERIMENT:** SEMREAD-001D. **Yeni plan entry izlendi:** `docs/PLAN-15.md` bayt kopya
  (sha256 `909e46cb67aac205b0e270861a364ad79e69eaa2a1b74aa8cf2a4d572109144e`; PLAN-15 §48: yeni
  history entry — PLAN-14 son izlenen revizyonuyla `39cf9b84…` (+ önceki `a027cb4a…`, `f2d249b7…`)
  geçmişte korunur; skeleton pin'i + yeni geçmiş-pin testi güncellendi). 001C **CLOSED / READ-ONLY** —
  closure `--verify` bu commit'te tekrar koşuldu: **45/45** (dokümanlar `recorded_at_git_head`
  blob'una çapalı olduğu için yaşayan report/handoff düzenlemeleri kapanış kaydını bozmaz).
- **IMMUTABLE HISTORY:** değişmedi — `docs/HERMES_SEMREAD_001C_HANDOFF.md`, `docs/PLAN-13.md`,
  `eval/semread_001b_gold/FREEZE.json`, `eval/semread_001c_closure.{py,json}`, `out/lab/semread-001c/**`.
- **WHAT CHANGED:** §60'ın tek somut işi (0 inference; yalnız saf fonksiyonlar + manifest kurulumu):
  1. **Kimlik (§9/§10):** `CONTRACT_VERSION = "semread-001d-run-contract/1"`; docstring current
     sözleşmeyi 001D anlatır (**semantic-content-aware full-page V/VE**), 001C tarihi closure
     artifact'ına işaret eder. **Üretim zarfı DEĞİŞMEDİ** — model `qwen3-vl:8b-instruct`, digest
     `0533d743…`, runtime `0.32.1`, num_ctx 22528 / num_predict 8192 / temperature 0.0 / paylaşımlı
     repeat_penalty 1.25 + repeat_last_n 512 / image_max_side 1280 / maxItems 32 (test: 001C kapanış
     kaydıyla birebir; V==VE invariantı korunur).
  2. **Attempt manifest kimlik alanları (§12):** `_attempt_manifest` artık açıkça `experiment`
     (=`semread-001d`), `schema_version` (`semread-candidates/3`), `reader_version`
     (`semread-candidate-reader/3`), `contract_version` (`001d/1`), `producer_identity`,
     `preprocessing_identity` taşır (mevcut alanlar korunur; attempt `schema` adı değişmedi).
     Producer bind listesi (contract + candidates/reader/schema/images/llama/inference_log) §12'yi
     kapsar: schema /3 · reader /3 · prompt v3 · semantic-empty parser · run-contract 001d/1.
  3. **Dry-run manifest (§13):** dört Round-1 hücresinin manifesti çağrısız kuruldu — hepsi
     experiment `semread-001d`, phase `dev`, schema/reader `/3`, contract `001d/1`; eski 001C kimliği
     manifeste girmiyor (test + log).
  4. **Gönderim bloğu (§13):** canlı gönderim öncesi kimlik denetimi (`contract_identity_block()`):
     aktif deney `semread-001d` için beklenen sözleşme tanımlıysa ve kurulu kimlik farklıysa gönderim
     `blocked_contract_identity` ile durur — attempt defterine yazılır, `send_attempted=false`, bütçe
     harcanmaz, kaynak/prompt hazırlığına girilmez; test `read_page`'in çağrılmadığını kanıtlar.
     Tanımsız deney adlarında (test/sandbox) beklenti yoktur.
  5. **Producer identity (§12):** `eedd96a878891c23…` (BEFORE/HEAD: `d21c9436b4448a02…`, temiz
     worktree'de ölçüldü); closure'da kayıtlı üç 001C kimliğinden (`52ed8c5e…`, `670da040…`,
     `dab89088…`) farklı (test). Yan etki (kayıtlı): `evaluation_identity` `96b7e66a…` →
     `d88f995a…` (pilot: manifest alanları + guard) ve `preprocessing_identity` `94edf558…`
     (değişmedi) — hepsi attempt manifestlerinde saklanır.
- **TEST EVIDENCE:** odak süiti (identity + skeleton + prompt_v3 + semantic_content + 001c closure +
  001c contract + dev-semantik + 001b closure) **101 passed**; hızlı SEMREAD süitleri (lifecycle +
  identity + gold-manifest + reference + `test_semread_001b`) **119 passed**; gates dosyası tamamı
  **34 passed (1027.95 s ≈ 17:07)** — koşu sonrası yalnız yorum/docstring düzenlemesi yapıldı
  (davranış değişmedi); 001C closure `--verify` **45/45**; `eval/check_tables.py` **21 satır / 0
  tutmuyor**. Yeni: `tests/test_semread_001d_identity.py` (8) + skeleton `test_plan14_history_is_preserved`.
- **§61 BÜTÇE/DRY-RUN KANITI (0 inference):** `--experiment semread-001d --budget` → dev 0/12 ·
  final 0/20 (toplam 0/32); `--matrix` → 30 hücre (20 vlm + 10 d), tümü `to_run` (yeniden kullanım
  yok, ledger yok); `--dry-run --phase dev` → `planned_real_calls 0` (001D corpus PNG'leri henüz yok —
  pre-live gate işi) · `remaining_phase_budget 12`; `out/lab/semread-001d` **kurulmadı**. Log:
  `~/.hermes/cache/scratch/semread-001d-identity-evidence.log`.
- **INFERENCE BUDGET:** 001D dev **0/12**, final **0/20** (toplam **0/32**) — değişmedi; bu commit
  **0 inference** (canlı çağrı yok, ledger kurulmadı).
- **OPEN GATE:** §62 — 001D dev rapor katmanı (§16–§23) + static preflight (§24–§28).
- **NEXT SINGLE STEP:** §16/§17: 001D dev-report aracı — yalnız `experiment = semread-001d` +
  current kimlikli attempt'ler; attempt yoksa `missing` (001B/001C fallback yok); formal (§18) +
  semantik (§19; `semantic_claim_flags` reuse) + echo v2 (§20) + duplicate (§21) metrikleri; gerçek
  ölçüm kapısı (§22) — sıfır-satır `vs_d` ölçüm sayılmaz.
