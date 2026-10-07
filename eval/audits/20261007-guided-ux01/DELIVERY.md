# UX-01 — DELIVERY (kabul, 2026-10-07)

**Sonuç: UX-01 PASS.** Gerçek Chrome kabulü: **35/35 adım** (koşu 04; 0 console error, 0 reddedilen istek).
Bu dosya, kullanıcının `UX_PLAN.md` §28 DONE listesinin her satırını kanıta bağlar.

## Sıra (korundu)

G10 manifesti sonuç görülmeden donduruldu ve commit edildi (`3cdeb5f`) → **UX-01** (bu tur) → resmî
G11 10-pafta koşusu (§29; **henüz başlamadı**). UX-01 öncesi yürütülen G11 *pilot* kayıtları (7/10,
sürücü doğrulaması) ayrıdır; resmî koşu UX-01 sonrası koduyla, dondurulmuş manifestle sıfırdan yapılır.

## Ürün değişikliği

| Commit | İçerik |
|---|---|
| `430aa8f` | Backend: atomik `bulk_set_ignored` (tek revizyon/history/undo/audit; all-or-nothing). UI: „Sonraki eksik“ + oto-ilerleme, çoklu seçim + bulk bar, üçlü ipucu, „Eksik kalanlar“ checklist + navigasyon, teknik detay collapse, kullanıcı dili |
| `3ff97ed` | Kabul sürücüsü + koşu kanıtları; `rowResolved` otoriter parse satırından; oto-ilerleme yalnız çözülen satırda; G11 runner yeni bulk akışı |

## Kabul koşuları (loglar `logs/`)

| Koşu | Sonuç | Not |
|---|---|---|
| 01 | durdu | sürücü hatası: `click_selector` yalnız id alır (bileşik seçici) |
| 02 | 1 FAIL + durdu | **gerçek ürün bulgusu**: oto-ilerleme, satır çözülmemişken de zıplıyordu → `if(!rowResolved(previousId))return;` |
| 03 | 34 PASS / 1 FAIL | test-tarafı: public payload `history` taşımaz (kanıt zaten tek-undo adımı) |
| 04 | **35/35 PASS** | temiz kabul; token `4d1c43eaa5d1431baa4e40a9293eb087` |

## §16–§21 senaryo eşlemesi

- **§16 tek tık**: adım 4–8 (soru görünür; seçim/panel/reload yazmaz; tek tık sunucu-doğrulamalı yazar; çözülmeden ilerlemez; çözülünce ilerler)
- **§17 düzelt**: adım 9–12 (draft sunucuya gitmez; „Kaydet“ sonrası birebir kalıcı; kapsam kararı çözünce ilerler)
- **§18 bulk**: adım 13–17 (satır başına checkbox; tıklamalar yazmaz; tek eylem 6 satır → +1 revizyon / 1 audit / 1 istek; tek undo hepsi; reload kalıcı)
- **§19 checklist**: adım 18–21, 30 (sayılar backend satırlarıyla birebir; „Ölçü/not“ ilk çözülmemişe odaklar; „Dış şekli seç“ konturu odaklar; hazır olmadan hazır demez)
- **§20 sessiz karar yok**: adım 3 (tüm gezinme/toggle çiftleri yazmaz), 5, 10, 14, 24 (öneri vurgusu yazmaz), 20
- **§21 smoke**: adım 31–33 (build complete; dondurulmuş değerlendirici **verdict pass**; bbox [15, 80.002, 120.011] G9/g11 kaydıyla ≤0.02 mm; 1 katı / 16 yüz / aynı silindirler; STEP sha farkı yalnız dosya başlığı damgası)

## §23 metrikler (`ux01-metrics.json`)

| Metrik | G9 (UX turu öncesi) | UX-01 koşusu |
|---|---|---|
| elle yazılan metin | 4 | 4 (aynı 4 callout; hole+pocket dahil toplam iş aynı) |
| tek-tık ipucu kabulü | 4 | 4 |
| tek-satır kapsam dışı | 1 | 1 |
| toplu kapsam dışı | 36 satır / 1 eylem | 42 satır / 3 eylem* |
| elle hedef düzeltmesi | 1 | 1 |

