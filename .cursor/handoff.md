# Handoff

Bu sohbette tek bir görev üzerinde dur. Context dolunca aynı sohbette devam et. Yeni sohbet açılırsa bu dosya `sessionStart` ile geri gelir; dersleri buraya yaz.

## Görev

Açılı çizilmiş ölçü çizgisini oku. `lines.diagonal_strokes` ve leader yolu duruyor; `dimension_for` hâlâ eksen boyunca dizilmiş çizgileri okuyor, bu yüzden açılı dimension çizgisi görünmez. Stroku kendi eksenine ve ona dik yönde izdüşür. Hedef: flanştaki `6 x Ø6.40` ve `Ø11.00`, ve `plate-pocket-1` üzerindeki açılı ölçü.

Durumu `dur` yapmadan bitmiş sayma. Bitmiş sayma koşulu: açılı dimension çizgisi en az bir gerçek sayfada okunuyor, ilgili pytest yeşil, `eval/frontend.py` ve `--as-raster` tablosunda kapsam düşmüyor ve gürültü artmıyor.

## Nasıl çalış

- Başlamadan önce `eval/README.md` içindeki Known gaps bölümünü oku. Orada ölçülüp bırakılmış yolları tekrarlama.
- Bir hipotez kur, en küçük değişikliği yap, ölç. Sayı iyileşirse tut. Kötüleşirse geri al ve nedenini aşağıya yaz.
- İlgili test: `PYTHONPATH=src .venv/bin/python -m pytest tests/test_diagonal_leaders.py tests/test_lines.py tests/test_perceive.py -q`
- Okuma değişince model çağırma. Önce `PYTHONPATH=src .venv/bin/python eval/frontend.py`, sonra aynı komut `--as-raster` ile. Kapsam artmalı, gürültü artmamalı. Bir sayfa kazanç, başka sayfa kayıp ise değişiklik kabul değildir.
- Aynı hatayı ikinci kez aynı yolla deneme.

## Dersler

Henüz bu dosyaya işlenmiş bir tur yok. Ölçülmüş boşluklar `eval/README.md` Known gaps bölümünde.
