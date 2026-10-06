# drawingto3d — durum raporu (yaşam belgesi)

**Tarih:** 2026-10-06 · **Aktif ürün yönü:** **guided transcription** (callout alanları → kullanıcı metni → deterministik parser → kullanıcı onayı → mevcut guided CAD yolu → STEP; ürün hedefi: 10 çizimde 10 geometrik doğru STEP — G10–G13) · **Aktif plan:** `docs/PLAN-20.md` · **İlerleme:** `docs/GUIDED_PROGRESS.md` · **Kapsam:** G0 + G1 (kabul; iki inceleme turu sonrası) + **G2 aktif** (Observations → deterministik CalloutCandidate)
**Park edilen araştırma:** SEMREAD-001D = **PARKED RESEARCH — Round 1 FAIL** (formal 0/4; dev bütçe **4/12** donduruldu; yeni requalification/001E/VLM ayarı yok) · eski planlar, attempt kayıtları, dev-report, preflight ve input identity kayıtları tarihsel kanıt olarak korunur.

---

## Aktif ürün yönü — guided transcription (current; 2026-10-06)

- **Pivot (PLAN-20 §2.1):** otomatik VLM okuması kritik yoldan çıkarıldı. Yeni akış: callout alanları → kullanıcı metni yazar/doğrular → deterministik parser → kullanıcı parse önizlemesini onaylar → sistem geometri hedefi önerir → kullanıcı hedefi onaylar → eksik fiziksel anlam/birim/eksen kararları tamamlanır → mevcut guided kararlar → GeneralPlan → CAD → STEP → STEP yeniden açılır + bağımsız geometri kontrolü.
- **Uygulama durumu:** G0 + G1 kabul edildi (iki bağımsız inceleme turu sonrası; callout veri sözleşmesi: dört model, kalıcılık ve eski oturum uyumu, revision, tazelik, undo, build stale). **G2 aktif:** `Observations → CalloutCandidate` deterministik adaptör (kök `PLAN.md`). **G3–G13 kapsam dışı**; kullanıcı faz açmadan başlanmaz.
- **Kayıtlar:** plan `docs/PLAN-20.md` (yeni history entry; `docs/PLAN-19.md` ve öncesi korunur) · ilerleme `docs/GUIDED_PROGRESS.md` (iş kalemleri + komut/exit-code/kanıt).
- **Çağrı disiplini:** bu pivotta yeni model çağrısı yok; SEMREAD dev bütçesi **4/12** · final **0/20** park kararıyla donduruldu.

## Park kaydı — SEMREAD-001D (PARKED RESEARCH — Round 1 FAIL; 2026-10-06)

- **Durum:** Round 1 dört canlı çağrıyla koşuldu → **FAIL (formal 0/4)**; ayrıntı aşağıdaki HISTORICAL bölümde.
- **Bütçe:** dev **4/12** · final **0/20** (toplam 4/32); yeni 001D requalification çağrısı yok, 001E yok, VLM prompt tuning / model değişimi / yeni OCR-VLM servisi kurulumu yok (PLAN-20 §2.3).
- **Korunan kanıt:** eski planlar (`docs/PLAN-19.md`, `PLAN-18.md`, …), attempts, raw responses, dev-report, preflight ve input identities kayıtları değiştirilmez; eski "sıradaki requalification" ifadeleri artık tarihseldir, aktif talimat değildir.

