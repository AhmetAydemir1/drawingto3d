# G11 — devam notu (kaldığı yerden sürdürme)

**Durum:** 6/10 vaka kayıtlı (plate PASS; drawing-2, plastic-enclosure, exercise-12, exercise-51 →
CAD_WRONG; exercise-17 → CAD_UNSUPPORTED). Kalan: exercise-13, my-part, flange,
flange-elbow-90-raster-noref. Ölçütler dondurulmuş: `DELIVERY-PLAN.md` (değişmez); manifest:
`eval/guided_10_manifest.json` (değişmez).

**ÖNEMLİ — sabır:** vaka koşusu raster paftada 5–10 dk sürer ve sürücü yalnız kontrol noktalarında
satır basar; arada "takıldı" sanıp ÖLDÜRME (yaşandı: üç koşu yanlışlıkla kesildi, biri build
ortasında). İlerleme kanıtı: `cases/<id>/` dosyaları + `shots/<id>-NN-*.png` mtime'ları.

## Vaka koşma sırası (her vaka için)

```bash
# 0) ortam: uygulama (yeniden başlatmak gerekirse) + Chrome 9222 + cdp-venv
cd /Users/aydemir/Desktop/drawingto3d
pkill -f drawingto3d.app; sleep 1
PYTHONPATH=src .venv/bin/python -m drawingto3d.app > out/guided-g11/app.log 2>&1 &   # 127.0.0.1:8765
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=~/.hermes/cache/scratch/chrome-g11 about:blank &
curl -s -o /dev/null -w "app=%{http_code}\n" http://127.0.0.1:8765/

# 1) probe (görünen veri + ekran görüntüsü; raster ingest dakikalar sürer — sabırlı ol)
~/.hermes/cache/scratch/cdp-venv/bin/python eval/audits/20261007-guided-g11/g11_probe.py \
  "examples/pdf with steps/3/Exercise 17.PNG" exercise-17
#    ingest istemciyi aşarsa: oturum yine tamamlanır; token = out/guided/<token>/ klasör adı.
#    Token hazır olduğunda (curl /api/guided/<token> → 200) aynı probe'u 3. argümanla çalıştır:
#    g11_probe.py "<source>" <name> <token>

# 2) recete yaz: eval/audits/20261007-guided-g11/recipes/<case_id>.json
#    (kontur, kalibrasyon/öneri, kalınlık, kararlar, notlar — yalnız görünen veri + çizim okuması)

# 3) koşu (rasterlerde gerekirse confirm_view:true ekle; çizim çerçevesi bulunamazsa zorunlu)
~/.hermes/cache/scratch/cdp-venv/bin/python eval/audits/20261007-guided-g11/g11_runner.py \
  eval/audits/20261007-guided-g11/recipes/<case_id>.json > out/guided-g11/case-<case_id>.log 2>&1
#    exit≠0 = verdict fail ya da adım hatası; kayıt yine yazılır (cases/<case_id>.json) ve log saklanır.
```

## Sürücü davranışı (öğrenilen gates)

- Koşudan önce tarayıcıyı temizle: `.venv/bin/python g11_clean.py` (34 sekme birikti → yeni sekme
  starve olur; temizlik koşuyu hızlandırır).
- Kararlar hep gerçek girdi olaylarıyla; `Runtime.evaluate` yalnız okuma/scroll/fetch.
- Idempotent: kontur seçimi/ack yeniden koşuda atlanır — aynı token'da güvenle tekrar çalıştırılır.
- Gate'ler: `#view-ack`+`#view-confirm` (çerçeve bulunamazsa zorunlu; recetede `confirm_view:true`),
  `#contour-fix` (önce "… kenarını çıkar" düğmeleri, sonra birleşim onay kutusu), `#ack`,
  ve **`#build` tıklamasından önce düğmenin etkinleşmesini bekle** (`state.questions` boş + pending
  bitene kadar disabled kalır; pending yarışı yaşandı).
- Kontur tıklaması: sunucu-doğrulamalı (`decisions.profile_id`); DOM geçici durumu yetmez.
- Öneri kabulü: `#proposals .proposal:nth-child(N) button` — **kutudan** tıklanır (`click_element`).
- Kalan kararsızlar: `#callout-ignore-many` iki adımlı toplu eylem (UX turu akışı).
- Üretim reddi kanıtı: build POST'u 400 dönebilir (eksik/geçersiz model) — kayıtta
  `console_errors`/`rejected_requests` altında görünür; kanıt indirmeleri artık yalnız gerçek build
  (step URL'i) varsa yapılır.
- Değerlendirici: `.venv-cad` altında `evaluate_case.py` (reopen + `metrics.compare`),
  referans yolu manifestteki `reference_identifier_evaluator_only`.

## Rapor (tüm vakalar bitince)

```bash
.venv/bin/python eval/audits/20261007-guided-g11/g11_report.py
# → eval/guided_10_report.json + eval/guided_10_report.md (pending vakalar açıkça listelenir)
```

## Notlar / bilinen maliyetler

- Raster ingest uçuk: exercise-51 ≈ 20 CPU-dk (~25 dk duvar); Flange.PNG ~258 s (önceki ölçüm).
  İstemci zaman aşımına düşerse sunucu bitirmeye devam eder → **token ile devam** (yukarı bkz.).
- `out/guided/<token>/` klasörü: `source.png`, `drawing.png`, `observations.json`, `session.json`.
- `out/` gitignore'da; kanıtlar `eval/audits/20261007-guided-g11/` altında (shots/, logs/).
- İlk denemelerin kanıtları: `logs/case-drawing-2-abort1.log`, `logs/case-exercise-51-attempt1.json`,
  `logs/run-*.log` (UX turu). Hiçbir başarısızlık sessizce atılmadı.
