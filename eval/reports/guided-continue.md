# Yönlendirmeli akış: devam kanıtı — 2026-09-28

Kullanıcı %15 kullanılabilir pay kalana kadar devam istedi. Başlangıçta beş saatlik kullanım %7, haftalık %63; son eşik kontrolünde beş saatlik kullanım %86 (%14 kaldı), haftalık %75 oldu. Yeni kapsam durduruldu; yalnız son doğrulama ve kayıt tamamlandı. Genel hedef tamamlanmadı.

### Bu turda doğrulanan ve değişen

- Önceki devirden sonra §24 öneri/günlük ve flanş kodları eklenmişti; korundu. Temiz arayüz oturumunda gerçek PDF yüklendi; öneriler onaylandı; üretim tamamlandı, STEP ve önizleme bağlantıları göründü. Oturum: `8bf7ba9f1e1e4039b4cb839b53b6b161`, revizyon 2, `build-2-e3ac2ef2`.
- `GuidedStore.accept`: tek cep onayı kullanıcının mevcut derinliğini korur. Yeni cep seçilmemiş derinlik önerisini sessizce kullanmaz; gerekli kararı ister. Yalnız derinlik onayı mevcut cepleri günceller; cep yoksa açıklayıcı hata verir. Günlük gerçekten kaydedilen derinliği gösterir.
- `_proposal_note`: basılı ölçü kimliği taşımayan geometrik öneri çizim açılışını artık çökertmez.
- Odaklı `test_guided.py + test_guided_proposals.py + test_advise.py`: **45 geçti / 36,61 sn**. Tam takım bu turda yeniden çalıştırılmadı.
- Yeni `sketch_constraints.py`: kapalı çizgi konturları için X/Y mesafe bağları, yatay/dikey ilişkiler, datum, çelişki ve serbestlik raporu, GeneralPlan kaynak ifadeleri. Yaylı/daire dış konturda yalnız seçilmiş daire merkezleri kapsamı. **Arayüze ve guided.make_plan'a bağlanmadı.** `test_sketch_constraints.py`: **22 geçti / 4,37 sn** (bağımsız STEP boyut/merkez testi dahil). Entegrasyon öncesi API ve kaynak ifadelerini ayrıca gözden geçir.

### Açık sınırlar ve tek sonraki iş

Mevcut kullanıcı akışı hâlâ pikselden izlenen taslak üretir. Yeni çözücünün varlığı mevcut STEP'leri kesin ölçülü yapmaz. Önce çözücüyü küçük bir entegrasyonla `Decisions` / `make_plan` / kayıt-geri alma akışına ve kullanıcı ölçü bağlama arayüzüne bağla; desteklenmeyen yay kısıtlarını açık göster. Bütün noktaların kaynağını ve kalan serbestlikleri koru, çelişkide üretimi engelle. Önce bozuk piksel dikdörtgeni ve delik merkezini bağımsız CAD ölçüsüyle doğrula; sonra gerçek parçaya genişlet.

Arayüzde tıklama ile kalibrasyonun elle tamamlandığı kabulü hâlâ açık: bu turdaki CUA koordinatları/ekran görüntüsü arasında uyuşmazlık vardı; seçilen piksel mesafesi beklenenle uyuşmadı. Bunun uygulama mı otomasyon eşlemesi mi olduğu ayrıştırılmadı. Menü/düğmeler klavyeyle çalıştı; öneri onayı ve STEP üretimi doğrulandı. Manuel akışı tamamlandı sayma. Nihai UI ekran görüntüsü dosyaya kaydedilmedi. Süre kazancı ve görülmemiş parçalar doğrulanmadı.

### Dosyalar ve yeniden başlatma

Kanıt: `eval/reports/guided-continue.md`, test günlükleri `out/guided-dev-continue/`. Yedek: `out/checkpoints/guided-latest.json`. Önceden var olan değişiklikleri koru; Git sıfırlama yapma.

`PYTHONPATH=src .venv/bin/python -m drawingto3d.app` → `http://127.0.0.1:8765/guided`. Bu turdaki geçici sunucu 55096 portundaydı; backend düzeltmelerinden önce başlatıldı. Güncel düzeltmeleri kullanmak için sunucuyu yeniden başlat. Kayıtlı oturum query parametresiyle açılır. Model eğitimi veya ağırlık indirme yapılmadı.

