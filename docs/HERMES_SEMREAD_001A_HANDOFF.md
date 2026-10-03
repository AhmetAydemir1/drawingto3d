# SEMREAD-001A — devir notu (diğer agenta)

> **ÖNEMLİ (ikinci faz tamamlandı):** bu notun 3–5 ve 6. bölümlerindeki "11/12, A09 açık" durumu
> **geçersizdir**. İkinci faz koşusu (`20261004-011753-564abb62`, şema/okuyucu v2, `shape` alanı,
> katı kapsam, `per_image_message_labeled`, yeni L5 kimlik kontrolü) ile **A01–A13'ün tamamı
> kapandı**; `conclusion: SEMREAD-001A complete`. Güncel gerçek için bölüm 7'ye ve
> `out/lab/semread-001a/continuations/semread-001a-identity-20261004/diagnosis.md` dosyasına bak.
> Aşağıdaki mekanizma/kanıt-kuralı anlatımı hâlâ geçerlidir (kurallar sertleşti: kimlik artık git
> durumundan değil **içerikten** türetilir).

**Durum (ilk faz, tarihsel):** uygulama + kanıt tamam. **Kabul: 11/12 kapalı, açık tek satır A09** (nedeni ve kanıtı aşağıda).
**Ağaç:** commit yok. `out/` gitignored; tüm kanıt dosyaları yerelde durur. Çalışan ağaçta `M`/`??`
dosyaları var — üzerine yazmadan önce `git status` al.

Kanıt kökleri:

| ne | yol |
| --- | --- |
| kabul tablosu | `out/lab/semread-001a/acceptance.json` |
| üretilen rapor (kanıttan) | `out/lab/semread-001a/final/report.md` |
| durum / engel / bütçe | `out/lab/semread-001a/state.json` |
| test kanıtı (junit + sidecar) | `out/lab/semread-001a/junit/{semantic,regression}.xml` + `*.tree.json` |
| canlı attempt kanıtı | `out/lab/runs/20261003-223023-29eb57bf/semread-001a-l{1..4}/attempt-*` |

## 1) Ne değişti

Yeni (untracked):

- `src/drawingto3d/semantic_schema.py` — `PreparedImage`, kaynak izi (sha256/sayfa/bbox), probe yanıt sözleşmesi, `probe_json_schema()`. Bozuk gövde **onarılmaz** (`parse_probe_json` fırlatır).
- `src/drawingto3d/semantic_images.py` — `open_source`, `prepare_full_page`, `prepare_crop`, `_render_pdf_crop`, `overlay_from_observations`, `observation_snapshot_id`.
- `src/drawingto3d/semantic_reader.py` — `probe_prompt`, `SemanticReader.probe`, `leak_check`, `ALLOWED_REQUEST_KEYS` / `ALLOWED_IMAGE_KEYS`.
- `eval/semantic_reader_probe.py` — sürücü: `--dry-run`, `--record-tests`, `--live`, `--evaluate`, `--extend-budget`, `--worker` (paylaşılan `LabRunner`/`Job`, kök `out/lab`, iş id `semread-001a-l*`).
- `tests/test_semantic_schema.py`, `test_semantic_images.py`, `test_semantic_transport.py`, `test_semantic_reader.py`, `test_semantic_reader_probe.py`.

Değişen (tracked):

- `src/drawingto3d/llama.py`:
  - `_chat_request(..., image_labels=None, images_layout="single_message")` → gövde + kayıt tek yerden; kayıt artık `images_layout` ve `messages_layout` (hangi görsel hangi mesajda) taşır, her görsel için `image_id` + **gönderilen son byte'lardan ölçülmüş** boyut (`_png_size`, IHDR).
  - `_ollama_chat(..., images_layout=...)`, `OllamaChat.complete(..., images_layout=None)` (`None` → `ChatSettings.images_layout`), `ChatSettings.images_layout` alanı + `as_dict()`'e yeni anahtar.
- `src/drawingto3d/inference_log.py`: `RecordedChat.complete(..., images_layout=None)` yalnız verilince iletilir (eski imzalar bozulmadı).
- `tests/test_planner.py`: `ChatSettings.as_dict()` kapalı küme testi `images_layout` ile güncellendi (aksi halde regresyon düşüyordu — yakalandı ve düzeltildi).
- `tests/test_inference_log.py`: çoklu görsel "görüntüsüz yazılmaz" testi (önceki turdan).

