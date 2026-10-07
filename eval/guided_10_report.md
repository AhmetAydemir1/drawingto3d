# G11 — ilk 10-pafta koşusu, sonuç raporu

- Kayıtlı vaka: **10/10** · bekleyen: —
- **GUIDED_CORRECT_STEP_RATE = 0.1111** (1/9 full_step vaka) — payda donmuş manifestin sabit full_step kümesi; STEP üretilemeyen/bekleyen vaka paydadan düşülmez (G11R-01). Üretilemeyenler: exercise-17-raster, exercise-13-raster, my-part-raster.
- Koşullu oran (bilgi; ana metrik değildir): 0.1667 (1/6) — yalnız geometri kararı üretilebilen vakalar arasında.
- Taksonomi dağılımı: {'CAD_WRONG': 5, 'CAD_UNSUPPORTED': 2, 'EVALUATOR': 4, 'CONSTRAINT_UNSUPPORTED': 2, 'TRANSCRIPTION': 1}
- Ürün kodu değişmedi (ilk→son vaka HEAD): evet

| vaka | sınıf | aday | kapsam dışı | metin | üretim | verdict | taksonomi |
|---|---|---|---|---|---|---|---|
| plate-pocket-vector | full_step | 45 | 37 | 8 | ok | pass | — |
| drawing-2-vector | full_step | 66 | 66 | 0 | ok | fail (şekil -) | CAD_WRONG |
| plastic-enclosure-vector | full_step | 65 | 64 | 1 | ok | fail (şekil ok, detay -) | CAD_WRONG |
| exercise-12-vector | full_step | 70 | 70 | 0 | ok | fail (şekil -) | CAD_WRONG |
| exercise-51-raster | full_step | 26 | 26 | 0 | ok | fail (şekil -) | CAD_WRONG |
| exercise-17-raster | full_step | 20 | 20 | 0 | durdu | üretilmedi | CAD_UNSUPPORTED, EVALUATOR |
| exercise-13-raster | full_step | 32 | 32 | 0 | durdu | üretilmedi | CAD_UNSUPPORTED, EVALUATOR |
| my-part-raster | full_step | 49 | 49 | 0 | durdu | üretilmedi | EVALUATOR, CONSTRAINT_UNSUPPORTED |
| flange-raster | full_step | 29 | 29 | 0 | ok | fail (şekil -) | EVALUATOR, CAD_WRONG |
| flange-elbow-90-raster-noref | callout_scope_only | 27 | 27 | 0 | durdu | kapsam dışı | TRANSCRIPTION, CONSTRAINT_UNSUPPORTED |

## Dürüstlük notları
- Ana metrik paydası manifestin 9 full_step vakasıdır; build/evaluator hatası olan ve bekleyen vakalar bu kümeden çıkarılmaz (G11R-01 düzeltmesi).
- Her vaka taze oturumda, aynı ürün HEAD'inde koştu; kayıtlar `git_head` taşır; ilk→son ürün kodu farkı: yok.
- sha256 doğrulaması tüm kayıtlı vakalar: tamam.
- Referans STEP'ler yalnız evaluator'a verildi; kararlar `recipes/*.json` içinde, görünen oturum verisi + çizim okumasıyla alındı.
- Bekleyen vakalar listede açıkça `pending`; sessiz örneklem yok.