\* Koşu §18'i bilinçli olarak üç kez egzersiz eder (uygula → **undo** → yeniden uygula → reload); iş akışı
düzeyinde 45'lik kuyruk tek toplu eylemdir (adım 29: kalan 30 satır tek eylem).

## §28 DONE checklist → kanıt

- [x] G10 freeze + commit → `3cdeb5f` (UX-01'den önce)
- [x] G11 (resmî) başlamadı → pilot kayıtları ayrı; resmî koşu bu kabulden sonra (§29)
- [x] next unresolved çalışıyor → adım 8, 12 + `#callout-next` pini
- [x] resolved tanımı plandakiyle aynı → `rowResolved` (§6.2 birebir: transcription current + parse current + parse.status parsed + target current; unbindable/ignored çözülmüş) → pin + sürücü aynı tanımı bağımsız hesaplar
- [x] auto-next yalnız başarılı explicit decision sonrası → adım 7 (çözülmemişken ilerlemez), 11 (kapsam kararı öncesi ilerlemez), 8/12 (çözülünce ilerler); `if(!rowResolved(previousId))return;` pini
- [x] bulk ignore atomic → adım 15 + `test_guided_callout_http.py` 8 test
- [x] 1 revision / 1 history / 1 undo → adım 15 (+1 revizyon, 1 audit), 16 (tek undo)
- [x] unknown/stale/foreign/empty all-or-nothing → HTTP testleri (400; kısmi yazım yok)
- [x] machine hint yalnız explicit `Evet, doğru` ile transcription → adım 4–6 (seçim/panel/reload yazmaz; tek tık yazar)
- [x] `Düzelt` draft'ı save öncesi yazılmıyor → adım 9–10 (sunucu iki kez okundu: değişmedi)
- [x] no-hint manual path → adım 23, 28 (elle yazılan hole/pocket) + `$('callout-hint-yes').hidden=!row.machine_text_hint;` pini (ipucusuzda düğmeler gizli, akış aynı `transcribe`)
- [x] readiness `Eksik kalanlar` → adım 2 (başlık) + 18 (○/✓ satırları, sayılar backend'den)
- [x] checklist doğru yere navigate ediyor → adım 19 (ilk çözülmemiş + odak), 21 (kontur), + kalibrasyon/seviye satırları aynı mekanizma
- [x] backend false iken frontend ready diyemiyor → adım 18 („Model henüz hazır değil · 41 şey kaldı“) + 30 („✓ Tüm gerekli bilgiler tamamlandı“ + build açık); `build.disabled=pending||!r.ready` pini
- [x] technical IDs gizlendi → adım 2 çipler + `<details id="technical-details">` / `<details id="callout-technical">` ve S5 adım 3 (aç/kapa yazmaz)
- [x] gerçek Chrome scenarios PASS → koşu 04, 35/35
- [x] callout/guided regressions PASS → `pytest -q tests -k "guided or callout"`: **507 passed**
- [x] `pytest -q tests -k "not semread"` PASS → **1450 passed / 339 deselected (25:58)** — log: `logs/regression-not-semread.log`; semread bloğu bilinçli parkta
- [x] Plate UX smoke PASS → adım 31–33 + `evaluate.json`
- [x] no automatic truth / no automatic ignore → adım 3/5/10/14/20/24 (yazmayan etkileşimler) + adım 6 (Evet = kullanıcının kendi transcribe'ı) + adım 27 (tek satır ignore kullanıcı tıklaması)
- [x] docs current → bu dosya + `docs/GUIDED_PROGRESS.md` (UX-01 bölümü)
- [x] commit + push → `430aa8f`, `3ff97ed` + bu belge commit'i — push sonrası `git status -sb` origin/main ile eşit (doğrulandı)

## Yeniden koşma

```bash
# uygulama (yeni backend şart: süreç guided.py'yi başlangıçta yükler)
PYTHONPATH=src .venv/bin/python -m drawingto3d.app
# gerçek Chrome (debug port 9222) + sekme hijyeni
~/.hermes/cache/scratch/cdp-venv/bin/python eval/audits/20261007-guided-g11/g11_clean.py
# kabul
cd eval/audits/20261007-guided-ux01 && ~/.hermes/cache/scratch/cdp-venv/bin/python ux01_acceptance.py
```
