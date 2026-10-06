# G6 hedef onayı — gerçek tarayıcı kabulü (PLAN §11)

Bu klasör G6'nın kabul kanıtıdır: hedef onayı akışı **gerçek Chrome** üzerinde, gerçek tıklama ve
yazma olaylarıyla yürütüldü. Test kodu kullanıcı cevabını oturuma enjekte etmez; her adım ya bir
fare/tuş olayıdır ya da sunucunun kendi kaydının okunmasıdır.

## Nasıl koşulur

```bash
# 1) uygulama
PYTHONPATH=src .venv/bin/python -m drawingto3d.app          # 127.0.0.1:8765

# 2) Chrome (ayrı profil, uzak hata ayıklama açık)
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-g6 --headless=new

# 3) kabul
~/.hermes/cache/scratch/cdp-venv/bin/python g6_target_acceptance.py
```

CDP istemcisi ve sayfa yardımcıları **kopyalanmadı**: `../20261006-guided-g3-review/` altındaki tek
ortak harness (`cdp_client.py`, `browser_acceptance.py`) yol üzerinden kullanılır — iki farklı sürücü
tutmak kabulün neyi sürdüğünü belirsizleştirirdi.

## Sonuç: 17/17 adım geçti

`g6-steps.json` her adımın kanıtını, konsol kayıtlarını ve reddedilen istekleri taşır.

| Adım | Kanıt |
|---|---|
| çizim açıldı | 45 callout alanı listelendi (`Plate With A Pocket`) |
| callout seçildi | daireye en yakın bölge gerçek tıklamayla seçildi |
| metin kaydedildi | `Ø8 THRU` yazıldı; öneriler ayrı bir okumayla geldi |
| öneri vurgusu | öneri satırına tıklama tuvalin gerçek piksellerini değiştirdi |
| **Onayla** | kayıt: `target_kind=circle`, `target_ids=[g61]`, `evidence[0].kind=proposal` (`T3`), `status=confirmed` |
| panel | “Onaylı: tek daire · g61 · · T3 · g61” |
| yeniden açılış | onay kayıttan geldi, durum `hedef güncel` |
| geometri değişimi | kontur `outline_1`'e alındı → `hedef eskidi (geometry_changed)` |
| hazırlık kapısı | bekleyen sorular listelendi, üretim düğmesi kapandı |
| elle seçim | `Başka hedef seç` + çizimde daireye tıklama → panelde birikti |
| **Seçimi onayla** | yeni onay `evidence[0].kind=user_click`, `profile_id=outline_1` (yeni geometri anahtarı) |
| geri alma | son onay geri alındı, kayıt tarihsel sürümüne döndü |
| yeniden açılış | geri alma sonrası durum tutarlı |
| inceleme paketi | indirme düğmesi çalıştı; paket 45 callout ve `raw_text=Ø8 THRU` taşıdı |
| konsol | beklenmeyen hata yok, reddedilen istek yok |

Ekran görüntüleri: `g6-00-proposal.png`, `g6-01-confirmed.png`, `g6-02-reopened.png`,
`g6-03-stale.png`, `g6-04-picked.png`, `g6-05-panel.png`.

## Açık bulgu (G9'a taşınır)

Paftada 45 metin bölgesi var; G8 hazırlığı **her bölge için bir karar** bekliyor (metin ya da
“bu callout değil”). Antet/çerçeve metinleri için bu, elle 40+ karar demek.  Bu turda hiçbir şey
sessizce düşürülmedi (44 bölge “metin yazın” olarak listede duruyor) — ama G9'un Plate altın yolu
bu yüzden yavaş ilerler. Seçenekler: (a) G9'da toplu “seçilenleri yok say” eylemi (kullanıcı
seçimiyle, sessiz filtre değil), (b) dedektörün antet bölgesini ayrı sınıflandırması (G2 kararı,
yeniden açılması gerekir).
