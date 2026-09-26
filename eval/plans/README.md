# Genel plan örnekleri (derleyici sözleşmesi)

Bu klasördeki iki JSON, `src/drawingto3d/general.py` içindeki `GeneralPlan` sözleşmesinin
iki farklı işlem birleşimini gösterir. İkisi de **sentetik derleyici örnekleridir**: hiçbir
ölçü bir teknik çizimden okunmuş gibi gösterilmez (`source.kind = "synthetic"`, tüm
parametreler `assumed`). Çizimden okuma başarısı bu dosyalarla iddia edilmez.

- `bracket_linear_pattern.json` — L profili `extrude`, XZ düzleminde tanımlı delik
  silindiri, `repeat_linear` ile 2'li desen, `cut`.
- `shaft_revolve_cross_hole.json` — iki `revolve` (mil + flanş), `fuse`, YZ düzleminde
  ofsetli daire aracıyla `cut` (yan delik).

Değerlerin türetilmesi ve bağımsız doğrulaması `derive_examples.py` içindedir:

```sh
PYTHONPATH=src .venv/bin/python eval/plans/derive_examples.py
```

Kurma:

```sh
PYTHONPATH=src .venv/bin/python -m drawingto3d build-general eval/plans/bracket_linear_pattern.json out/general-examples/bracket
PYTHONPATH=src .venv/bin/python -m drawingto3d build-general eval/plans/shaft_revolve_cross_hole.json out/general-examples/shaft
```

## Beklenen değerlerin kaynağı

- **Bracket**: hacim kapalı form; L kesit alanı 744 mm², `744 * width - 2 * pi * (hole_d/2)² * thickness`.
  Ölçülen 22 084,380550980757 mm³ (kapalı formla fark ~8e-12 mm³; kesimler çokyüzlü, çekirdek tam).
- **Shaft**: mil hacmi dönel hacim integraliyle kapalı form
  (`shaft_washers`, π hariç; ölçülen 13 894,70825010 mm³, formülle tam uyuşuyor). Yan deliğin
  kaldırdığı hacim `8*∫₀^r √((R²-y²)(r²-y²))dy` ile sayısal integrallenir (Simpson; bağımsız
  Monte Carlo ile de doğrulandı): 349,9866 mm³.

## Çekirdek (OCC) hassasiyeti — bilinen sınır

Silindir–silindir kesişimi (yan delik) CAD çekirdeğinde yaklaşık hesaplanır: ölçülen kesme
hacmi 349,9709 mm³, analitik 349,9866 mm³ → ~1,6e-2 mm³ (4,5e-5 göreli) sapma. STEP'e yazıp
geri okumak da ~2,6e-9 göreli hacim gürültüsü ekler. Bu nedenle:

- `check_general` içindeki `export_round_trip` eşiği göreli 1e-7 (bozuk dışa aktarımı yakalar,
  çekirdek yuvarlamasını taşımaz).
- Shaft örneği **hacim beklentisi bildirmez**; yan delik, araç silindirinin yarıçap/eksen/derinlik
  denetimiyle doğrulanır (konum ve çap 1e-3 mm toleransla). Sayısal beklenti varsayımlar
  listesinde rapor edilir.
