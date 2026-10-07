"""G12 reçete v2 — kapsam kararları satır satır, blanket yok (PLAN-25 §23–§26).

Rol: operatör reçetesinin şeması ve doğrulaması. G12.1b dersi, G11 koşusunun ölçtüğü hatadır:

```text
undecided = tüm kalan callout'lar → bulk ignore → "kapsam tamam"
```

Bu modül o yolu YAPISAL olarak imkânsız kılar: eylemler yalnız reçetede adı geçen kimliklere
uygulanır, "kalanlar" diye bir hedef yoktur ve blanket alan adları (`ignore_rest`,
`bulk_remaining`, `ignore_all_unhandled`) her derinlikte reddedilir. Toplu karar bile kimlikleri
açıkça listelemek zorundadır; koşucu kendiliğinden kimlik EKLEYEMEZ (PLAN-25 §24/§25).

İkinci sınır (PLAN-25 §26): reçete üretici tarafındadır ve referans bilgisi taşıyamaz — referans
bbox/hacim/yüz sayısı/silindir listesi/beklenen özellik sayısı/referans STEP yolu yasaktır. Saf
modül: dosya okur (reçetenin kendisi), ağ/model/referans okumaz.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # kardeş sınır modülü için

import producer_input  # noqa: E402 — G12.0 süreç sınırı: aynı yasak sözlüğü paylaşılır

CALLING_ACTIONS = ("not_model_input", "redundant", "build_relevant_unsupported", "bulk_not_model_input")

FORBIDDEN_RECIPE_FIELDS = ("ignore_rest", "bulk_remaining", "ignore_all_unhandled",
                           "ignore_remaining", "remaining_not_model_input", "close_rest")
"""Blanket kapsam eyleminin alan adları — hangi derinlikte olursa olsun reçete reddedilir."""

# Üretici sınırının yasak alanları (G12.0) + PLAN-25 §26'nın kendi listesi: reçete referans
# bbox/hacim/yüz sayısı/silindir sayısı/beklenen özellik sayısı/referans STEP yolu taşıyamaz.
REFERENCE_FIELDS = tuple(sorted(set(producer_input.FORBIDDEN_FIELDS) | {
    "reference_bbox", "reference_volume", "reference_face_count", "reference_cylinders",
    "expected_feature_count", "reference_step_path"}))
"""Üretici reçetesinde geçemeyecek referans alanları (PLAN-25 §26) — değerlendirici tarafı hariç."""

TOP_FIELDS = ("case_id", "source_sha256", "operator_basis", "callout_actions", "profile_actions",
              "view_decisions", "strategy_decision", "dimension_bindings", "feature_links", "notes")

OPERATOR_BASIS = "source_drawing_only"

CALL_KEYS = ("callout_id", "action", "reason", "duplicate_of")
BULK_KEYS = ("action", "callout_ids", "reason")

STEP_SUFFIXES = (".step", ".stp", ".stl")
"""Üretici reçetesi katı model dosyası adı taşımaz — koşucu hangi STEP'i yazacağını kendisi bilir."""


class RecipeError(ValueError):
    """Reçete sözleşmeye uymuyor — koşu başlamadan durur, sessiz düzeltme yok."""


def _walk(input_value, path: str = ""):
    """(yol, anahtar, değer) üçlüleri — her derinlik; alan adı denetimleri bunun üzerinde koşar."""
    if isinstance(input_value, dict):
        for key, value in input_value.items():
            here = f"{path}.{key}" if path else str(key)
            yield here, str(key), value
            yield from _walk(value, here)
    elif isinstance(input_value, list):
        for index, item in enumerate(input_value):
            yield from _walk(item, f"{path}[{index}]")


def _nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(recipe: dict) -> dict:
    """Şemayı doğrula ve normalize edilmiş bir kopya döndür (PLAN-25 §23–§26)."""
    if not isinstance(recipe, dict):
        raise RecipeError("reçete bir nesne olmalı")
    for path, key, _value in _walk(recipe):
        if key in FORBIDDEN_RECIPE_FIELDS:
            raise RecipeError(f"blanket kapsam eylemi yasak (PLAN-25 §24): {path}")
        if key in REFERENCE_FIELDS:
            raise RecipeError(f"reçete referans alanı taşıyamaz (PLAN-25 §26): {path}")
    unknown = [key for key in recipe if key not in TOP_FIELDS]
    if unknown:
        raise RecipeError(f"bilinmeyen reçete alanı: {', '.join(sorted(unknown))}")
    if not _nonempty(recipe.get("case_id")):
        raise RecipeError("case_id zorunlu")
    sha = recipe.get("source_sha256")
    if not _nonempty(sha) or len(str(sha)) != 64 or any(c not in "0123456789abcdef" for c in str(sha)):
        raise RecipeError("source_sha256 zorunlu (64 hex)")
    if recipe.get("operator_basis") != OPERATOR_BASIS:
        raise RecipeError(f"operator_basis '{OPERATOR_BASIS}' olmalı: reçete yalnız kaynak çizime dayanır")
    actions = recipe.get("callout_actions")
    if not isinstance(actions, list):
        raise RecipeError("callout_actions bir liste olmalı (boş olabilir)")
    normalized = [validate_action(item, index) for index, item in enumerate(actions)]
    for field in ("profile_actions", "view_decisions", "dimension_bindings", "feature_links"):
        value = recipe.get(field)
        if value is not None and not isinstance(value, list):
            raise RecipeError(f"{field} bir liste olmalı (bu sürümde boş)")
    strategy = recipe.get("strategy_decision")
    if strategy is not None and not isinstance(strategy, dict):
        raise RecipeError("strategy_decision nesne ya da null olmalı")
    notes = recipe.get("notes") or []
    if not isinstance(notes, list) or any(not isinstance(item, str) for item in notes):
        raise RecipeError("notes metin listesi olmalı")
    return {"case_id": recipe["case_id"], "source_sha256": str(sha),
            "operator_basis": OPERATOR_BASIS, "callout_actions": normalized,
            "profile_actions": list(recipe.get("profile_actions") or []),
            "view_decisions": list(recipe.get("view_decisions") or []),
            "strategy_decision": strategy, "dimension_bindings": list(recipe.get("dimension_bindings") or []),
            "feature_links": list(recipe.get("feature_links") or []), "notes": list(notes)}


