# 2026-09-29 goal denetimi — küçük kanıtlar

Bu dosyalar üretim mantığı değildir. Depo kökünden `PYTHONPATH=src .venv/bin/python <script>` ile çalıştırılabilir.

- `contour_probes.py/.jsonl`: beş yanlış kontur kararı ve bir yansıma kontrolü; girdiler/beklentiler/çıktılar.
- `audit_geometry_state_probe.py/.txt`: geçiş kimliği, eski bağ, boş profil ve güncel çıktı kusurları. Bu script mevcut hatalı sonucu assert eder; düzeltmeden sonra assertion kırılması beklenir.
- `constraints_ui_probe.py/.json`: HTML düğmeleri, kalibrasyon, ölçü kapısı, referans ve unsupported plan.
- `focused-tests.txt`: 90 passed + sandbox port izni nedeniyle 1 failed.
- `http-retest.txt`: aynı HTTP testinin izinli localhost koşusunda 1 passed.
- `source-snapshot.json`: denetimin başlangıcındaki kaynak/test SHA256 özetleri.

Kalıcı regresyon testi yazarken kusurlu davranışı beklenen sonuç olarak taşımayın. Bu dosyalardaki sayılar bağımsız denetim girdileridir; üretim kodunda özel duruma dönüştürülmez. Kaynak kod değiştikçe yeni çıktı eski denetim kaydının üzerine yazılmadan ayrı bir koşuda tutulmalıdır.
