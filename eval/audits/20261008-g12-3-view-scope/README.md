# G12.3 — view-scoped geometry foundation (PLAN-25 §45–§54)

Bu dizin G12.3'ün kanıtıdır. Fazın özü: geometri artık *ölçüldüğü görünüşe* aittir — adaylar oturumla
bir kez kalıcı yazılır, her kontur/daire sahibini taşır, "hangi görünüş üretimin kaynağı" kullanıcının
kararıdır ve hiçbir aşama çizilmiş bir resimden (izometrik adayı) kendiliğinden üretim çıkarmaz.

## Ne değişti

- **`src/drawingto3d/view_scope.py` (yeni)** — atama kuralı (tek adayın içinde → o görünüş, belirsiz
  sınır → `None`, en yakın komşu tahmini yok), aday etiketleri (`Görünüş 1/2`, `Kesit adayı`,
  `İzometrik adayı`), rol sözlüğü ve çatışma kapısı (çapraz görünüş / izometrik aday / bayat rol).
- **`guided.py`** — `DrawingViewDecision` + `Decisions.drawing_views` (§47, `ViewConfirm`'e dokunulmadı);
  `create` sayfayı bir kez segmentler ve adayları + sahipliği yazar (§46/§48); migration *aynı* kimlik
  kurallarıyla görünüş katmanını da tazeler (kural dışı, sessiz yeniden segment yok); `set_drawing_view`
  komutu sunucu damgasını yazar; public yükünde `view_candidates` / `view_roles` / `drawing_views`;
  boşta kalan kapılar: `_sheet_issues` kategorisi + `dispatch_plan` reddi (§52).
- **`callout_models.geometry_key`** — satır bazında `view_id` + onaylı rol kararları (§50): sahiplik ya da
  rol değişince eski hedef/strateji kendiliğinden güncelliğini yitirir.
- **`GEOMETRY_VERSION 3 → 4`** (§49, önerilen yol).
- **UI** — `guided.html` görünüş paneli + "Tüm geometrileri göster" kaçışı; `guided.js` rol seçimi
  (`/api/guided/view`, istemci sürüm uydurmaz), kontur/daire menülerinin ana görünüşe daralması (§52),
  tuval üstünde aday kutuları ve etiketleri (§51); `app.py` görünüş ucu.

## Kanıt

- `browser/ui-run.log` + `A-open/B-primary/D-scoped-menu/E-show-all/G-overlays.png` — **§54 gerçek
  Chrome: 7/7** (adaylar ve roller, menü kapsamı, kaçış, yeniden yüklemede kalıcılık ve *yeniden
  segment yok*). Bu fazda **inşa doğruluğu iddiası yoktur** (§54).
- `pytest-relevant.log` — ilgili süit (incelemenin kendi komut seti): **628 passed / 235,04 s / EXIT=0**.
- `pytest-broad.log` — geniş regresyon (`pytest -q tests -k "not semread"`): **1582 passed / 339 deselected /
  27:17 / EXIT=0** (G12R: 1569 → +13).
- `plate-regression.log` — G12R Plate kabulü v4 altında yeniden koştu: kabul edilmiş üretim yolu
  görünüş katmanından etkilenmedi.
- `browser/r01_r02-recheck.log` — G12R'nin gerçek Chrome koşusu (R-01/R-02, 11/11) **nihai kodla**
  yeniden koştu: menü kapsamı ve görünüş paneli, kabul edilmiş UI akışlarını bozmadı.

## Sınır (bilinçli)

Sahipsiz (`None`) kontur bir çatışma değildir: sahiplik *kurulmamıştır*, "görünüşler arası" değildir —
bu yüzden kapı yalnız kullanıcının kendi kararıyla *çelişen* sahiplikte kapanır (farklı görünüş,
referans/izometrik rol). Mevcut tek görünüşlü pafta yolları bu katman yokmuş gibi çalışmaya devam eder.

Dokunulmayanlar: eski G12/G12R kanıt dizinleri, tarihsel G9/G11 kanıtları, dondurulmuş manifest
(`eval/g12_baseline/manifest.json`) ve `eval/metrics.py`; ana metrik **1/9** olarak sabit.
