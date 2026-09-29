# Genel input nerede duruyor — modelsiz `propose` süpürmesi (2026-09-27)

Kullanıcının sorusu: “proje sadece örnekler üzerine mi çalışıyor, genel input olacak?” Bu rapor o soruya
koddan verilebilecek cevabı ölçüyle ayırır: **iskelet genel, karar katmanı değil.** Ölçüm tek komutla
yeniden üretilir, model çağrısı yoktur (saniyeler sürer):

```
PYTHONPATH=src .venv/bin/python -m drawingto3d.cli propose "<drawing>" out/general-input-check
```

`propose` aile bilmeyen yoldur: ne model çağırır, ne dosya adına bakar, ne parça şablonu taşır. Plaka dahil
10 vaka dosyasının tamamı koşuldu (plaka dışı 9 dosya aşağıda; plaka `draft` verir).

| pafta | sınıf | çıktı | ilk ret gerekçesi |
| --- | --- | --- | --- |
| plastic-enclosure-1 (vektör PDF) | vektör | refused | `tam iki çap ölçüsü bekleniyordu (delik + cep), 0 okundu; doğrulanan iddia türleri: {'distance': 3, 'radius': 1}` |
| exercise-1-vector (`Drawing.pdf`) | vektör | refused | `en büyük kapalı döngü yuvarlatılmış dikdörtgen değil (3 ilkel, 20.54×35.95 mm; bu dilim yalnız düz parça arketipini öneriyor)` |
| exercise-1 (`my_part.jpg`) | raster | refused | `pafta ölçeği okunamadı (kalibrasyon yok)` |
| exercise-51 (PNG) | raster | refused | `pafta ölçeği okunamadı (kalibrasyon yok)` |
| exercise-17 (PNG) | raster | refused | `pafta ölçeği okunamadı (kalibrasyon yok)` |
| exercise-13 (PNG) | raster | refused | `pafta ölçeği okunamadı (kalibrasyon yok)` |
| studycadcam-60 (JPG) | raster | refused | `pafta ölçeği okunamadı (kalibrasyon yok)` |
| studycadcam-50 (JPG) | raster | refused | `pafta ölçeği okunamadı (kalibrasyon yok)` |
| flange-1 (PNG) | raster | refused | `pafta ölçeği okunamadı (kalibrasyon yok)` |

Hepsinde `readings = 0`: modelsiz genel yol plaka dışında hiç ölçü kümesi üretmiyor.

## Bunun okunuşu

- **Tek başına en büyük engel raster ölçek:** 9 dosyanın 7'si aynı gerekçeyle duruyor — ankraj ve ölçek
  yok, dolayısıyla milimetre yok. Bu, yeni bir bulgu değil, ölçülmüş hâli: raster okuyucusu çizgileri,
  daireleri ve yazıları buluyor (flange 388 çizgi + 2 daire + 29 ifade) ama hangi sayının hangi çizgiyi
  ölçtüğünü bağlayacak ankraj ve ölçek henüz yok.
- **Vektörde engel arketip sözlüğü:** plastic paftası **11/11 sayıyı sıfır gürültüyle** okuyor (bkz.
  `eval/README.md` okuma tabloları), yine de `propose` reddediyor çünkü dilim “tam iki çap ölçüsü” istiyor;
  okuma 3 mesafe + 1 yarıçap doğruladı. Yani sayılar okunmuş, karar katmanı plaka şeklinde.
- **Döngü seçimi ayrı bir açık:** `Drawing.pdf`'te en büyük kapalı döngü 3 ilkelli 20,54 × 35,95 mm bir
  detay — parçanın dış konturu değil. “Hangi kapalı döngü parçadır” sorusu da arketip sözlüğüyle birlikte
  çözülmeli.
- **Model yolu bu tabloyu değiştirmiyor:** `chain_model` bugüne kadar iki parçada denendi (plaka 7
  başarısız koşu; plastic 1 başarısız + bir kez hatalı `skipped`) ve hiçbirinde geçerli plan vermedi.
- **Derleyici gerçekten aile-bağımsız:** `verified_plan` koşuları `bracket_linear_pattern` ve
  `shaft_revolve_cross_hole` planlarını STEP'e çevirdi; `general.py` dosya adına/aileye/referansa
  dallanmıyor, plaka yalnız `from_plate` uyum katmanında yaşıyor.

## Genel input sayılmaz — projenin kendi kuralı da bunu söylüyor

`eval/cases.json`: `pilot: []`, `hidden: []`, 8 bağımsız parçanın tamamı deponun kendi örnekleri
(5 görülmüş regresyon + 3 atanmamış). PLAN Bölüm 5'in genel-input kapısı ≥10 pilot parça ve ≥20 saklı
parça (≥10'u raster) istiyor; ikisi de boş. Bu yüzden “genel input” bugün **hedeftir, ölçülmüş özellik
değildir**.

Bir de yanıltıcı nokta: `flange-1` çizim kontrolünde “KALDI” verdict'i alıyor ama kutu ölçüsü
`[1, 2, 50]` ↔ referans `[50, 100, 100]` ve hacim `0,1` ↔ `202,1` cm³ — yani verdict geçerken parça yanlış.
Genellik iddiası bu verdict'e dayandırılamaz.

## Sıradaki iş sırası (birer satır)

1. `propose`'a ikinci arketip (revolution/şaft ya da serbest kapalı profil) — iki vektör paftada modelsiz
   taslak üretmeye başlar; genellik yolunun asıl açığı budur.
2. Raster ankraj + ölçek — 7 raster paftayı milimetreye çevirir, okuyucunun bulduğu geometri kullanılabilir
   hâle gelir.
3. “Hangi kapalı döngü parçadır” seçimi — detay görünüşü parça sanan dalı kapatır.
4. Bunların hiçbiri model eğitimi gerektirmez; hepsi kural tabanlı ve çevrimdışı ölçülebilir.
