# G12.1b — kapsam kararı kabulü (gerçek Chrome)

Sürücü: `g12_disposition_acceptance.py` (PLAN-25 §21/§99). Kararlar gerçek fare/klavye olaylarıyla
girer; `Runtime.evaluate` yalnız durumu okur. Çizim: `examples/pdf with steps/5/Plate With A Pocket
Drawing.PDF` (dondurulmuş vaka değil, ürün yüzeyi).

## Koşum

```bash
PYTHONPATH=src .venv/bin/python -m drawingto3d.app            # http://127.0.0.1:8765
# Chrome: --remote-debugging-port=9222 (scratch profil)
~/.hermes/cache/scratch/cdp-venv/bin/python g12_disposition_acceptance.py
```

Kanıt: `browser-acceptance.log`, `g12-disposition-steps.json` (makine okunur adım listesi),
`A-*.png … E-*.png`. Çıkış kodu 0 = 10/10 adım.

## Adımlar (10/10 PASS)

| # | Adım | Ne kanıtlıyor |
|---|---|---|
| 1 | Plaka açılışı | Genel durum kapsam denetimini taşır (`coverage.counts`), 45 etkin alan |
| 2 | A: “Bu bir ölçü/not değil” | Karar `not_model_input` olarak yazılır; panel “Modele ait değil” der (ham enum görünmez) |
| 3 | A: ilerleme | Satır backend kovasından çözülür ve oto-ilerleme kararın KENDİ konumundan sürer |
| 4 | B: desteklenmeyen + gerekçe | Buton kopyası birebir; gerekçe kullanıcıdan; sunucuya aynen yazılır |
| 5 | B: build kapalı | `unsupported_build_relevant` sorusu readiness'te; `#build` disabled; kova `build_relevant_unsupported` |
| 6 | B: blok/navigasyon | “Sonraki eksik” desteklenmeyen satıra uğrar; panel §16 metnini + madde durumunu gösterir |
| 7 | C: temsil ediliyor | Karar sözlüğü `decision:thickness`; kalınlık kararı dayanak seçilir; kova `redundant` |
| 8 | D: dayanak eskidi | Alan düzeltmesi dayanağın okumasını eskitir → bağımlı satır `invalid_duplicate` (blocker) |
| 9 | E: reload | Kararlar sunucu kaydından gelir; kapsam özeti backend sayılarından çizilir |
| 10 | E: undo | Alan değişikliği geri alınır; dayanak yeniden geçerli — sessiz yeniden yazım yok |

## Notlar

- B/1. koşuda üç adım düştü; üçü de **sürücü kusuruydu** (karar sonrası rozet okuma, ilerleme
  beklentisinin yanlış kurgusu, `uygulayamıyor`/`uygulanamıyor` harf farkı). Ürün tarafında düşen
  adım olmadı; düzeltmeler aynı turda yapıldı ve koşum 10/10 yeşil bitti.
- Ölçek: plaka 45 adayın 41'i bu koşumda kasıtlı olarak açık bırakıldı (kapsam tamamlanmadı) —
  build kapalı kalır; kanıtlanan şey *yanlış hazırlık* değil, kararların doğru kovaya düşmesi.