> **Aşağıdaki SEMREAD bölümleri (## 0 ve sonrası): HISTORICAL arşiv.** Aktif yönlendirme yukarıdaki iki bölümdür; bu kayıtlar silinmez ve değiştirilmez. Önceki izleme başlığı ve 001C durumu (o dönemin kaydı) alıntı olarak korunur:
> **Tarih:** 2026-10-06 · **Aktif deney:** SEMREAD-001D · **Aktif plan:** `docs/PLAN-19.md` (SEMREAD-001D; PLAN_LATEST; bayt kopya sha256 `d2148cb9…` — "Static preflight yeşil sonrası: Round 1 → offline semantic evaluation → tek karar noktası" planı; PLAN-19 §38: bu plan repo authority yapılacaksa `docs/PLAN-19.md` olarak **yeni history entry** ve **PLAN-18 overwrite edilmemeli** — öyle yapıldı; PLAN-18 **rewrite edilmedi**, son izlenen revizyonuyla `ec49e985…` geçmişte donar; PLAN-17 `1bdd4987…`; PLAN-16 `73f81009…`; PLAN-15 `909e46cb…`; PLAN-14 son izlenen revizyonuyla `39cf9b84…` (+ önceki `a027cb4a…`, `f2d249b7…`) geçmiş olarak korunur; PLAN-13 + PLAN-12 + kök PLAN.md history)
> **001C durumu (aşağıdaki 001C kaydı — HISTORICAL):** §21 dev kapısı **8/8 GEÇTİ**; §37 semantik değerlendirme TAMAM (V/VE degenerate — §2b); §35 #5 requalification **KOŞULDU: §8 resmî kapı 7/8 (elbow-VE `schema_coordinate`; paylaşımlı ayar 8/8 ✓, stop 8/8 ✓, içerik 0/8 — §2c)** · **KAPANIŞ (2026-10-05): 001C final yok — READ-ONLY kapandı (Kapanış); karar: yeni experiment version = SEMREAD-001D; closure snapshot: `eval/semread_001c_closure.json`; kayıt: handoff §1t.**

---

## 0. SEMREAD-001D dev kaydı (HISTORICAL — Round 1 FAIL ile park edildi)

- **Bütçe:** dev **0/12** · final **0/20** (toplam **0/32**) — PLAN-18 başlığı; artış yok; ledger
  (`out/lab/semread-001d/`) henüz kurulmadı (ilk dev çağrısında kurulur).
- **Kod (current):** `semread-candidates/3` · `semread-candidate-reader/3` ·
  **`semread-001d-run-contract/2`**. Şema/reader `/3` (§3/§61: semantic-empty geçersiz, semantic
  claim ≠ evidence-only, prompt semantic-first, no-guess korunur) ve **run-contract `001d/2` kimliği
  + yenilenmiş producer identity** yürürlükte (PLAN-15 §9–§15, 0 inference): docstring current'i
  001D anlatır; attempt manifesti experiment/schema_version/reader_version/producer/preprocessing
  kimliklerini açıkça taşır (§12); dry-run manifesti 4 Round-1 hücresinde current kimlik verir
  (§13); eski kimlikle gönderim `blocked_contract_identity` ile durur. **Üretim zarfı:** tek sapma
  ölçümlü `num_ctx` revizyonudur — 22.528 → **24.576** (`/1` → `/2`, aşağıdaki R1 bullet'ı);
  model/digest/runtime ve diğer ayarlar 001C kapanışından devralındı (§10).
- **§94/§95 tamam (current): 001D dev rapor katmanı** (0 inference) —
  `eval/semread_001d_dev_report.py` + `tests/test_semread_001d_dev_report.py` (23 test): yalnız
  current kimlikli 001D attempt'leri seçilir (experiment / `/3` / `/3` / `001d/2` + producer
  identity); eski 001B/001C attempt'e fallback **yok** — attempt yoksa hücre `missing`, ölçüm ve
  semantik-valid `false`. Hücre başına formal (§16) + semantik (§17; `semantic_claim_flags` reuse)
  + dondurulmuş gold (§18; FREEZE sha fail-closed) + **gerçek ölçüm kapısı** (§19; sıfır-satır
  `vs_d` ölçüm değildir) + `semantic_valid_output` (§21) + echo v2 (§23) + kopya (§24) + maxItems
  (§25) + overclaim (§26); Round 1/2 kapıları (§57/§72). Araç salt-okur: defter kurmaz/yazmaz;
  `--write` yalnız `dev-report.{json,md}` yazar (§27).
- **§31–§41 tamam (current): 001D dev girdi kurulumu + raw-page kimliği** (0 inference) —
  `eval/semread_001d_inputs.py` + `tests/test_semread_001d_inputs.py` (14 test): dört dev sayfanın
  prepared PNG'si kaynaktan türetilir (§33/§34 — kör kopya yok; 001B/001C ile byte-eşitlik hash'le
  kanıtlanır), `corpus/input-identity.json` sayfa başına source/prepared sha256 + width/height +
  page index/rotasyon + `input_identity` + preprocessing kimliğini kaydeder (§35); V/VE ham sayfa
  byte'ı aynı, VE overlay'i + gözlem tablosu ayrı hash'li (§36/§37); araç gold okumaz (yalnız
  kaynak + deterministik gözlem) ve gönderim yapmaz; `--check` salt-okur yeniden türetimle
  doğrular (§40 — çelişkide veya kaynak yoksa hiçbir şey yazılmaz); frozen sayfalar kurulmaz
  (§32/§82).
- **§41 dry-run kanıtı (current):** `--dry-run --phase dev` Round 1 için `planned_real_calls 4`
  (dört hücre `call`); bütçe dev **0/12** · final **0/20**; ledger kurulmadı.
