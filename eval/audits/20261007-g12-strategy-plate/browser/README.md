# browser/ — üretim biçimi paneli, gerçek Chrome kabulü (PLAN-25 §42 + §97/8)

G12.2 UX'i değiştirdi (yeni panel + hazırlık kategorisi metinleri), §97'nin faz listesi "UX değiştiyse
gerçek Chrome" der. Bu koşu, **ölçülmüş** bir oturumun (kapsam tam, üretim biçimi seçilmemiş) üzerinden
kullanıcının yolunu gerçek fare/klavyeyle yürür; `Runtime.evaluate` yalnız durumu OKUR ve `fetch`'i
gözlemler. Hiçbir karar komutla verilmez.

```bash
# 1) oturumu app'in kendi deposuna hazırla (üretim biçimi ve üretim tarayıcıda kalsın)
.venv/bin/python eval/audits/20261007-g12-strategy-plate/g12_strategy_plate_acceptance.py \
    --prepare-only --store-root out/guided          # → {"token": …} + PASS 0/1/1b/2
# 2) app + gerçek Chrome (CDP 9222) açıkken
~/.hermes/cache/scratch/cdp-venv/bin/python \
    eval/audits/20261007-g12-strategy-plate/browser/strategy_panel_acceptance.py <token>
```

## Sonuç: **TÜMÜ GEÇTİ 7/7**, EXIT=0

| adım | ne kanıtlar | sonuç |
|---|---|---|
| A | hazırlık listesi sunucunun kendi satırını gösterir: `○ Parçanın ana oluşturma biçimini seç` (kategori `missing_build_strategy`), tamamlananlar ✓ satırları | PASS |
| B | panel dört seçeneği sunar; **döndürme ve çok görünüş "(bu sürümde yok)" ve seçilemez**, uzatma `(önerilir)`, durum yazısı `Henüz seçilmedi — üretim bu kararı bekler.` | PASS |
| C | üretim biçimi seçilmeden **üretim düğmesi kapalı** (örtük extrude yok) | PASS |
| D | gerçek tıklama + kaydetme `/api/guided/strategy`'ye gider; gövde **yalnız `{token, revision, kind}`** (`strategy_key`/`geometry_version` YOK — §36); sunucu kararı anahtarıyla (64 hex) ve geometri sürümüyle (3) sabitler | PASS |
| E | durum yazısı seçili biçimi söyler, üretim düğmesi açılır; gerçek tıklamayla üretim **complete**, sunucunun ilan ettiği STEP adresi 200 · 52.008 bayt · `ISO-10303` başlığı | PASS |

Ekran görüntüleri: `S-00-open.png` / `S-01-choices.png` (oturum açıldı; sağ panelde "Model henüz hazır
değil · 1 şey kaldı — ○ Parçanın ana oluşturma biçimini seç" ve kapsam özeti), `S-02-strategy-saved.png`
(panel: seçili "Sabit kalınlıklı profili uzat (önerilir)", döndürme ve çok görünüş boş/devre dışı,
"Seçili: …", üretim düğmesi açık), `S-03-built.png` (üretim tamam). Adım kayıtları:
`strategy-panel-steps.json`, tam çıktı: `strategy-panel-run.log`.

## Sürücü tuzakları (bu koşuda öğrenilenler)

- Radyo düğmesi `value` **özelliği** taşır, `value` niteliği değil: `input[value='extrude_profile']`
  seçicisi `null` döner. Etikete/kutuya tıkla (`page.box` + `page.click`).
- Hazırlık listesi `#readiness-questions`'dır (`#questions` callout panelinin eski listesi) ve sunucu
  yanıtıyla **asenkron** dolar: okumadan önce metni bekle.
- Public durum üretim hâlini **`build_status`** alanında taşır (`build.status` yok); artefakt adresi de
  `step` alanında ilan edilir — URL uydurma, ilan edileni kullan.
