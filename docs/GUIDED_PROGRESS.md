# Guided progress

Scope: G0 + G1  
Active plan: `docs/PLAN-20.md`  
Initial HEAD: `5175f373f1d6892e481341ed2cbcfd89dec29e36`  
Current HEAD: `5175f37` + G0 commit `373e096` + uncommitted G1.2/G1.3 değişiklikleri  
Initial worktree changes: `?? PLAN-17-HERMES.md` (kullanıcının verdiği plan kaynağı; **korunur, stage edilmez**)  
Current task: G1.4

| İş | Durum | Kanıt | Kalan |
|---|---|---|---|
| G0 | PASS | `docs/PLAN-20.md` (yeni history entry), `report.md` pivot başlığı + park kaydı, bu dosya; commit `373e096`; kod dosyası değişmedi; 0 model çağrısı | — |
| G1.1 | PASS | Entegrasyon haritası (aşağıda) + odak baseline: **59 passed, 83.30 s, EXIT=0** — `out/guided-transcription/g1-baseline.log` | — |
| G1.2 | PASS | `src/drawingto3d/callout_models.py` (4 model + normalize/region/cardinality + `geometry_key` + `callout_states`); `tests/test_callout_models.py` **35 passed** (`out/guided-transcription/g1-2-models.log`); negatif probe: bool/ters-sıfır bölge/crop kapsama/cardinality/evidence-tipi **doğru nedenle** kırmızı | — |
| G1.3 | PASS | Store entegrasyonu (create/save/accept/public + `_merge_callout_defaults`/`_prepare_callouts`/`_validate_callouts`); `tests/test_guided_callouts.py` **11 passed** (`out/guided-transcription/g1-3-callouts.log`); birleşik odak kümesi **105 passed, 80.14 s, EXIT=0** (`out/guided-transcription/g1-3-green.log`) — regresyon yok | — |
| G1.4 | IN_PROGRESS | — | T06/T07/T09/T10/T11/T12/T21 + freshness public kanıtları |
| G1.5 | TODO | — | undo akışı + `transcribe`/`edit_transcription`/`confirm_target` log testleri |
| G1.6 | TODO | — | build/artifact stale regresyonu + geç-build yarışı |
| G1.7 | TODO | — | birleşik doğrulama + kabul tablosu + teslim |

## Son doğrulamalar

- **G1.3 birleşik küme**: `.venv/bin/python -m pytest -q tests/test_callout_models.py tests/test_guided_callouts.py tests/test_guided.py tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py tests/test_guided_proposals.py tests/test_binding_end_meaning.py tests/test_guided_html.py` → exit **0**, **105 passed** (80.14 s) — log: `out/guided-transcription/g1-3-green.log`
- **G1.3 izole**: `tests/test_guided_callouts.py` → exit 0, **11 passed** — log: `out/guided-transcription/g1-3-callouts.log`
- **G1.2 izole**: `tests/test_callout_models.py` → exit 0, **35 passed** — log: `out/guided-transcription/g1-2-models.log`
- **G1.1 baseline**: odak kümesi → exit 0, **59 passed** (83.30 s) — `out/guided-transcription/g1-baseline.log`

## Entegrasyon haritası (G1.1) — mevcut store yolları × yeni callout alanları

