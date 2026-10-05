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