- **§32–§41 statik preflight (current; 0 inference):** `eval/semread_001d_preflight.py` (+13 test) —
  on kapı tek koşuda: kimlik / dry-run (`planned_real_calls 4`) / bütçe (`0/12`·`0/20`) / runtime
  (`0.32.1` + digest birebir; yerel metadata) / paylaşımlı ayar / istek `options` imzası /
  structured-output (`format` json-schema; `anyOf` yok; gövde kurulur, gönderilmez) / girdi
  güncelliği (prepared-input cache == yeniden türetim; V/VE ham byte aynı; VE kanıtı ayrı hash) /
  001C closure **45/45**. §37 ölçümü (model çağrılmadan; kalibrasyon 0.816 tok/byte + 664):
  plate-pocket V 3.364 B→**3.409** · VE 7.574 B→**6.844** · flange-book V 3.364 B→**3.409** ·
  **flange-book VE 17.868 B→15.244**.
- **R1 bloğu → pre-inference ölçümlü revizyon `/1` → `/2` (current):** preflight `/1`e karşı
  KIRMIZI verdi — `dev-flange-book-VE` → `15.244 + 8.192 = 23.436 > 22.528` (§49 kanıtı: gerekli
  **23.436** · mevcut **22.528** · **eksik 908**; kırmızı kayıtlar scratch'te tarihsel:
  `...contract-1-red.json` + `...contract-2-stale-inputs-red.json`). Karar: kör artış değil (§39)
  **kanıtlı sözleşme revizyonu** — `num_ctx` 22.528 → **24.576**, `CONTRACT_VERSION`
  `semread-001d-run-contract/2`, producer identity yenilendi; diğer üretim ayarları değişmedi;
  revizyon **ilk canlı çağrıdan önce** yapıldı (0 attempt → geçersizleşen veri yok). Preflight
  `/2` ile **10/10 yeşil**: flange-book-VE headroom **+1.140** (diğerleri +9.540/+12.975/+12.975);
  dört hücre `call`; `planned_real_calls 4`. Revizyon girdi katmanını da bilinçli yeniledi:
  producer-bound cache geçersizleşti (preflight `inputs_current` KIRMIZI yakaladı) →
  `eval/semread_001d_inputs.py --write` yeniden kurdu (sayfa PNGleri byte-kararlı, 0 yeni yazım) →
  salt-okur `--check` **ok** (4 sayfa, 0 problem; 001B/001C byte cross-check aynı). Kayıtlar:
  `corpus/static-preflight.json` (`ok=true`), `corpus/input-identity.json` (`/2`).
- **Tamamlanan:** skeleton (PLAN-14 izleme + bütçe deklare + gates 34/34) → **§47 ilk uygulama
  adımı: semantik-içerik sözleşmesi (0 inference)** — tek kaynak `semantic_claim_flags` /
  `candidate_has_semantic_claim` / `evidence_flags`; wire sınırında `schema_semantic_empty` reddi
  (§3/§5/§8/§9); D yolu audit'i (§6 — D doğrudan `Candidate` kurar, wire parser'a girmez) →
  **§61: schema/reader `/3` + prompt v3** (0 inference) — ortak V/VE görevi semantic-first
  (§6/§7), no-guess anti-pressure (§8), VE kanıt bölümünde satır-başına-aday yasağı (§9), şema item
  açıklaması aynı asgari sözleşmeyi söyler (§4; `anyOf` **eklenmedi** — §5) → acceptance
  ölçüm-kapısı düzeltmesi (§5/§6) → **§60/§61: run-contract `001d/1` + producer identity**
  (0 inference; §9–§15).
