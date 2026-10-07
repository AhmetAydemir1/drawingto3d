# G9 — Plate golden path (PLAN §15) · delivery plan, FROZEN BEFORE THE FIRST BUILD

Tarih: 2026-10-07 · Otorite: kök `PLAN.md` §15 + `docs/PLAN-20.md` §11.7 (G9 maddesi).
Bu dosya, ilk üretim çalıştırılmadan **önce** yazıldı ve o haliyle commit edildi; kabul ölçütleri
çıktı görülmeden sabitlendi (PLAN-20 §11.7: "yeni tolerans gerekiyorsa çıktı görmeden gerekçesiyle sabitle").

## Akış (gerçek UI, gerçek tarayıcı — kararlar yalnız kullanıcı girdisiyle)

    drawing → candidates → transcription → parse → proposal → confirmation → compile → build → STEP → evaluator

Sürücü: `plate_acceptance.py` (Chrome CDP; G3 kabulünün gerçek-girdi harness'ı). Tüm kararlar gerçek fare
tıklaması / gerçek klavye girdisiyle verilir; test kodu oturuma karar enjekte etmez, yalnız okur.

1. **Aç** — `Plate With A Pocket Drawing.PDF`, taze oturum (yeni upload). 45 callout adayı beklenir.
2. **Kontur** — çizimde plaka dış konturuna tıklanır (en büyük kapalı `wire`; recon: `outline_1`, 8 kenar
   line/arc, px kutusu 945×630).
3. **Kalibrasyon** — `İki ölçü noktası seç`: g9 ve g11 delik merkezlerine tıklanır; değer, basılı ölçü
   satırı `1 00,00` (=100 mm) seçilerek doldurulur; uygulanır. (Beklenen ölçek ≈ 7.876 px/mm.)
4. **Kalınlık** — `15` yazılır, kaydedilir (basılı `1 5,00`).
5. **Görüş** — pafta çerçevesi bulundu + hizalı + `/Rotate=0` olduğundan ürün ekseni kendi çerçevesinden
   doğrular (PLAN §8.6); ek kullanıcı onayı istenmez, karar açık bırakılmaz. (Kanıt: `options.sheet_frame`.)
6. **Callout'lar** (43'ü kapsam kararı, kural: okunan yazılır; bağlanamayan beyan edilir; callout olmayan yok sayılır):

   | callout (ipucu) | kullanıcı metni / karar | hedef |
   |---|---|---|
   | `6,80 THRU ALL` | `4 x Ø6,80 THRU ALL` — çizimde yazan notun tamamı (adet + Ø + geçiş) | elle: 4 daire `circle_group` (g9,g11,g10,g12) → `user_click` onayı |
   | `50,00` | `Ø50 8 DEEP` — üst görünüş Ø50, derinlik kesitten (8,00) | öneri: g8 dairesi (kalibrasyonla uyum) → `Onayla` |
   | `M8 - 6H THRU ALL` | metin aynen yazılır (diş: dilbilgisinde yok) | `Bağlama yok / desteklenmiyor` (kapsam dışı beyanı) |
   | `1 00,00` / `80,00` / `60,00` / `1 5,00` / `8,00` | sırasıyla `100,00` / `80,00` / `60,00` / `15,00` / `8,00` | `Bağlama yok / desteklenmiyor` — düz ölçü derleyicisi yalnız kontur *köşe çifti* bağlar; bu kontur yaylı olduğundan v1 çekirdeği yalnız daire merkezi bağlar (çizimdeki karşılıkları: 100 → kalibrasyon, 15 → kalınlık, 80/60 → izlenen taslak + evaluator) |
   | `4 x` (not parçası) | yok sayılır (`Bu callout değil`) — bağımsız callout değil, metni ana notla okundu | — |
   | diğer 36 (zarf rakamları/harfleri, başlık bloğu, `SECTION B-B`) | yok sayılır (`Bu callout değil`) | — |

7. **Üret** — hazırlık kapısı temizken `3B taslak ve STEP üret`; üretim kendi `plan-audit.json`'unda STEP'i
   yeniden açıp denetler.

## Dondurulmuş kabul ölçütleri (ilk çıktı görülmeden)

Temel kapı — mevcut evaluator (`eval/metrics.py` `compare`): tek katı, `isValid`, vektör ≤ max(1 mm, %2),
hacim ≤ %25, silindir yarıçapları ≤ 0.5 mm. (PLAN-20 §11.7: "mevcut evaluator'ın bağımsız formülünü ve
toleranslarını kullan".)

G9 sıkı kapı — `plate_regression.py` (bağımsız formül; bbox-min köşesine göre):

| ölçüt | değer | gerekçe (dondurma anında) |
|---|---|---|
| bbox (120, 80, 15) | her eksen ±0.2 mm | kalibrasyon tam (787.57 px ↔ 100.00); izleme hatası recon'da ≤0.02 mm |
| hacim | referanstan ≤ %0.5 **ve** analitik nominal 124825.4 mm³'ten ≤ %0.5 | tüm özellik ölçüleri basılı metinden; hata kaynağı yalnız dış kontur izlemesi |
| 4 geçişli delik | r = 3.4 ±0.05; merkez ±0.3 mm (10,10)(110,10)(10,70)(110,70); z-spân (0→15) ±0.1 | izlenen merkezler nominalden ≤0.02 mm sapıyordu; yarıçap basılı `6,80`den |
| 1 kör cep | r = 25 ±0.05; merkez ±0.3 mm (60,40); spân (7→15) ±0.1 (üstten, derinlik 8) | çap basılı `Ø50`, derinlik basılı `8,00` |
| 4 köşe yuvarlatma | r = 10 ±0.3; aynı dört konum; tam kalınlık | yuvarlatmalar basılı değil, mürekkepten izlendi |
| silindir envanteri | tam 9 mantıksal silindir (referansta da aynı; kernel yarım-yüz bölebilir → eksen konumuna göre birleştirilir) | yanlış/fazla özellik yakalanır |
| (üretilen ↔ referans) simetrik fark | kütle merkezi hizalı ≤ %0.5 hacim | kalan şekil sapmaları görünür kalsın; ham fark da raporlanır |
| STEP yeniden açılış | evaluator `importStep` + ürünün kendi `plan-audit.json` yeniden-açılış kaydı | PLAN §15 "STEP reopen" |

Referans: `examples/pdf with steps/5/plate with a pocket.STEP` (bbox 120×80×15, hacim 124825.417 mm³,
14 silindir yüzü = 8 yarım delik + 2 yarım cep + 4 yuvarlatma — kernel bölmesi; mantıksal envanter 9).

## Kanıt yolları

- adım adım JSON: `g9-steps.json`; ekran görüntüleri: `plate-??-*.png`
- oturum kaydı: `session-public.json`, `session.json` (kopya), `review-bundle.json` (PLAN §14 denetim tablosu)
- üretim: `part.step`, `plan.json`, `plan-audit.json` (kopya)
- değerlendirme: `verdict.json` (`plate_regression.py` çıktısı)
- rapor: `DELIVERY.md` (sonuç) — bu dosya dondurulmuş plandır, sonuç görüldükten sonra değiştirilmez.

## Hata politikası (PLAN §15)

İlk koşu bir adımda düşerse: sapma genel bir ürün kusuru mu (çizime özel kestirme değil) diye kök nedeni
bulunur, çözüm testi kırmızıdan yeşile yazılır, uygulanır; süreç **taze oturumla** baştan koşulur.
Kullanıcı onayı beklenmez (PLAN §15). Koşu 1'in başarısızlığı da kanıt olarak kaydedilir.
