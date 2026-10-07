# G12R — gerçek Chrome kabul koşusu (R-01 + R-02)

UX değişti (yeni kategori metni, onayın bağlandığı bağlam), bu yüzden kabul **gerçek tarayıcıda**:
`ui_acceptance.py` taze Plate oturumunu (kapsam kapalı, üretim biçimi seçilmemiş) kullanıcının kendi
yolundan yürür — gerçek fare tıklamaları, gerçek klavye, isteklerin `fetch` gözlemi.

Sonuç: **11/11 PASS, EXIT=0** (`ui-run.log`, `ui-acceptance-steps.json`).

| Adım | Ne ölçüldü | Sonuç |
| --- | --- | --- |
| **A** | kapsam kapalı, üretim biçimi seçilmemiş → üretim düğmesi kapalı | PASS (`missing_build_strategy: 1`, `build_disabled: true`) |
| **B** | gerçek tıklamayla `extrude_profile` onayı; istek gövdesi **yalnız** `{token, revision, kind}`; anahtarı/sürümü sunucu yazdı | PASS (`strategy_key` 64 hane, gövde anahtarları `[kind, revision, token]`) |
| **C** | **R-01**: onaydan SONRA kalınlık 20 + «Kalınlığı kaydet» → normal kayıt **geçti** (tarayıcı JSON turu sahte sayılmıyor) | PASS (durum «Karar kaydedildi.», `strategy_key_kept: true`) |
| **C2** | **R-02 (değer ayağı)**: kalınlık 20 olunca kalınlığa dayanan onay düştü — soru metni «…seçilen dayanak («decision:thickness») artık güncel değil.» | PASS (1 soru, `invalid_duplicate: 1`) |
| **D** | **R-01**: profil değişince karar güncelliğini yitirdi → hazırlık stratejiyi yeniden sordu (`stale_build_strategy: 1`), üretim kapandı; profil geri alınıp karar yeniden onaylanınca soru kapandı | PASS (iki kayıt) |
| **D2** | kalınlık 15'e dönünce onay sabitlendiği değere yeniden eşit oldu → kapsam kapandı, üretim açıldı | PASS (`invalid_duplicate: 0`, kategori yok) |
| **E** | **R-02 (okuma ayağı)**: «zaten temsil ediliyor» satırı listeden gerçek tıklamayla seçildi, metni `30,00` yapıldı → satırın **kendi okuması** değiştiği için onay düştü (`stale: 1`), üretim kapandı | PASS (2 kayıt) |
| **F** | aynı satır aynı dayanakla yeniden onaylandı → kapsam kapandı; onayın **kanıtını sunucu yazdı** (`kind: callout`, `revision: 3`) | PASS |
| **G** | düzeltmelerden sonra gerçek tıklamayla üretim tamamlandı; STEP servis edildi (`ISO-10303-21`, 52.008 bayt) | PASS |

## Ekran görüntüleri

| Dosya | Ne gösterir |
| --- | --- |
| `R-00-open.png` | taze oturum: kapsam kapalı, üretim biçimi seçilmemiş, üretim düğmesi kapalı |
| `R-01-thickness-saved.png` | R-01: onaydan sonra kalınlık 20 kaydedildi (durum «Karar kaydedildi.») |
| `R-02-value-stale.png` | C2 anı: kalınlık 20; kalınlığa dayanan onay düştü (soru sunucu kaydında listeli) |
| `R-01-stale.png` | D: profil değişti → strateji güncelliğini yitirdi, üretim kapalı |
| `R-02-claim-stale.png` | E: satırın metni `30,00`; panel «Zaten başka bir bilgiyle temsil ediliyor (dayanak: 0f5ccd0e…). **Okuma değişti: kararı yeniden onaylayın.**» diyor |
| `R-02-re-approved.png` | F: yeniden onay sonrası kapsam kapandı, üretim açık |
| `R-03-built.png` | G: üretim tamamlandı, STEP bağlantısı görünür |

## Notlar

- Kararlar komutla verilmez: `Runtime.evaluate` yalnız durumu OKUR ve `fetch` gövdesini gözlemler;
  düğmelere `Input.dispatchMouseEvent`, metin kutusuna gerçek klavye olaylarıyla yazılır. Açılır
  listeler (profil/dayanak seçimi) için değer + `change` olayı yayınlanır — olayın kendisi ürünün
  kendi işleyicisini çalıştırır.
- Panel etiketleri (`C1`, `C8`…) istemcide üretilir; satır seçimi sunucunun verdiği etkin liste
  sırasıyla eşleştirilip DOM'dan doğrulanır.
- Koşu, sonda tarayıcı sekmesini kapatır; uygulama sunucusu bu dizindeki kanıt için yeniden
  başlatılabilir (`PYTHONPATH=src .venv/bin/python -m drawingto3d.app`).