- **ROUND 1 KOŞULDU (2026-10-06, dört canlı çağrı; PLAN-19 §48) — SONUÇ: FAIL (formal 0/4).**
  Dört hücre de gönderildi (`send_state sent`, sıralı, retry yok), bütçe dev **4/12** · final **0/20**
  (toplam 4/32); attempt defteri 4 attempt / hepsi `parse_error`; dördünde de `done_reason stop`,
  kesilme yok, sızıntı yok, metadata tam. Ortak arıza biçimi: model **yalnız bölge iskeleti**
  üretiyor (`source.region` + `callout_region` + `target.state:"unknown"`), **hiçbir adayda semantik
  alan yok** (dört yanıtın tamamında anlamlı alan sayısı **0**). Ayrıntı: `dev-plate-pocket-V`
  `schema_semantic_empty` (2 aday, tek bölge; 84.8 s) · `dev-plate-pocket-VE`
  `schema_semantic_empty` (**32 aday = maxItems tavanı**, 32 farklı bölge; 704.6 s) ·
  `dev-flange-book-V` `schema_coordinate` (32 aday; aday 17 bölgesi `y1 = 1.0311 > 1`; 737.2 s) ·
  `dev-flange-book-VE` `schema_semantic_empty` (25 aday, 20 farklı bölge; 676.8 s). Ölçülen prompt
  token'ları tahminin **altında** kaldı (1963 / 6034 / 2083 / **14.427** vs tahmin 3409 / 6844 /
  3409 / 15.244) → context zarfı yetti (§4 headroom kanıtı canlı koşuda doğrulandı). V/VE ham görüntü
  byte'ı canlı koşuda da aynı (`794fdedc…`) ve VE kanıt görüntüsü ayrı hash'li. Dev raporu (§15,
  0 inference): `out/lab/semread-001d/dev-report.{json,md}` — `complete: HAYIR`, eligible 4/8,
  ölçülü 0, semantic-valid 0, `round_1` kapısı **AÇIK** (6 açık koşul).
- **(HISTORICAL — PLAN-20 park kararıyla geçersiz; yeni çağrı yetkisi yok.) Sıradaki (§29–§33 / §42):** Round 1 FAIL → offline forensic tanı **yapıldı** (yukarıdaki arıza
  biçimi; yeni çağrı yok); §30/§31 gereği en fazla **tek deklare jenerik sözleşme revizyonu** + aynı
  dört hücrenin requalification'ı (4 dev çağrı; kalan dev bütçesi 8/12). Karar noktası operatörde
  (sözleşme/prompt revizyonu); ikinci FAIL olursa §33: 001D kapanır, Round 2 yok, yeni deney 001E.
- **Test kanıtı (current, `/2`):** odak **155** · hızlı **119** · gates **34/34** (1015.27 s) ·
  001C closure `--verify` **45/45** · check_tables **21/0**; hepsi 0 inference koşumlar (P4
  ön-gönderim kapısı tamam; preflight `/2` PLAN-19 yetkisiyle **10/10 yeşil**).
