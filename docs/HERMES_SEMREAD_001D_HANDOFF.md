# HERMES — SEMREAD-001D handoff günlüğü

**Plan:** `docs/PLAN-14.md` — SEMREAD-001D (semantic-content contract → dev proof → bağımsız
holdout → freeze → final). PLAN_LATEST olarak izlenir (bayt kopya, sha256
`f2d249b7bf14f4417c979f26903d70dd637bc110727e3f5369d765c0e9b2e2a4`); PLAN-13 + PLAN-12 + kök
PLAN.md history olarak korunur.
**Kayıt biçimi:** PLAN-12 §47 — *CURRENT HEAD / CURRENT EXPERIMENT / IMMUTABLE HISTORY / WHAT
CHANGED / TEST EVIDENCE / INFERENCE BUDGET / OPEN GATE / NEXT SINGLE STEP*.
**Kural:** 001C kaydı `docs/HERMES_SEMREAD_001C_HANDOFF.md` ve `out/lab/semread-001c/**`
**değiştirilmez** (001C READ-ONLY HISTORICAL; closure: `eval/semread_001c_closure.json` —
`--verify` 45/45). 001D işleri yalnız burada + PLAN-14 altında yürür; ledger'lar karıştırılmaz.

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
  **5/5**; 001C closure `--verify` **45/45**. Not: gates dosyasının tamamı (34 test) ayrı uzun
  koşuda — ağır BLAS/numpy ön-işlemeli test içeriyor; sonucu ayrıca işlenecek.
- **INFERENCE BUDGET:** 001D dev **0/12**, final **0/20** (toplam **0/32**); ledger
  `out/lab/semread-001d/` ilk dev çağrısında kurulur (§41#8). 001C bütçesine dokunulmadı
  (32/32 kapalı, READ-ONLY).
- **OPEN GATE:** §41#4 — semantic-content validator.
- **NEXT SINGLE STEP:** §41#4: §13 tanımıyla `semantic_content_count` ölçen deterministic
  validator (yalnız `source.region` taşıyan aday içeriksiz; gözlem-satırı kopyası da sayılmaz —
  §13/§20) + odak testler; şema/sözleşme v3 bu adımın devamıdır (§17–§22).
