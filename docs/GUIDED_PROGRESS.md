# Guided progress

Scope: G0 + G1  
Active plan: `docs/PLAN-20.md`  
Initial HEAD: `5175f373f1d6892e481341ed2cbcfd89dec29e36`  
Current HEAD: `5175f373f1d6892e481341ed2cbcfd89dec29e36` (G0 doküman değişiklikleri commit'e hazırlanıyor)  
Initial worktree changes: `?? PLAN-17-HERMES.md` (kullanıcının verdiği plan kaynağı; **korunur, stage edilmez**)  
Current task: G1.2

| İş | Durum | Kanıt | Kalan |
|---|---|---|---|
| G0 | PASS | `docs/PLAN-20.md` (yeni history entry), `report.md` pivot başlığı + park kaydı, bu dosya; HEAD planla aynı (`5175f373…`); `git status --short`: yalnız bu üç dosya + untracked plan kaynağı; kod dosyası değişmedi; 0 model çağrısı | — |
| G1.1 | PASS | Entegrasyon haritası (aşağıda) + odak baseline: **59 passed, 83.30 s, EXIT=0** — `out/guided-transcription/g1-baseline.log` | — |
| G1.2 | IN_PROGRESS | — | `callout_models.py` + `tests/test_callout_models.py` |
| G1.3 | TODO | — | — |
| G1.4 | TODO | — | — |
| G1.5 | TODO | — | — |
| G1.6 | TODO | — | — |
| G1.7 | TODO | — | — |

## Son doğrulama

- Kod sürümü: HEAD `5175f37` + uncommitted G0 doküman değişiklikleri (PLAN-20.md, report.md, GUIDED_PROGRESS.md)
- Komut: `.venv/bin/python -m pytest -q tests/test_guided.py tests/test_guided_geometry_state.py tests/test_guided_geometry_migration.py tests/test_guided_proposals.py tests/test_binding_end_meaning.py tests/test_guided_html.py`
- Exit code: **0**
- Passed / failed / skipped: **59 passed** (83.30 s; önceden var olan hata yok)
- Log yolu: `out/guided-transcription/g1-baseline.log`

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

- Baseline temiz (59/59); yeni değişiklik hataları bu tabana karşı ayrılabilir.
- `rg` bu host'ta yok → dosya aramaları daraltılmış yollarla (tek dosya / `grep` ile açık dosya listesi).
- Pydantic 2.13.5 ölçümü: `bool` → `int` **kabul ediliyor** (lax mod) → "bool adet olmaz" kuralı açık doğrulayıcı ister (sayı alanlarında uygulanacak).

## Yeniden başlarken ilk somut işlem

- G1.2: `tests/test_callout_models.py` (kırmızı) → `src/drawingto3d/callout_models.py` (asgari yeşil). Devamında G1.3 store entegrasyonu + `tests/test_guided_callouts.py`.