- **Bonus koşu bulgusu (0 inference, §1d/§1e):** 001B acceptance süiti ölçümsüz kapanabilen bir rapor
  kapısı gösterdi (`report_evidence.measured` sıfır satırlı `vs_d`'yi ölçüm sayıyordu) — tek kaynak
  `arms_with_measurement()` ile düzeltildi + pin testi; süit tamamı **27 passed** (31:48).
- **External CI/status:** yok — kabul kanıtı yerel pytest + `eval/` araçlarıdır (PLAN-18 §5).

---

> **Aşağıdaki §1–§7 + Kapanış bölümü: SEMREAD-001C faz kaydı (HISTORICAL).** 001C READ-ONLY
> (closure `--verify` 45/45: `eval/semread_001c_closure.json`); kapanış kaydı sonraki sürüm
> düzenlemelerinden etkilenmez (yaşayan report/handoff ayrımı).

## 1. Ne yapıldı (P0–P6 + araçlar)

| İş | Commit | İçerik |
|---|---|---|
| A | dc3ade0 | PLAN-12.md repoya (workspace dışı dosyanın kopyası) |
| P0 | f5b34b1 | 001B closure aracı + test (9/9 birebir doğrulama) |
| P1 | 1a54b4c | Bölge sözleşmesi v2: tek tanım, 0..1 normalize, parser dışını reddeder |
| P2 | 12f8527 | `provenance` model wire'ından çıktı; harness enjekte eder |
| P3 | e039ae1 | `raw_observation_rows`; gözlem tablosu sıkıştırması yalnız serileştirmeye |
| P4 | ae91dc6 | `truncated_output` birinci sınıf; parse alt türleri `kind` |
| P5/P6 | fa7b6a3 | `semread-001c-run-contract/1`; kabul: stop + eval ≤ 0.8×predict; ayrı defter |
| araç | 6555e62 | `eval/semread_001c_dev_report.py` (§21 kapısı + §19/§43 ölçüm) |
| kapanış | 1f5977a | report.md + handoff §1o |
| §37 | 21e0691 | Offline dev semantik değerlendirme (0 inference) + D kolu (4 sayfa) + PLAN-13 izlendi |
| §35 #2–#4 | d08e8c3 · f9b417f · 85b3bdf | Paylaşımlı zarf (ortak rp + `generation_settings` invariantı) · `maxItems=32` + kopya kuralı · dev tavanı 32 deklare (o an 24/32; kapanış 32/32 — §5) |

Ek tanı araçları: `eval/semread_001c_measure_prompts.py` (çağrısız prompt ölçümü),
`eval/semread_001c_probe_big.py` (`--ctx/--predict/--format/--repeat-penalty/--labeled/--dump`).

## 2. §21 dev kapısı — 8/8 GEÇTİ (HISTORICAL kapı fazı: 24/24 çağrı; güncel defter 32/32 — §2c)

| hücre | geçerli | parse | refs | stop | koord. | sızıntı | attempt | aday |
|---|---|---|---|---|---|---|---|---|
| dev-plate-pocket-V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | attempt-0001 | 2 |
| dev-plate-pocket-VE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | attempt-0006 | 41 |
| dev-flange-book-V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | attempt-0002 | 1 |
| dev-flange-book-VE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | attempt-0004 | 1 |
| dev-flange-elbow-V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | attempt-0007 | 1 |
| dev-flange-elbow-VE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | attempt-0003 | 1 |
| dev-drawing-2-V | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | attempt-0001 | 2 |
| dev-drawing-2-VE | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | attempt-0001 | 2 |

**Kapı:** GEÇTİ — V 4/4, VE 4/4, stop=True, koordinat=True, refs=True, sızıntı=True.
`valid_output_rate = 1.0`. Kanıt: `out/lab/semread-001c/dev-report.{json,md}` (araç:
`eval/semread_001c_dev_report.py`; **kapanışta tazelendi** — dosyalar artık "en yeni pass" seçimini
gösterir, §2c; bu bölümdeki tablo kapı fazının 24-çağrı seçimidir — HISTORICAL).

**Attempt dağılımı (24, kapı fazı):** pass 8 · truncated_output 5 · transport_error 2 · parse_error 1 ·
failed_gates 1 · sonuçsuz (kill/kuyruk) 7. (Güncel defter: 37 attempt dizini — §7.)

## 2b. §37 offline dev semantik değerlendirme — TAMAM (HISTORICAL veri: §37 anı; bulgu: parse-valid V/VE çıktısı degenerate — requal sonrası da sürüyor, §2c)

**0 model çağrısı** (o an defter 24/24; kapanışta 32/32 — §2c; final 0/20). Araç: `eval/semread_001c_dev_semantic_eval.py`
(salt-okur; dondurulmuş gold FREEZE hash denetimli; D/V/VE **aynı** `semantic_evaluation` yolu; VLM
zincirini import etmez). Çıktı: `out/lab/semread-001c/dev-semantic-report.{json,md}`. Testler:
`tests/test_semread_001c_dev_semantic_eval.py`.

D kolu bu değerlendirme için 4 dev sayfada deterministic koşuldu (0 inference): plate-pocket 7 ·
flange-book 12 (attempt-0002; 0001 = kesilen yerel koşudan orfan, result.json'sız, defterde kayıt
değil) · elbow 17 · drawing-2 17 — 001B D adetleriyle birebir aynı (7/12/17/17). Bütçe değişmedi.

| ölçüm | D | V | VE |
|---|---|---|---|
| aday | 53 | 6 | 45 |
| içerik taşıyan aday | **53** | **0** | **0** |
| gold eşleşen | 2 | 1 | 3 |
| yerelleştirme | 9.1% | 4.5% | 13.6% |
| alan doğruluğu (eşleşenlerde) | 66.7% | 0% | 0% |
| abstention | 33.3% | 100% | 100% |
| FP / unscorable | 9 / 42 | 0 / 5 | 0 / 42 |

1. **Parse-valid ≠ içerikli:** seçili 8 V/VE hücresinin **51 adayının 0'ı** semantik alan taşıyor
   (yalnız `source.region` kutusu; callout/temsil/ölçü/bitiş/hedef hepsi boş). `valid_output_rate=1.0`
   yalnız biçimsel geçerlilikti; içerik ölçümü bu raporda ilk kez yapıldı.
2. **VE = gözlem-tablosu yankısı:** 45/45 VE adayı prompt'taki gözlem satırlarının birebir kutusu
   (plate-VE 41/41; 21'i metin satırı). Model okuma üretmiyor, tabloyu kopyalıyor.
3. **Kesik flood'lar da içeriksiz:** elbow-V'nin kesilen denemeleri (40/64/30 öğe) sıfır semantik
   içerikli → "aşırı bastırma gerçek içeriği kesti" okuması veriyle desteklenmiyor (§28).
4. **plate-VE 41 aday:** 0 eşleşme, 41 unscorable (kapsam dışı), 4 yakın kopya, 41/41 yankı (§27).

**Sonuç:** freeze'e bu çıktıyla geçilemez (§37 anı). Sıradaki iş o an: PLAN-13 §35 #5 — 8-hücre
shared-envelope requalification (#2–#4 tamam; koşuldu → §2c).

## 2c. §35 #5 shared-envelope requalification — SONUÇ (2026-10-05 12:00–15:00)

8 çağrı (4 dev sayfa × V/VE), paylaşımlı zarf (rp 1.25 + rln 512 + ctx 22528 + predict 8192 +
`maxItems=32` + anti-loop metin). Bütçe 24→32 — **hepsi kullanıldı (32/32)**; elle kill yok.

| hücre | attempt | sonuç | aday | içerikli | kopya | yankı |
|---|---|---|---|---|---|---|
| plate-pocket-V | 0002 | pass | 2 | 0 | 1 | — |
| plate-pocket-VE | 0007 | pass | 32 | 0 | 3 | 32 |
| flange-book-V | 0003 | pass | 32 | 0 | 6 | — |
| flange-book-VE | 0005 | pass | 32 | 0 | 15 | 32 |
| flange-elbow-V | 0008 | pass | 32 | 0 | 28 | — |
| flange-elbow-VE | 0004 | **parse_error** | 32 | — | — | — |
| drawing-2-V | 0002 | pass | 2 | 0 | 1 | — |
| drawing-2-VE | 0002 | pass | 32 | 0 | 16 | 32 |

**§8 kapısı:** `valid_result` **7/8 ✗** · `stop` 8/8 ✓ · coordinate 7/8 ✗ · refs 7/8 ✗ · sızıntı
temiz 8/8 ✓ · **paylaşımlı ayar 8/8 ✓** (tek imza — V dahil rp 1.25). Elbow-VE/0004: 32 adayın
1'inde tek normalize ihlali (`c32.callout_region.y1 = 1.05`) → katı bölge sözleşmesi reddetti
(`schema_coordinate`); model ihlali, sessiz tamir yasak.

**Ne sağlandı:** paylaşımlı zarfta V==VE 8/8; stop 8/8; adaylar ≤32 (truncation yok — elbow-V'nin
bitmeyen döngüsü bitti: eski 64/30-aday kesintileri yerine 32'de `stop`).
**Ne sağlanmadı:** içerik hâlâ **0/8** (degenerate sürüyor; VE 32/32 gözlem-tablo yankısı, elbow-V'de
28 birebir kopya); resmî kapı **7/8**.

**Sonuç (PLAN-13 §7 birebir):** "32 sonrası geçmezse: 001C final yok; yeni experiment version.
Call-call bütçe artırma yok." → **001C bu haliyle final fazına geçemez**; retry/redo §36 gereği yasak.
Karar kullanıcıya sunuldu (handoff §1s: (a) plan yolu = yeni experiment version, (b) tek-sapma redo —
§36'ya aykırı, önerilmez). → **Kapanış: karar (a) uygulandı — 001C final yok, yeni experiment
version = SEMREAD-001D; bu bölümden sonra 0 canlı çağrı (Kapanış).**

## 3. Zarf revizyonları — HISTORICAL gelişim (hepsi ölçümle; kapanış zarfı altta)

| # | Değişiklik | Gerekçe (kanıt) |
|---|---|---|
| ilk | predict 2048 · ctx 12288 · case 600 | Plan başlangıcı; case tavanı lab settings'ten (600) geliyordu |
| 1 | predict → 4096/5120 | plate-VE 3072'de son item'ın ortasında kesildi |
| 2 | ctx 12288 → 20480 | flange-VE prompt'u **14.121 token** (ölçüm); 12288'de HTTP 400 |
| 3 | timeout MODEL 900 / CASE 1200 / RUN 14400 | plate-VE ilk denemede 300 s'de transport_timeout |
| 4 | ctx → **22528**, predict → **8192** | elbow-V 5120'de kesildi (≥40 aday); flange 14121+8192=22.313 ≤ 22.528 |
| 5 | MODEL 1800→**3000** / CASE 2400→**5400**; lab case tavanı 600→**7200** | İşler paralel; istekler ollama'da kuyruğa giriyor (aşağıda) |
| 6 | `repeat_penalty` kablolandı (llama.py) | VLM döngüsü (aşağıda) |
| 7 | Döngü kırıcı **kol başına: V=1.4 / VE=1.25**, pencere 512 | Prob taraması: 1.25 kırmadı · 1.6 susturdu (items:[]) · 1.4 durdu (150 tok); 1.4 ayrıca plate-VE'nin 41-adaylı zengin yanıtını 175 tokene kısıyor (kol-başına seçim HISTORICAL; paylaşımlı zarfa §35 #2'de geçildi) |

**HISTORICAL envelope evolution:** yukarıdaki 7 revizyon ölçüm gerekçeleriyle tarihsel gelişimdir;
döngü kırıcı önce kol başına seçilmişti (**V 1.4 / VE 1.25** — HISTORICAL).

**CURRENT 001C closure envelope (FINAL):** `num_predict` **8192** · `num_ctx` **22528** ·
`temperature` **0.0** · `repeat_last_n` **512** · `repeat_penalty` **1.25** (**paylaşımlı:
V == VE**) · `maxItems = 32` + kopya kuralı · MODEL 3000 s < CASE 5400 s < RUN 14400 s
(lab case tavanı 7200 s). Paylaşımlı-ayar requalification'ı bu zarfla koşuldu (§2c; 8/8 tek imza).
Sabitlerin tek kaynağı: `src/drawingto3d/semantic_run_contract.py`
(`generation_settings(V) == generation_settings(VE)`).

Ayrıca şema sertleştirmesi (model çıktısını doğrudan etkiler): `candidate_id` →
`minLength:1` + `pattern ^[A-Za-z0-9][A-Za-z0-9_.-]*$` (parser'ın reddettiğini şema da yasaklar).

## 4. Platform/model kök nedenleri (teşhis → düzeltme)

1. **LabRunner 600 s tavanı** (out/lab/settings.json): her iş sessizce 600 s'de SIGKILL ediliyordu —
   "kama" sanılan olayların bir kısmı buydu (plate-VE-0003/0005, flange-VE-0002/0003 sonuçsuz öldü).
   → tavan 7200, istekler MODEL/CASE ile hiyerarşik.
2. **Ollama kuyruğu**: öldürülen isteğin üretimi SUNUCUDA devam eder; sonraki istek sırada bekler —
   "kama" görünen beklemelerin asıl nedeni buydu (probe: ölü istek ardından 16 dk sessizlik).
   → Kural: bekleyen işi elle öldürme; kuyruk kendiliğinden boşalır.
3. **VLM tekrar döngüsü** (asıl zorluk): yoğun çizimde (flange-elbow) V kolu aynı adayı **64 kez**
   üretip 5120'de kesildi; 8192'de de 30 özdeş adayla tekrarladı. Varsayılan ceza penceresi (64)
   ~230–580 token'lık item'ı görmediği için hiç ateşlemiyordu. → `repeat_penalty/repeat_last_n`
   kablolandı; kol-başına değerler prob taramasıyla seçildi (1.25 kırmadı / 1.6 susturdu / 1.4 durdu).
   Kol-başına seçim HISTORICAL'dır; kapanış zarfında ceza paylaşımlı **1.25 + rln 512** (§3).
4. **Şema↔parser ayrışması**: model cezadan kaçmak için `candidate_id: ""` üretti (şema izin verdi,
   parser reddetti → parse_error); sonra parser'ın kendi sentinelini taklit etti (`"<auto-generated>"`
   ×2 → yinelenen kimlik → refs düştü). → minLength + pattern; parser ve şema artık aynı sözü verir.
5. **Bellek/ön-ısıtma notu**: uzun oturumlarda llama-server şişiyor; `ollama stop` + taze yükleme
   ile temizlenir (kanıtlı: taze modelde format'lı büyük istek 74 s).

## 5. Bütçe tarihçesi (§20 sapmaları)

dev **10 → 12 → 16 → 18 → 20 → 22 → 24 → 32** (toplam 30 → 44 → **52**). Closure: **dev 32/32
kullanıldı; final 0/20** (kullanılmadı).
Sınıflar (ilk 24'ün): platform kurbanı 5 (600 s tavanı) · operatör kill'i 4 (yanlış/erken kill —
rapor sorumluluğu kabul edilir) · zarf/kıyas redo'ları 8 · döngü+şema redo'ları 4 · ilk geçerli 3;
\+ **8 requalification çağrısı** (§35 #5; paylaşımlı zarf doğrulaması — #25–#32) = **32**.
Her artış `state.json` notu + handoff §1i/§1l/§1n/§1o/§1q + test assertion'ı ile kayıtlıdır
(son tavan #6: §1q; requalification sonucu: §1s).

## 6. Kalan işler

- **PLAN-13 §35 #2–#4 TAMAM** (d08e8c3 / f9b417f / 85b3bdf); **#5 requalification KOŞULDU — §8 resmî
  kapı GEÇMEDİ (7/8: elbow-VE `schema_coordinate`); paylaşımlı ayar 8/8, stop 8/8, içerik 0/8 (§2c).**
  §7 gereği **001C final yok**; karar (a) uygulandı: **yeni experiment version = SEMREAD-001D**
  (kullanıcı planı; 001D skeleton'ı sıradaki commit'lerde). **001C bundan sonra READ-ONLY; yeni çağrı
  yok** (bütçe 32/32 kapandı; retry/redo §36 gereği yasak).
- **P7 (bağımsız holdout) 001D'ye taşındı** — 001D planı holdout intake/selection'ı kapsar
  (PLAN_SEMREAD_001D §30–§33). 001C'de final koşusu yapılmayacak.
- Sıra (PLAN_SEMREAD_001D §41–§43): closure snapshot (bu kayıtla) → 001D skeleton → semantic-content
  contract → dev proof → holdout → freeze → final.

## 7. Kanıt yolları

- Defter: `out/lab/semread-001c/state.json` (**32 canlı çağrı; dev 32/32 · final 0/20**;
  requalification #25–#32) · `attempts/` (**37 attempt dizini**: 32 canlı + 4 D + 1 D-orphan
  [result.json'sız, defterde kayıt değil — §2b]; ham yanıt + kapı sonuçları + kaynak/istek
  manifestleri)
- Dev raporu: `out/lab/semread-001c/dev-report.{json,md}` — **kapanışta tazelendi** (0 inference,
  salt-okur; "en yeni pass" seçimi; bütçe satırı dev 32/32) · araç `eval/semread_001c_dev_report.py`
- Dev semantik raporu (§37): `out/lab/semread-001c/dev-semantic-report.{json,md}` —
  **requalification sonrası tazelendi** (§2c seçili attempt'leri) · araç
  `eval/semread_001c_dev_semantic_eval.py` · testler `tests/test_semread_001c_dev_semantic_eval.py`
  (8 test; sıfır-inference ayrıca taze süreçte kanıtlanır)
- **Kapanış snapshot'ı:** `eval/semread_001c_closure.json` (+ `eval/semread_001c_closure.py`,
  `tests/test_semread_001c_closure.py`) — izlenen doküman/defter/rapor/attempt hash'leri + kimlikler;
  `--verify` ile denetlenir (Kapanış)
- Prob kanıtları (repo dışı): `~/.hermes/cache/scratch/probe-*.log|json` (rp 1.4/1.6/1.3 taraması,
  etiketli üretim-birebir probe dahil)
- Koşu zincirleri (repo dışı): `~/.hermes/cache/scratch/semread-001c-batch*.log` ·
  `semread-001c-elbowV-final*.log` · `semread-001c-requal.log` (§1r/§1s)
- Handoff: `docs/HERMES_SEMREAD_001C_HANDOFF.md` (§1a–§1t; kapanış kaydı §1t)

---

## Kapanış — 001C READ-ONLY ilanı (2026-10-05)

- **Karar (PLAN-13 §7 birebir):** dev bütçesi 32/32 dolu ve §8 resmî kapısı geçilmedi → **001C
  final fazına geçmez**; call-call bütçe artırma yok. Karar (a) uygulandı: **yeni experiment
  version = SEMREAD-001D** (kullanıcı planı).
- **Closure hijyeni (0 inference; izlenen dosyalarda docs-only):** report zarf/bütçe/kanıt satırları
  historical/current ayrımıyla güncellendi (§3/§5/§7); `semantic_run_contract.py` docstring'i iki
  katmana ayrıldı (P0.5 — sabitler ve davranış değişmedi; dosya byte'ı değiştiği için
  `producer_identity()` recompute'u run-time değerinden mekanik sapar, snapshot ikisini de kaydeder);
  `dev-report` ve `dev-semantic-report` tazelendi; handoff §1t.
- **Closure snapshot:** `eval/semread_001c_closure.json` (`--write`/`--verify`) — izlenen doküman +
  defter + rapor + 12 seçili attempt hash'leri, kimlikler (producer/evaluation/run-contract) ve
  bütçe/requalification özeti; kapanış HEAD'ini pinler.
- **Read-only ilanı:** 001C attempt/bütçe/ledger artifact'ları bundan sonra **değiştirilmez**
  (rewrite yasak — PLAN_SEMREAD_001D §9); bir düzeltme gerekirse yeni sürümde (001D) yapılır.
  Kanıt zinciri `--verify` ile (temiz klonda `out/` eksikleri açıkça raporlanarak) denetlenir.
