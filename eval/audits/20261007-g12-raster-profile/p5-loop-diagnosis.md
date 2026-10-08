# §65 P5 — zincir tanısı: ex13 ön görünüşü neden döngü kurmuyor

**Durum:** kök neden bulundu; düzeltme (TDD) sıradaki iş. **Tarih:** 2026-10-08, HEAD `6a29b88`.
Kanıt: `p5-evidence/g125-ex13-loop-trace.log` (iz koşumu), `g125_ex13_pinch.py`,
`g125_ex13_loopsprobe2.py`, `g125_ex13_front_primitives.py`, `ex13-front-compare.png`,
`ex13-front-primitives.png`, `ex13-allprofiles-small.png`.

## Yöntem

Beceri kuralı gereği döngü kopyalanmadı: `proposal._loops`'un **kendisine** geçici, env-korumalı
(`D3D_LOOPS_TRACE=1`) iz eklendi (tohum → alınan parça → gap/turn → ölüm noktası + en yakın 6
kullanılmamış uç); tek koşumdan sonra aynı dilimde geri alındı (`git checkout`), ağaç = HEAD.
Koşum önbellekli okumayla (`g125-audit-cache/exercise-13-raster.pkl`) saniyeler sürdü.

## Bulgular (ölçülü)

1. **47 döngünün 0'ı ön görünüşte.** Hepsi: izometrik (37: x 2300–3070, y 260–920) + antet
   hücreleri (10: x 2200–2305, y 2170–2295). `frames=[]`, `annotations=[]` — yani eleme katmanı
   (çerçeve/antet kuralı) suçlu değil; kayıp tamamen `_loops` zincirinde.
2. **Ön görünüşte tespit tamamen boş değil:** bölgede 22 primitif; plaka kenarları, dik
   çizgiler ve bore/R50 civarı yaylar (ör. g517 ucu (1599.4,1641.7) → bore merkezine göre
   r≈90 ≈ Ø60; g356 → r≈150 ≈ R50) tespit edilmiş.
3. **İz: 12 tohumun 12'si ≤4 adımda ölüyor.** Ölüm noktalarındaki en yakın kullanılmamış
   parça **45–186 px** uzakta (tolerans 40 + köşe erimi 48; hepsi erim dışı).
4. **Kilit yürüyüş (tohum g210):** sol kenar (gap 13.0) → alt kenar (12.5) → sağ kenar (12.5),
   sonra **(1799.5, 1777)'de ölüm.** Burada plakanın üst kenarı = **g209 (x241→2831 @1777.5)**:
   sayfa boyunca uzanan ölçü/uzatma çizgisiyle **aynı doğruya birleşmiş tek parça**. Zincir
   uç-nokta komşuluğu aradığı için g209'u göremiyor (en yakın ucu 1031 px uzakta) — oysa:
   - kuyruk (1799.5,1777) g209'un **içinde** (≈0.5 px),
   - zincirin başlangıcı (1089.8,1778) de g209'un **içinde**.
5. **Kapanış da aynı sınıf:** kuyruk g209'un içinden başın üstüne yürüyüp orada kapatabilirdi;
   uç-nokta tabanlı kapanış bunu görmüyor.

## Kök neden sınıfı

**İç-join + iç-kapanış eksik:** çizim kenarı, sayfa boyu bir eksen/ölçü/uzatma çizgisiyle aynı
doğruya birleştiğinde (yaygın pafta deseni), uç-nokta komşuluğu tabanlı zincir o parçayı hiçbir
zaman kullanamaz. Genel kural adayı (örnek-bağımsız):

- bir aday parçanın **içi** kuyruğa tolerans içindeyse: parçayı temas noktasından **ayır**,
  yürüyüş yönündeki artığıyla devam et (parçanın öteki artığı havuza döner);
- kuyruk bir parçanın içinden geçerken **başlangıç noktası** da o parçanın içindeyse: orada
  böl ve **kapat**.

Not: plaka kenarları 12–13 px boşluklarla sorunsuz yürüdü — 40/48 bütçesi normal join'ler için
yeterli; sorun tolerans değil, **kural** eksikliği. Bu yüzden toleransı büyütmek yanlış çözüm
(beceri: "asla en yakın ucu alma lisansı değil").

## İkincil gözlemler (kapsam dışı, not)

- Menüyü 37 izometrik tel dolduruyor; ön görünüş döngüsü kurulunca bunların öneri/archetype
  yarışına girmemesi ayrı bir temizlik adayı (pictorial bölge ayrımı).
- Bore/R50 yayları parçalı (merkez çizgileri + ölçü okları bölmüş); daire kurtarma boşluğu
  (p5-analysis.md boşluk #2) aynen duruyor.

## Sonraki adımlar

1. TDD: sentetik birim test (kare + üst kenarı iki yana taşan tek uzun çizgi; raster
   `corner_joins=True`) — döngü iç-join ile kapanmalı. Önce RED.
2. `_loops`'a iç-join + iç-kapanış (ayırma mantığıyla); GREEN + ilgili süit.
3. ex13 iz koşumunu yinele: ön görünüş döngüsü kuruldu mu (`p5-evidence/` tablosu yenile).
4. P5 akışına dön: daire kurtarma → kararlar/derleme → kabul koşumu.
