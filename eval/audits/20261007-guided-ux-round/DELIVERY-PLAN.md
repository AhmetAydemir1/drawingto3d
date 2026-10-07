# G9 UX turu — kabul planı (ilk koşudan önce donduruldu)

**Tarih:** 2026-10-07 · **Kapsam:** PLAN-23 §15 dar UX turu — G9 pafta koşusunda ölçülen *kullanıcı
yükü*nü (45 aday, 43 kapsam dışı ilanı) generic biçimde azaltan dört akış. Bu dosya ilk koşudan
**önce** commit'lenir; koşu sonucu görüldükten sonra değiştirilmez. Her ölçüt, sürücüde tek bir
`record()` satırıdır ve gerçek Chrome'da gerçek girdi olaylarıyla yürütülür.

## Kapsam — değişen dört akış (ürün)

1. **next-unresolved**: `#callout-next`, karara bağlanmamış (metin yok / yok sayılmamış / “bağlanamaz”
   ilan edilmemiş) callout'lar arasında sırayla gezinir; sayaç düğme etiketinde ve özet satırındadır.
2. **explicit bulk ignore**: `set_ignored_many` sunucu komutu + `#callout-ignore-many` düğmesi.
   Yalnız *kararsız* satırlara dokunur, kararlı satırı asla ezmez; tek geçmiş adımı, tek revizyon;
   her satır kendi `callout_reviews` kaydını ve kendi log satırını (`evidence.bulk = true`) alır;
   düğme iki adımlı açık silah (`bulkArmed`) — ilk tıklama hiçbir şey yazmaz, yalnız onay ister.
3. **machine hint tek-tık**: `transcribe` + `accept_hint`. Sunucu, yazılan metnin *bu callout'un
   kendi* makine ipucuyla birebir aynı olmasını doğrular; log satırı kabul edilen ipucunu
   (`accepted_hint`, `machine_text_hint`) adlandırır. “İpucunu düzenle” yolu (taslağa alma) durur.
4. **readiness actionable checklist**: hazırlık maddeleri kategori rozetli, her biri `Git`
   düğmeli; tıklama, sunucunun kendi `action`/`reason` alanına göre ilgili denetime odaklanır
   (callout seçimi + `#callout-text` / `#target-panel` / `#profile` / `#pick-calibration` …).

Kapsam dışı sayılan (bilinçli): sessiz title-block filtreleme yok, case-specific kural yok, yeni
parser/grammar işi yok, G10/G11 manifestine dokunma yok.

## Kabul ölçütleri (dondurulmuş)

Sürücü `ux_acceptance.py`, aynı plate çizimiyle, taze oturum + taze Chrome profili ile:

1. 45 aday listelenir; özet satırı `45 kararsız` gösterir; `#callout-next` etiketi `Sıradaki
   kararsız (45)` ve etkin; hiçbir satır sessizce gizlenmemiştir (görünür satır = 45).
2. Readiness listesi: her madde rozet + `Git` düğmesi taşır; *transcribe* eylemi düğmeye basınca
   ilgili callout seçilir ve odak `#callout-text`'e gider; kontur maddesi odak `#profile`'a gider.
3. next-unresolved: ilk tıklama C1'i, ikinci tıklama C2'yi seçer (sıra korunur), sayaç düşer.
4. Kontur, kalibrasyon (basılı `1 00,00`), kalınlık 15, iz onayı G9 koşusundaki gibi gerçek
   tıklamayla girilir; kalibrasyon px/mm değeri G9 ile aynıdır (7,876 ± 0,01).
5. `4 x` fragmanı tek tek (mevcut yol) kapsam dışı ilan edilir — tek-satır yolu regresyona uğramaz.
6. Delik notu (“4 x Ø6,80 THRU ALL”, bileşik metin: elle yazılır) parse `parsed`; dört delik
   `circle_group` ile elle onaylanır (`user_click`).
7. Cep (“Ø50 8 DEEP”, bileşik metin: elle yazılır) parse `parsed` (blind, derinlik 8, Ø50); cep
   dairesi onaylanır (öneri ya da elle).
8. **İpucu tek-tıkı**: M8 notu ve basılı metni eksiksiz üç ölçü (`80,00`, `60,00`, `8,00`) tek
   tıkla (`#callout-hint-save`) kaydedilir; alan kullanıcı yazmadan doludur; sunucu kaydı
   `raw_text == ipucu`; log `accepted_hint = true` + `machine_text_hint` taşır. Uzunluk/spacing
   düzeltmesi gereken iki ölçü (`1 00,00`, `1 5,00`) elle yazılır (Evet/Düzelt/Ölçü sorusu yok —
   yalnız normal metin alanı). M8 + beş ölçü “bağlanamaz” ilan edilir.
9. **Toplu kapsam kararı**: kalan kararsız = 36. Birinci tıklama: durum satırı onay ister, sunucu
   revizyonu ve karar sayısı **değişmez**. İkinci tıklama: 36 satır tek revizyonda `ignored`;
   revizyon artışı tam 1; her satırın log kanıtı `bulk = true`; özet `0 kararsız`; düğme pasif.
   Kararlı satırlar (delik, cep, M8, ölçüler, fragman) kararlarını korur (ezilmez).
10. “Yok sayılanları göster” ile 45 satırın 37'si `Yok sayıldı` olarak görünür — sessiz düşme yok.
11. Hazırlık temiz (liste yalnız “✓ …” durum satırı), üretim düğmesi açık.
12. Üretim gerçek CAD ile koşar: `build_status == "complete"`, STEP üretilir; inceleme paketi
    delik+cep için derlenmiş zinciri taşır; konsol hatası ve reddedilen istek yoktur.
13. **Yük ölçümü** (kayıt): kapsam kapatma = 1 tek ignore + 1 toplu eylem (36 satır) = G9'da 37 tek
    akış; elle yazılan metin 4 (G9: 7); tek tıkla kabul edilen ipucu 4 (G9: 0).

## Yöntem / ortam (G9 ile aynı)

```bash
PYTHONPATH=src .venv/bin/python -m drawingto3d.app                     # 127.0.0.1:8765
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=~/.hermes/cache/scratch/chrome-ux-round about:blank
~/.hermes/cache/scratch/cdp-venv/bin/python eval/audits/20261007-guided-ux-round/ux_acceptance.py
```

Kanıtlar bu klasöre yazılır: ekran görüntüleri, `ux-steps.json`, `session-public.json`,
`review-bundle.json`, `part.step`, `plan.json`, `plan-audit.json`. Sürücü, herhangi bir adım
düşerse sıfırdan farklı döner.

## Başarısızlık tanımı

Herhangi bir ölçütün düşmesi, konsolda beklenmeyen hata, ya da kararlı bir satırın toplu kararla
ezilmesi/ sessizce düşmesi **bulgu**dur: koşu durdurulur, bulgu kaydedilir, ürün düzeltilir ve
taze oturumda yeniden koşulur (fail → generic fix → rerun).
