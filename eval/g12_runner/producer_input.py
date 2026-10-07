"""G12 üretim/ölçüm süreç sınırı (PLAN-24 §8) — üretici referansı göremez.

G12 koşucusu iki aşamaya ayrılır:

```text
produce_case.py    → kaynak çizim + kullanıcı kararları (referans YOK)
evaluate_case.py   → üretilen STEP + tam manifest girdisi + referans STEP
```

Bu modül sınırın kendisidir: manifest girdisinden üretici görünümünü beyaz listeyle süzer ve bir
üretici yükünde (girdi JSON'u, süreç ortamı ya da argv) referans yolu veya yasak alan geçerse açıkça
patlar — sessiz sızma yok. Saf: ne yazar ne okur; yalnız süzer ve denetler.
"""
from __future__ import annotations

import json

PRODUCER_FIELDS = (
    "case_id", "source_path", "format", "source_kind", "expected_scope_class",
    "page_index", "view", "source_sha256",
)
"""Üreticiye taşınabilen alanlar — beyaz liste; manifest'in geri kalanı sınırın dışında kalır.

`source_sha256` üretici tarafında meşrudur: sürücü dosyanın kendisini doğrular, geometri bilgisi
taşımaz. `tags`/`note`/`prior_exposure` değerlendirme sınıflandırmasıdır (PLAN-24 §117) ve üreticiye
taşınmaz.
"""

FORBIDDEN_FIELDS = (
    "reference_identifier_evaluator_only", "reference_path", "reference_available",
    "expected_bbox", "expected_volume", "reference_radii", "reference_feature_count",
)
"""Üretici yükünde geçemeyecek alan adları (PLAN-24 §8/§65); JSON'un her derinliğinde denetlenir."""


class ReferenceLeakage(AssertionError):
    """Üretici sürecine referans bilgisi sızmış — koşu burada durur, sessizce devam etmez."""


def producer_view(entry: dict) -> dict:
    """Bir manifest girdisinin üretici görünümü: beyaz liste; referans alanları hiç girmez."""
    return {field: entry.get(field) for field in PRODUCER_FIELDS}


def reference_values(manifest: dict) -> list[str]:
    """Manifestteki bütün referans kimlikleri (yol ya da null) — sınır denetiminin sözlüğü."""
    values = []
    for entry in manifest.get("cases") or []:
        value = entry.get("reference_identifier_evaluator_only")
        if value:
            values.append(str(value))
    return values


def _walk_keys(payload, path: str = "") -> list[str]:
    """JSON yapısındaki bütün anahtar yolları (`a.b[0].c` gibi) — alan adı denetimi için."""
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            here = f"{path}.{key}" if path else str(key)
            found.append(here)
            found.extend(_walk_keys(value, here))
    elif isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            found.extend(_walk_keys(value, f"{path}[{index}]"))
    return found


def assert_reference_free(payload, *, reference_values: list[str], where: str) -> None:
    """`payload` (JSON'a çevrilebilir her yapı) referans taşımıyorsa döner, taşıyorsa patlar.

    İki soru sorulur ve ikisi de *yalnız* sınırın kendi kuralıdır (vaka adına göre dallanma yok):

    * anahtar adı `FORBIDDEN_FIELDS` içinde mi ya da `reference` ile başlıyor mu;
    * serileştirilmiş metin bir referans kimliğini (tam yol ya da dosya adı) içeriyor mu.
    """
    keys = _walk_keys(payload)
    for key_path in keys:
        leaf = key_path.rsplit(".", 1)[-1].split("[")[0]
        if leaf in FORBIDDEN_FIELDS or leaf.lower().startswith("reference"):
            raise ReferenceLeakage(f"{where}: yasak alan adı üretici yükünde: {key_path}")
    blob = json.dumps(payload, ensure_ascii=False, default=str)
    lowered = blob.lower()
    for value in reference_values:
        needle = str(value)
        for token in {needle, needle.rsplit("/", 1)[-1]}:
            if token and token.lower() in lowered:
                raise ReferenceLeakage(f"{where}: referans değeri üretici yükünde: {token!r}")


__all__ = ["FORBIDDEN_FIELDS", "PRODUCER_FIELDS", "ReferenceLeakage", "assert_reference_free",
           "producer_view", "reference_values"]