| Store yolu | G1'de yeni alanlara nasıl dokunacak |
|---|---|
| `create` | Record'a `callout_schema_version` + boş `callout_candidates`/`callout_parses` yazar; `decisions` yeni listeleri boş taşır |
| `load` | Salt-okur; yeni alanlar yoksa varsayılanla okunur; disk migration / `geometry_version` artışı **yok** |
| `_migrated` | Değişmez; callout alanları kimlik karşılaştırmasına girmez |
| `save` (edit) | Eksik anahtar = mevcut değeri koru; `normalized_text` + transcription `revision` + target pin alanları sunucuda türetilir; yeni/değişen kayıtlar bağlantı denetiminden geçer; callout olayları loglanır; `revision+1`, `build=None` |
| `save` (undo) | History snapshot'ı yeni alanları taşır; pop ile aynen geri gelir; global revision artar; `build=None` |
| `accept` | Yalnız mevcut alanları değiştirir; callout alanları korunur; yeni callout onayı üretmez |
| `public` | `callout_schema_version`, `callout_candidates`, `callout_parses`, `callouts` (her callout için transcription/parse/target: current/stale/missing + gerekçe kodu) eklenir |
| `build` | Akış değişmez; geç build yarışında `build=None` durumuna karşı tamamlanma yolu çökmemeli (dar düzeltme) |
| `artifact` | Değişmez; mevcut stale/kimlik kapıları eski çıktıyı "güncel" sunmaz |
| `recheck` | Değişmez |

## Kararlar / engeller

- **Kalıcı sunucu kuralları (G1.2/G1.3'te uygulandı, G1.4+ testlerle genişleyecek):**
  - `normalized_text` daima sunucuda türetilir; istemci değeri ezilir. `raw_text` birebir saklanır.
  - Transcription `revision` = kayıt ilk yazıldığında/changed olduğunda `session revision + 1`; taşınan (metin+bölge aynı) kayıt eski kimliğini korur.
  - Target pinleme yalnız **yeni/değişen** onayda yapılır (`geometry_key`, `geometry_version`, `profile_id` sunucudan); taşınan onay byte-korunur → eski onay "silently current" olamaz.
  - Hedef doğrulama (store): `circle`/`circle_group` id'leri `options["circles"]` içinde olmalı; `vertex_pair` seçili profilin `v{edge}` kenarlarında **ardışık** iki uç olmalı; parse'ta açık `count` varsa benzersiz hedef sayısı ona eşit olmalı; referans verilen transcription revision'ı güncel olmalı ve exact `(callout, rev, parser_version)` parse kaydı bulunmalı.
  - `_normalized_decisions` iki taraflı karşılaştırma → aynı kayıt ikinci kez save edilince **no-op** (revision/history/log şişmez); eski istemcinin eksik anahtarı varsayılanla doldurulup eşitse dosya hiç yazılmaz.
  - `_stamp_callout_version`: callout katmanı kendi sürümünü taşır; `geometry_version` **artırılmaz**.
  - Log: `transcribe` / `edit_transcription` / `confirm_target` yalnız kullanıcı eylemleri olarak; freshness hesapları olay değil; G1'de gerçek parser olmadığından `parser/parse` olayı **yazılmaz**.
  - `CALLOUT_PARSER_VERSION = "callout-parser/1"` — G4 gerçek parser sürümünü besleyecek; şimdi parse kaydı bu sürüme bağlı; public'te parser yokken `missing/needs_parse` görünür.
- Baseline ve odak kümesi yeşil; yeni değişiklik hataları bu tabana karşı ayrılabiliyor.
- `rg` bu host'ta yok → dosya aramaları tek dosya / daraltılmış yolla yapılır.
- Pydantic 2.13.5: `bool` → `int` lax kabul → bool guard açık doğrulayıcıyla (model + store alanlarında) uygulandı.
- Test fixture'larındaki parse/target hazırlık verisidir; ürün parser/önerici kanıtı sayılmaz (PLAN-20 §10).

## Yeniden başlarken ilk somut işlem

- G1.4: `tests/test_guided_callouts.py` içine freshness + target davranış testlerini ekle (T06/T07/T09/T10/T11/T12/T21; store hedef reddi: olmayan circle, profilsiz/yakınlıksız vertex, duplicate, count uyumsuzluğu; profile/kontur değişimi → geometry_key değişir → target stale; parser sürümü değişimi → parse+target stale; stale taşınan kayıt başka düzenlemeyi engellemez). Kırmızıları gör, gereken en küçük düzeltmeyi yap, yeşil + log.
- Sonra G1.5 (undo + olay günlüğü), G1.6 (build/artifact stale + geç build), G1.7 (birleşik doğrulama + teslim).
