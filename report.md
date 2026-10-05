# SEMREAD-001C — Faz Raporu

**Tarih:** 2026-10-05 · **Aktif plan:** `docs/PLAN-13.md` (PLAN_LATEST; bayt kopya, sha256 `cc61e0bc…`; PLAN-12 + kök PLAN.md history — §34)
**Durum:** §21 dev kapısı **8/8 GEÇTİ**; §37 semantik değerlendirme TAMAM (V/VE degenerate — §2b); **§35 #5 requalification KOŞULDU: §8 resmî kapı 7/8 (elbow-VE `schema_coordinate`) — paylaşımlı ayar 8/8 ✓, stop 8/8 ✓, içerik 0/8 (§2c)** · §7 gereği 001C final kararı kullanıcıda (handoff §1s).

---

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
| §35 #2–#4 | d08e8c3 · f9b417f · bu commit | Paylaşımlı zarf (ortak rp + `generation_settings` invariantı) · `maxItems=32` + kopya kuralı · dev tavanı 32 deklare (24/32) |

Ek tanı araçları: `eval/semread_001c_measure_prompts.py` (çağrısız prompt ölçümü),
`eval/semread_001c_probe_big.py` (`--ctx/--predict/--format/--repeat-penalty/--labeled/--dump`).

## 2. §21 dev kapısı — 8/8 GEÇTİ (24/24 canlı çağrı)

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
`valid_output_rate = 1.0`. Kanıt: `out/lab/semread-001c/dev-report.{json,md}` (araç: `eval/semread_001c_dev_report.py`).

**Attempt dağılımı (24):** pass 8 · truncated_output 5 · transport_error 2 · parse_error 1 ·
failed_gates 1 · sonuçsuz (kill/kuyruk) 7.

## 2b. §37 offline dev semantik değerlendirme — TAMAM (bulgu: parse-valid V/VE çıktısı degenerate)

**0 model çağrısı** (defter 24/24 sabit; final 0/20). Araç: `eval/semread_001c_dev_semantic_eval.py`
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

**Sonuç:** freeze'e bu çıktıyla geçilemez. Sıradaki iş: PLAN-13 §35 #5 — 8-hücre shared-envelope
requalification (#2–#4 tamam; bkz. §6).

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
§36'ya aykırı, önerilmez).

## 3. Zarf revizyonları (hepsi ölçümle)

| # | Değişiklik | Gerekçe (kanıt) |
|---|---|---|
| ilk | predict 2048 · ctx 12288 · case 600 | Plan başlangıcı; case tavanı lab settings'ten (600) geliyordu |
| 1 | predict → 4096/5120 | plate-VE 3072'de son item'ın ortasında kesildi |
| 2 | ctx 12288 → 20480 | flange-VE prompt'u **14.121 token** (ölçüm); 12288'de HTTP 400 |
| 3 | timeout MODEL 900 / CASE 1200 / RUN 14400 | plate-VE ilk denemede 300 s'de transport_timeout |
| 4 | ctx → **22528**, predict → **8192** | elbow-V 5120'de kesildi (≥40 aday); flange 14121+8192=22.313 ≤ 22.528 |
| 5 | MODEL 1800→**3000** / CASE 2400→**5400**; lab case tavanı 600→**7200** | İşler paralel; istekler ollama'da kuyruğa giriyor (aşağıda) |
| 6 | `repeat_penalty` kablolandı (llama.py) | VLM döngüsü (aşağıda) |
| 7 | Döngü kırıcı **kol başına: V=1.4 / VE=1.25**, pencere 512 | Prob taraması: 1.25 kırmadı · 1.6 susturdu (items:[]) · 1.4 durdu (150 tok); 1.4 ayrıca plate-VE'nin 41-adaylı zengin yanıtını 175 tokene kısıyor |

**Kilitli zarf:** predict 8192 · ctx 22528 · temperature 0.0 · repeat_last_n 512 ·
repeat_penalty V 1.4 / VE 1.25 · MODEL 3000 s < CASE 5400 s < RUN 14400 s.

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
4. **Şema↔parser ayrışması**: model cezadan kaçmak için `candidate_id: ""` üretti (şema izin verdi,
   parser reddetti → parse_error); sonra parser'ın kendi sentinelini taklit etti (`"<auto-generated>"`
   ×2 → yinelenen kimlik → refs düştü). → minLength + pattern; parser ve şema artık aynı sözü verir.
5. **Bellek/ön-ısıtma notu**: uzun oturumlarda llama-server şişiyor; `ollama stop` + taze yükleme
   ile temizlenir (kanıtlı: taze modelde format'lı büyük istek 74 s).

## 5. Bütçe tarihçesi (§20 sapmaları)

dev **10 → 12 → 16 → 18 → 20 → 22 → 24** (toplam 30 → **44**). 24/24 kullanıldı.
Sınıflar: platform kurbanı 5 (600 s tavanı) · operatör kill'i 4 (yanlış/erken kill — rapor
sorumluluğu kabul edilir) · zarf/kıyas redo'ları 8 · döngü+şema redo'ları 4 · ilk geçerli 3.
Her artış `state.json` notu + handoff §1i/§1l/§1n + test assertion'ı ile kayıtlıdır.

## 6. Kalan işler

- **PLAN-13 §35 #2–#4 TAMAM** (d08e8c3 / f9b417f / 85b3bdf); **#5 requalification KOŞULDU — §8 resmî
  kapı GEÇMEDİ (7/8: elbow-VE `schema_coordinate`); paylaşımlı ayar 8/8, stop 8/8, içerik 0/8 (§2c).**
  §7 gereği karar kullanıcıda: (a) plan yolu — 001C final yok, yeni experiment version planı;
  (b) tek-sapma redo (plan dışı, önerilmez). **Yeni çağrı yok; karar bekleniyor (handoff §1s).**
- **P7 (§23) — YENİ BAĞIMSIZ HOLDOUT: kullanıcı girdisi gerekli.** Repoda görülmemiş bir sayfa yok;
  final fazının kilitleneceği yeni çizim(ler) sağlanmalı. P8 (freeze) → P9/P10 (20 final çağrı +
  değerlendirme) buna bağlıdır.
- Final fazı zarfı: dev'de kilitlenen zarfın aynısı önerilir (freeze adımında yeniden onaylanır).

## 7. Kanıt yolları

- Defter: `out/lab/semread-001c/state.json` (24 çağrı, bütçe 24/24) · `attempts/` (24 attempt dizini,
  ham yanıt + kapı sonuçları + kaynak/istek manifestleri)
- Dev raporu: `out/lab/semread-001c/dev-report.{json,md}` · araç `eval/semread_001c_dev_report.py`
- Dev semantik raporu (§37): `out/lab/semread-001c/dev-semantic-report.{json,md}` · araç
  `eval/semread_001c_dev_semantic_eval.py` · testler `tests/test_semread_001c_dev_semantic_eval.py`
  (8 test; sıfır-inference ayrıca taze süreçte kanıtlanır)
- Prob kanıtları: `~/.hermes/cache/scratch/probe-*.log|json` (rp 1.4/1.6/1.3 taraması, etiketli
  üretim-birebir probe dahil)
- Koşu zincirleri: `~/.hermes/cache/scratch/semread-001c-batch*.log`
- Handoff: `docs/HERMES_SEMREAD_001C_HANDOFF.md` (§1a–§1p)