Davranış sözleşmeleri (diğer agentın bilmesi gerekenler):

1. **Çoklu görsel çerçevelemesi**: `images_layout="per_image_message"` → görsel başına bir mesaj (metinsiz), en sonda istem. Tek görselde iki düzen aynı gövdeyi üretir. Bilinmeyen düzen `ValueError` (gönderilmez).
2. **Prompt çerçeveden bağımsız**: "You are given N image(s) … They appear in this exact order: …" (eski "This message carries …" kaldırıldı, yoksa görsel-başına-mesaj düzeninde yanlış olurdu). Prompt diske sabitlenir; üretilenle uyuşmazsa worker `prompt_drift` ile reddeder.
3. **Bildirilen ayar gerçekten uygulanır**: overlay'ın `resize_max_side`'ı daha önce sessizce yutuluyordu → artık uygulanıyor (`overlay_from_observations(..., resize_max_side=)`).
4. **İstek kaydı tek başına yeter**: `request-manifest.json` → `images_layout`, `messages_layout`, her görsel için `index/image_id/sent_sha256/sent_bytes/sent_width_px/sent_height_px/resize`.
5. **Kapalı listeler**: `ALLOWED_REQUEST_KEYS` (+`images_layout`, `messages_layout`), `ALLOWED_IMAGE_KEYS` (+`image_id`), `SETTING_KEYS` (+`images_layout`), `LAYOUTS`. Yeni alan eklerken bu listeleri de güncelle, yoksa `leak_check` "tanımsız anahtar" yazar.

## 2) Canlı kanıt (gerçek yerel çağrılar)

Model: `qwen3-vl:8b-instruct`, digest `0533d74300e4f9bc367d675d4e64ffd073d50ff16a2b4096cc2e8a1cf8c96319`,
Ollama `0.32.1`, Q4_K_M, 8.8B. Koşu: `20261003-223023-29eb57bf`. Dördü de `pass`.

| vaka | attempt | görsel | çerçeveleme | süre | token (prompt/üretilen) | request sha256 | kapsam |
| --- | --- | --- | --- | --- | --- | --- | --- |
| L1 | attempt-5 (13 dosya) | 2 | per_image_message | 68.861 s | 2286 / 145 | `e9ba2e23e49f62da…` | 2/2 |
| L2 | attempt-4 (13 dosya) | 2 | per_image_message | 60.919 s | 2286 / 145 | `7c61e96ab3862713…` | 2/2 |
| L3 | attempt-3 (14 dosya) | 3 | per_image_message | 93.586 s | 3416 / 223 | `1bd3395621b1a19f…` | 3/3 |
| L4 | attempt-3 (13 dosya) | 2 | per_image_message | 62.588 s | 2373 / 151 | `e1de02f20e6ac7ee…` | 2/2 |

Hepsi: artifact-index doğrulandı, `done_reason=stop`, 9 kapı True
(`images_sent_as_expected, request_has_hash, raw_answer_recorded, parsed, schema_valid,
references_valid, not_truncated, no_leakage, transport_ok`), altın ayrımı temiz, sızıntı yok.
Görsel ölçüleri: L1/L2 512×512 ×2; L3 ham sayfa 1024×724 + overlay + 600 dpi crop (841×594);
L4 ham raster + native crop.

Testler (kayıtlı, aynı ağaç parmak izi `417ad58727a5994e`):

- `semantic` → 122 passed, 0 failure (6.85 s)
- `regression` (`inference_log, model_choice, reader, planner, chain_model, baseline_fields, lab_runner`) → 139 passed, 0 failure (362.85 s)
- Toplam 261 test, 0 hata (iki sete ait dosyalar ayrık: 122 + 139).

Bütçe: **11/12 gerçek çağrı**. İlk tavan 8'di; `state.json → budget_extensions` içinde
`8→12` ve nedeni yazılı (`--extend-budget`). Tavan düşürülemez.

## 3) Kabul tablosu (A01–A12)

| # | ne | durum |
| --- | --- | --- |
| A01–A08 | test kapıları (taşıma, şema, referans, sızıntı, yeniden boyutlandırma, kayıt alanları, parser drift, overlay/kiminlik) | closed |
| **A09** | **L1/L2 görsel kimliği ↔ şekil eşleşmesi** | **open** |
| A10 | L3/L4 çoklu görsel (3/2) + çözülen bölgeler | closed |
| A11 | altın sentinel/leak testleri + canlı sızıntı temiz | closed |
| A12 | izlenebilirlik: dört vaka + index + güncel kod kimliği + rapor | closed |

