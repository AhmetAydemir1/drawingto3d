# SEMREAD-001B — izlenen kanonik gold (PLAN-8 §3–§4)

Bu dizin benchmark'ın **gerçeğinin** (gold) kanonik kaynağıdır ve git'te izlenir.

| Dosya | Rol |
| --- | --- |
| `specs/<page>.json` | Sayfa başına **kanonik gold spec'i** (iddialar, hedefler, kanıtlar) |
| `manifest.json` | Sayfa başına kaynak/spec/referans **sha256**'ları, claim sayısı, nitelikler + kararlı `gold_content_identity` (PLAN-9 §15) |
| `FREEZE.json` | Başarılı `--freeze` sonrası dondurma kaydı: kimlik + sayfa hash'leri (PLAN-9 §17; §22 alanları P5'te genişler) |

Üretilmiş dosyalar (`out/lab/semread-001b/corpus/gold-src/`, `.../corpus/gold/`) izlenmez;
çalışma zamanı çıktısıdır ve buradaki spec'lerden **yeniden üretilebilir** olmalıdır.

## Zincir

```
eval/semread_001b_gold/specs/<page>.json           (izlenen kanonik spec)
  └─ eval/semread_001b_gold_regions.py --page X --write      → out/.../corpus/gold-src/X.json
      └─ eval/semread_001b_reference.py --page X             → out/.../corpus/gold/X.json
          └─ eval/semread_001b_pilot.py --evaluate           → B02 kapısı + acceptance.json
```

`gold_regions.py --spec` verilmezse önce bu dizindeki spec'i arar (yerel `out/` kopyası yalnız
yedek). Ölçülen hedef kutusu (`target_box_norm`) kullanan spec'ler gözlem çıkarımı (OCR/Hough)
çalıştırmadan üretilir; `target_observation` / `callout_texts` kullananlar için çıkarım zorunludur.

## Manifest komutları

```bash
.venv/bin/python eval/semread_001b_gold_manifest.py --write    # spec'lerden manifesti üret
.venv/bin/python eval/semread_001b_gold_manifest.py --check    # hash/claim/nitelik doğrula
.venv/bin/python eval/semread_001b_gold_manifest.py --freeze   # P5 kapısı (atomik): 10/10 + hash'ler + tam yeniden üretim kanıtı
.venv/bin/python eval/semread_001b_gold_manifest.py --verify --page dev-plate-pocket
```

* `--check` kapsamı yazar (`6/10` gibi) ve **listelenen** girdilerin tutarlılığını doğrular.
* `--freeze` ayrıca **her** korpus sayfasının izlenen spec'i olmasını şart koşar; izlenmeyen
  üretilmiş gold varsa kapı kapanır (PLAN-8 §3, §13). Atomiktir (PLAN-9 §16–§17): kapı içinde
  **tüm** sayfalar izlenen spec'ten yeniden üretilip manifest hash'iyle karşılaştırılır —
  saklanan dosya geçerli olsa bile mevcut kod yeniden üretemiyorsa dondurma kapanır; başarıda
  `FREEZE.json` yazılır. Ayrıca `--verify` çalıştırmayı hatırlamak gerekmez.
* `--verify` izlenen spec'ten referansı yeniden üretir ve manifestteki hash ile karşılaştırır;
  eşleşme = "temiz klon gerçeği yeniden kurabiliyor" kanıtı (PLAN-8 §17).
* `gold_content_identity` (PLAN-9 §14–§15): manifest zaman damgası taşımaz; dondurmanın
  bağlandığı kimlik yalnız gerçeği etkileyen alanların (sayfa, kaynak/spec/referans hash'i,
  claim sayısı, `vision_checked`, `exhaustiveness`) kanonik sha256'sıdır — aynı içerik her
  koşuda aynı manifest baytlarını verir.

## Kurallar

* Her spec'te `scope` + yapılı `exhaustiveness` zorunlu.
* **Raster** sayfa: `vision_checked=true` **ve** her claim'in `source_evidence`ında görsel
  doğrulama izi (`vision`) bulunmalı (§16).
* Ölçülen kutu: dört sonlu değer, `0<=x0<x1<=1`, `0<=y0<y1<=1`, pafta içinde ve gerekçesi yazılı
  (`target_reason` / `measurement_reason` ya da kanıt metninde ölçüm ifadesi) (§10).
* **Döngüsel ölçek kanıtı yasak** (§11 + §6): `corroboration.kind = independent_scale` ise
  dayanak değer **ne** claim'in kendi yazılı değeri **ne de başka bir değerlendirilen Ø/R
  claim'inin** yazılı değeri olabilir — kök, claim setinin dışındaki bağımsız bir datuma
  (ör. doğrusal ölçü) çözülmelidir; A→B, B→A geçemez. Bağımsız dayanak yoksa `kind = none`
  yazılır ve mm değeri yalnız yazılı çağrıdan gelir. Ölçek çıkarılamayan sayfada ölçülmüş
  kutu yine geçerlidir (frozen-exercise-17 dersi).
* Spec'i değiştiren herkes `--write`'ı yeniden çalıştırıp manifesti commit'ler; `--check`
  sapmayı yakalar.