def validate_action(item, index: int) -> dict:
    """Tek bir kapsam eylemi: her satır açık (callout_id, action, reason) ya da açık id listeli toplu."""
    where = f"callout_actions[{index}]"
    if not isinstance(item, dict):
        raise RecipeError(f"{where}: eylem bir nesne olmalı")
    action = item.get("action")
    if action in FORBIDDEN_RECIPE_FIELDS:
        raise RecipeError(f"{where}: blanket kapsam eylemi yasak (PLAN-25 §24): {action}")
    if action not in CALLING_ACTIONS:
        raise RecipeError(f"{where}: bilinmeyen eylem {action!r} (izinli: {', '.join(CALLING_ACTIONS)})")
    if not _nonempty(item.get("reason")):
        raise RecipeError(f"{where}: her eylem gerekçe taşır (PLAN-25 §25)")
    if action == "bulk_not_model_input":
        unknown = [key for key in item if key not in BULK_KEYS]
        if unknown:
            raise RecipeError(f"{where}: toplu eylemde bilinmeyen alan: {', '.join(sorted(unknown))}")
        ids = item.get("callout_ids")
        if not isinstance(ids, list) or not ids:
            raise RecipeError(f"{where}: toplu karar kimlik listesi olmadan yazılamaz — "
                              f"koşucu kendiliğinden kimlik eklemez (PLAN-25 §25)")
        if any(not _nonempty(value) for value in ids):
            raise RecipeError(f"{where}: callout_ids boş ya da metin olmayan kimlik taşıyor")
        if len(set(ids)) != len(ids):
            raise RecipeError(f"{where}: callout_ids yinelenen kimlik taşıyor")
        for value in ids:
            _reject_model_file(value, where)
        return {"action": action, "callout_ids": [str(value) for value in ids],
                "reason": str(item["reason"]).strip()}
    unknown = [key for key in item if key not in CALL_KEYS]
    if unknown:
        raise RecipeError(f"{where}: bilinmeyen alan: {', '.join(sorted(unknown))}")
    if not _nonempty(item.get("callout_id")):
        raise RecipeError(f"{where}: callout_id zorunlu — satır satır karar (PLAN-25 §25)")
    _reject_model_file(str(item.get("callout_id")), where)
    row = {"callout_id": str(item["callout_id"]), "action": action, "reason": str(item["reason"]).strip()}
    if action == "redundant":
        if not _nonempty(item.get("duplicate_of")):
            raise RecipeError(f"{where}: 'redundant' dayanağını yazmak zorunda (duplicate_of)")
        row["duplicate_of"] = str(item["duplicate_of"]).strip()
    elif item.get("duplicate_of") is not None:
        raise RecipeError(f"{where}: duplicate_of yalnız 'redundant' ile anlamlı")
    return row


def _reject_model_file(value: str, where: str) -> None:
    if str(value).lower().endswith(STEP_SUFFIXES):
        raise RecipeError(f"{where}: reçete katı model dosyası adı taşıyamaz: {value!r}")


def load(path) -> dict:
    """Reçeteyi oku ve doğrula (PLAN-25 §23)."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise RecipeError(f"reçete JSON değil: {error}") from error
    return validate(raw)


def planned_actions(recipe: dict) -> list[dict]:
    """Reçetenin koşucuya söylediği istekler — TAM liste; kalan satırlar için istek YOK.

    Bu fonksiyonun sözleşmesi PLAN-25 §24'ün ta kendisidir: çıktı yalnız reçetedeki kimliklerden
    doğar. "Kalan her şeyi kapsam dışı ilan et" diye bir istek üretilemez, çünkü böyle bir hedef
    şemada yoktur.
    """
    requests: list[dict] = []
    for item in recipe.get("callout_actions") or []:
        if item["action"] == "bulk_not_model_input":
            requests.append({"http_action": "bulk_set_ignored",
                             "payload": {"callout_ids": list(item["callout_ids"]), "ignored": True},
                             "reason": item["reason"]})
        else:
            payload = {"callout_id": item["callout_id"], "disposition": item["action"],
                       "disposition_reason": item["reason"]}
            if item["action"] == "redundant":
                payload["duplicate_of"] = item["duplicate_of"]
            requests.append({"http_action": "set_disposition", "payload": payload,
                             "reason": item["reason"]})
    return requests


__all__ = ["CALLING_ACTIONS", "FORBIDDEN_RECIPE_FIELDS", "REFERENCE_FIELDS", "RecipeError",
           "load", "planned_actions", "validate", "validate_action"]
