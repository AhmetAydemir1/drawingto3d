# G11 — ilk sabit 10-pafta koşusu: yöntem (ilk vaka koşusundan önce donduruldu)

**Tarih:** 2026-10-07 · **Manifest:** `eval/guided_10_manifest.json` (G10'da sonuçlar görülmeden
donduruldu; koşu boyunca **değişmez**). **Spec:** kök `PLAN.md` §17.

## Kurallar (PLAN §17 + planın kendi yasaları)

1. **Vaka başına taze oturum** (yeni `set_file` yüklemesi), **aynı HEAD**, **vaka sırasında ürün kodu
   düzenlemesi yok**. Her vaka kaydı `git_head` taşır; rapor tek HEAD ister.
2. **No-reference-leak:** sürücü kararları yalnız *görünen oturum verisinden* (adaylar, ipuçları,
   `options.profiles/circles/measurements`) ve *çizimin kendisinden* (insan okuması) alınır. Referans
   STEP yolu yalnız evaluator'a verilir; vaka kaydı alındıktan **sonra** koşar. Vakaya özel kural
   ürün koduna girmez — kararlar `recipes/<case_id>.json` içinde, denetlenebilir biçimde durur.
3. **Tahmin yok:** eksik/çelişkili bilgi karar uydurularak kapatılmaz; vaka kendi taksonomi koduyla
   kaydedilir (aşağıda) ve koşu devam eder. Ürün düzeltmesi G12'nin işidir (generic fix → yeni koşu).
4. Toplu kapsam kararı (UX turu) standart akıştır: karara bağlanmamış satırlar tek açık eylemle
   kapatılır; kararlı satırlar dokunulmaz.

## Vaka kaydı (PLAN §17 alanları — birebir)

`eval/audits/20261007-guided-g11/cases/<case_id>.json`:

```
case_id · run_id · at · git_head · source_path · source_sha256_checked
candidate_count · manual_region_count · ignored_count · transcription_count
parse_success_count · parse_edit_count · proposal_count(offered, sürücü gözlemi)
proposal_accept_count(evidence=proposal) · manual_target_correction_count(evidence=user_click)
review_import_used(false) · build_blockers([...]) · build_success · step_reopen
bbox(métrics.describe.vector) · features(plan.json listeleri + métrics künyesi)
final_geometry_verdict(metrics.compare: {pass, shape_ok, detail_ok, checks})
user_interventions(logo dayalı: typed_texts, hint_clicks, single_ignores, bulk_rows, ...)
failures([{code, detail}]) · artifacts(step/plan/audit/session-public/review-bundle yolları)
```

**Verdict ölçütü:** `metrics.compare(describe(produced), describe(reference))` — repo'nun kendi
evaluator'ı. `shape_ok` = (solids, valid, vector) katı kapı; `detail_ok` = (volume, cylinders) yumuşak
katman; **correct = `pass`** (ikisi birden). `callout_scope_only` vakada geometric verdict yoktur —
yalnız okuma/kapsam beyanları kaydedilir (asla "geometric correctness" diye raporlanmaz).

**Primary metrik:** `GUIDED_CORRECT_STEP_RATE = correct full_step vakası / full_step vakası` (bu
koşuda 9 referanslı vaka; no-ref vaka paydada değil, ayrı raporlanır).

## Taksonomi (başarısızlık kodları, PLAN §17)

`DETECT_MISS · DETECT_FALSE_POSITIVE · TRANSCRIPTION · PARSE_UNSUPPORTED · PARSE_AMBIGUOUS ·
BIND_NO_PROPOSAL · BIND_WRONG_PROPOSAL · BIND_STALE · CONSTRAINT_UNSUPPORTED · CONSTRAINT_CONFLICT ·
CAD_UNSUPPORTED · CAD_WRONG · STEP_EXPORT · STEP_REOPEN · EVALUATOR`

Kayıt kuralı: her `failures[]` satırı bir kod + kanıt metni taşır; hiçbir başarısızlık sessizce
yutulmaz, hiçbir başarı olmayan şey "PASS" yazılmaz.

## Çıktılar

- Vaka kayıtları: `cases/<case_id>.json` (+ `shots/<case_id>-*.png`).
- **Teslimler (PLAN §17):** `eval/guided_10_report.json` + `eval/guided_10_report.md` —
  `g11_report.py` tarafından `cases/*.json` + manifest'ten üretilir; kapsam sınıfı, metrik, taksonomi
  dağılımı, vaka tablosu ve dürüstlük notlarını taşır.

## Ortam / yeniden üretim

```bash
PYTHONPATH=src .venv/bin/python -m drawingto3d.app                     # 127.0.0.1:8765
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=~/.hermes/cache/scratch/chrome-g11 about:blank
~/.hermes/cache/scratch/cdp-venv/bin/python eval/audits/20261007-guided-g11/g11_runner.py \
  eval/audits/20261007-guided-g11/recipes/<case_id>.json
.venv-cad/bin/python eval/audits/20261007-guided-g11/g11_report.py       # raporları yazar
```

Sürücü, G9/UX koşularının kanıtlanmış yardımcılarını yeniden kullanır
(`eval/audits/20261007-guided-ux-round/ux_acceptance.py` + g3-review `cdp_client.py`); bu dosya
yalnız vaka akışını ve kaydı ekler.

## Kapsam dışı

G12 (generic fix loop) bu koşuda başlamaz: bulgular kaydedilir, düzeltmeler ve yeniden koşu G12'dedir.
G13 (10/10 geometrik doğruluk) bu koşunun hedefi değildir; bu koşu **tam kayıt** hedefler.