`state.json → blocked`: `L2: gold şekil eşleşmesi tutmadı (kaçan=['image-1','image-2'])`.
`acceptance.json → conclusion`: "implementation status: 11/12 açık kabul kapandı; açık: A09".

## 4) A09: iki ayrı ölçüm (karıştırılmamalı)

1. **Bağlama (binding) — düzeltildi.** Tek mesajda iki *benzer* görsel bu backend'de ayrışmıyor:
   eski attempt'lerde yanıt ya tek madde döndü (L1) ya iki madde de üçgeni anlattı (L2).
   Görsel başına mesaj düzenine geçince L1 **tam doğru**: `image-1`=triangle, `image-2`=square.
2. **İlan edilen sırayı izleme — model sınırı, düzeltilmedi.** L2'de paket sırası
   `[image-2(kare), image-1(üçgen)]`; prompt sırayı birebir ilan ediyor; model yine de
   `image-1`="a black square", `image-2`="a black triangle" dedi — yani görselleri **kendi doğal ID
   sırasına** göre etiketliyor, ilan edilen permütasyonu yok sayıyor.

Kanıt satırları: `out/lab/runs/20261003-223023-29eb57bf/semread-001a-l2/attempt-4/request-manifest.json`
(sıra 0 = `image-2`, `sent_sha256` = karenin dosyası) vs aynı dizindeki `response-parsed.json`.
Attempt geçmişi (framework değişimi) raporun L1/L2 bölümünde tek satırda listelenir.

**Kasıtlı yapılmayan "düzeltme":** görselin yanına ID metni yazmak (ör. "image-2:") L2'yi geçirir ama
vakayı anlamsız kılar — aranan şey zaten sıra→kimlik eşlemesi; ID'yi vermek cevabı vermek olur.
Karar bekleyen nokta: A09 bu bulguyla 001B'ye mi taşınır, yoksa L2 ayrı bir vaka olarak mı yeniden
tanımlanır (ölçtüğü şey değişir, ayrı karar).

## 5) Yeniden üretim ve kurallar

```bash
# 1) kod donar (hiçbir düzenleme yapma)
.venv/bin/python eval/semantic_reader_probe.py --record-tests semantic,regression   # junit + ağaç parmak izi
.venv/bin/python eval/semantic_reader_probe.py --live                              # gerçek çağrılar (runner altında)
.venv/bin/python eval/semantic_reader_probe.py --evaluate                          # kabul + rapor
# öncesinde: --dry-run (çağrı yok), --extend-budget (tavanı kayda geçirerek yükseltir)
```

Kanıt kuralları (kabulün kapanması bunlara bağlı, testle kanıtlı):

- **Kod dondurulmadan kanıt kaydedilmez.** Test kanıtı, yanındaki `*.tree.json` sidecar'ındaki
  **ağaç parmak izi** güncel ağaca eşitse geçerli; canlı attempt'in `manifest.json → code_fingerprint`
  de güncel kod kimliğine eşit olmalı. Eski bir revizyonun testi/başarısı satır kapatmaz.
- **Test kanıtı bildirilen dosyadan gelmeli** (A01 regression ister; semantic.xml tek başına kapatmaz).
- **Canlı satır ek koşulları:** artifact-index doğrulandı, `image_id` **ve** ölçülmüş boyut kayıtta,
  yanıt kapsamı eksiksiz, verdict `pass`.
- **A12** dört vakanın hepsini + index'i + güncel kod kimliğini ister; **A11** yalnız taze sentinel
  testlerini sayar.
- Eksik/eski kanıt satırı **kapatmaz**; neden `state.blocked` ve raporda yazılır.
- Bilinen tuzak: `--timeout` `float` olmalı — case ayarı `300.0` iken `int` parser tüm işleri HTTP
  öncesi reddeder (exit 2, `missing_result`, sıfır çağrı). Üretilen iş komutları aynı `build_parser()`
  ile ayrıştırıldığı için arg-manşet kayması testle engelli.

## 6) Silinmeyen geçmiş / açık uçlar

- Eski başarısız koşular durur: `20261003-212829-8dbeaf1b` (argparse `--timeout` hatası, **sıfır
  çağrı**), `20261003-213015-15e5d296`, `20261003-213932-242c1095` (tek-mesaj çerçevelemesi),
  `20261003-221442-6683a691` (çerçeveleme deneyi; kod sonradan değiştiği için **kanıt sayılmaz**).
- 1 çağrı yedek kaldı (11/12) — harcanmadı.
- Üç dosya untracked kaldı ve commit edilmedi: yeni moduller, probe ve testler. İstenirse tek commit'te
  sabitlenebilir (kanıt dosyaları `out/` altında olduğu için commit dışında kalır).

## 7) İKİNCİ FAZ SONUCU (üstteki A09/11-12 durumunu geçersiz kılar)

**Kabul: A01–A13 kapalı → `SEMREAD-001A complete`.** Kanıt: `out/lab/semread-001a/acceptance.json`
(`open: []`), `final/report.md`, `continuations/semread-001a-identity-20261004/{diagnosis.md,
evaluation.json, acceptance.json, junit/, start/}`.

Ne değişti (sözleşme v2):

- **Okuma/yazma sürümleri:** `READER_VERSION=semread-reader/2`, `PROBE_SCHEMA_VERSION=semread-probe/2`.
- **`shape` alanı:** küçük, sürümlü sınıflandırma (`triangle/square/circle/other/unknown`); **aynı
  seçenekler her görsele** sunulur, hangi kimliğin hangi sınıfı taşıdığı prompt/şema'ya yazılmaz.
  Değerlendirme **birebir sınıf eşitliği** (`exact_class_equality`); metinde anahtar sözcük aramak
  kaldırıldı ("not a square" artık geçmez).
- **Yeni düzen `per_image_message_labeled`:** görsel başına bir mesaj; mesaj metni yalnız
  `Image ID: <id>` (`LABEL_PREFIX`). Kaynak adı/hash/gold taşınmaz; görüntü byte'ları değişmez.
  `LAYOUTS` sözlüğü tek yerde (`drawingto3d.llama`), bilinmeyen çerçeveleme gönderilmeden reddedilir.
- **Katı yanıt kapsamı:** gönderilen her ID yanıtta **tam bir kez**; tekrar kapsamı bozar, eksik reddedilir.
- **Tamamlanma:** eksik metadata `unknown`; `complete` yalnız `done_reason == "stop"` + sayım
  metadata'sıyla. Bilinmeyen kesilme kabulü geçirmez.
- **Kimlik (evidence identity) artık içerikten:** ilgili kod+test+config dosyaları + test komutları +
  ortam. Git durum metni kimlik değildir → **yalnız doküman eklemek kanıtı bayatlatmaz**, ilgili bir
  kaynağın içeriği değişirse bayatlatır (ikisi de testle bağlı).
- **Görsel kimliği kanıta bağlandı:** istek kaydındaki `image_id` ↔ diskteki byte'lar; beyan
  ölçümle çelişirse eşleme kurulmaz, iki kimlik aynı byte'ı paylaşırsa "belirsiz" yazılır (tek ad seçilmez).
- **Yeni kontrol vakası L5 / satır A13:** **aynı iki görsel** (`image-11`=L1'in `image-1` byte'ları,
  `image-27`=L1'in `image-2`), yalnız kimlik değişiyor → model yine triangle/square dedi. Genelleme
  iddiası değildir (tek fixture çifti, tek model).

Ölçülen canlı koşu: `20261004-011753-564abb62`, L1..L5 beşi de taşıma kapsamında `pass`; L2'de
gönderilen sıra `image-2,image-1` iken model **kimliğe göre** cevapladı (eski sıra-üzerinden hata
tekrarlanmadı). Testler: 159 semantic + 139 regression = **298, 0 hata**, kimlik `afa83bbf…/güncel`.
Bütçe: **16/18** gerçek çağrı; iki uzatma da gerekçesiyle `state.json`da. Kalan 2 çağrı harcanmadı
(tek görsel tanı çağrıları bilinçli olarak yapılmadı: probe kaynağını değiştirip taze kanıtı
bayatlatırdı ve A09 için gerekli değil — bkz. `diagnosis.md` §5).

Devir kuralı: bu koşudan sonra **yeni bir koşu gerekmiyor**. Bir devam koşusu açacaksanız önce
kanıt kimliğini alın (`--dry-run`/`--evaluate` çıktısı) ve probe/test kaynağını değiştirmeyin;
değiştirirseniz tüm canlı + junit kanıtı bayatlar ve bütçe yeniden gerekir.
