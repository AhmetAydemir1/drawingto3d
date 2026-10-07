"""G12.2 — taze Plate oturumu kabulü (PLAN-25 §44).

Akış, kullanıcının akışıdır; hiçbir adım atlanmaz:

```text
callout'ları incele  →  stratejiyi AÇIKÇA onayla  →  üret  →  STEP'i yeniden aç  →  dondurulmuş evaluator
```

Çizim: `examples/pdf with steps/5/Plate With A Pocket Drawing.PDF`. Callout kararları G11'deki resmî
plate reçetesinin (birebir; ipuçlarıyla eşleşir) satır satır kararlarıdır: her satır kendi gerekçesini
taşır, hiçbir satır toplu/örtük kapatılmaz. Üretim biçimi ayrı ve açık bir kullanıcı kararıdır
(PLAN-25 §32): `extrude_profile`.

Karar bu değil, KAYIT ölçülür: dondurulmuş evaluator
`eval/audits/20261007-guided-g9-plate/plate_regression.py` (G12.0'daki tolere birebir) üretilen
STEP'i bağımsız formülle değerlendirir ve `120 × 80 × 15`, 4 delik, 1 cep bekler.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import build_strategy, callout_readiness                       # noqa: E402
from drawingto3d.guided import GuidedStore                                      # noqa: E402

PLATE = ROOT / "examples/pdf with steps/5/Plate With A Pocket Drawing.PDF"
REFERENCE_STEP = ROOT / "examples/pdf with steps/5/plate with a pocket.STEP"
EVALUATOR = ROOT / "eval/audits/20261007-guided-g9-plate/plate_regression.py"
CAD_PYTHON = ROOT / ".venv-cad/bin/python"

# G11 resmî plate reçetesi, satır satır; G12 sözlüğüyle (PLAN-25 §9–§13). Her satır kendi gerekçesini
# taşır, hiçbir satır örtük kapanmaz. "Gerçek ölçü ama uygulanamıyor" YALNIZ gerçekten uygulanamayan
# satıra ayrılır ve üretimi bloklar; zaten başka bir kararla temsil edilen satır bunu SÖYLER (dayanak).
CALL_RECIPE = [
    {"hint": "4 x", "action": "not_model_input",
     "why": "sayı parçası: metni '6,80 THRU ALL' kutusuyla birlikte okundu, kendi başına ölçü değil"},
    {"hint": "6,80 THRU ALL", "action": "transcribe", "text": "4 x Ø6,80 THRU ALL",
     "target": {"kind": "circle_group", "circles": ["g9", "g11", "g10", "g12"]},
     "why": "bileşik metin: '4 x' çizimde çapın yanında basılı; hedef dört daire"},
    {"hint": "50,00", "action": "transcribe", "text": "Ø50 8 DEEP",
     "target": {"kind": "circle", "circles": ["g8"]},
     "why": "bileşik: Ø50 görünüşten, derinlik 8 kesitten"},
    {"hint": "M8 - 6H THRU ALL", "action": "redundant", "cite_hint": "6,80 THRU ALL",
     "why": "aynı dört delik: M8 dişin pilot çapı 6,8 mm — bu satır Ø6,80 kararıyla zaten temsil ediliyor"},
    {"hint": "80,00", "action": "redundant", "cite": "decision:trace",
     "why": "izlenen merkezler bu basılı aralığı zaten gerçekliyor (80,002 mm); yeni karar getirmiyor"},
    {"hint": "60,00", "action": "redundant", "cite": "decision:trace",
     "why": "aynı: izlenen merkezler 60,00 mm aralığı zaten sağlıyor"},
    {"hint": "8,00", "action": "redundant", "cite": "decision:trace",
     "why": "kesitteki basılı kalınlık okuması; izleme ve kalınlık kararı zaten temsil ediyor"},
    {"hint": "1 00,00", "action": "redundant", "cite": "decision:calibration",
     "why": "kalibrasyon bu aralıktan 100,00 olarak girildi (yazım boşluğu düzeltilerek)"},
    {"hint": "1 5,00", "action": "redundant", "cite": "decision:thickness",
     "why": "kalınlık bu ölçüden 15,00 olarak girildi (yazım boşluğu düzeltilerek)"},
]

STEPS: list[dict] = []

# Üst veri ve ölçü parçaları: kullanıcı bunları "modele ait değil" diye adıyla işaretler. Bu liste
# reçetenin dışında kalan satırlar içindir ve GEREKÇE GRUPLARI paftanın kendi okumasından türer —
# hiçbir satır sessizce kapatılmaz (PLAN-25 §24).
TITLE_BLOCK_HINTS = {"A4", "ALLOY STEEL", "DRAFTCRAFT", "MATERIAL:", "NAME:", "PRO",
                     "Plate With A Pocket", "SCALE1:1", "SECTION B-B", "SHEET 1 OF 1", "TITLE:",
                     "WEIGHT:", "date:", "2026"}
MARKER_HINTS = {"A", "B", "C", "D"}
FRAGMENT_HINTS = {"1", "2", "3", "4", "5", "6"}

FALLBACK_REASON = "basılı ölçünün parçası (kendi kutusunda okundu)"


def _reason_for(hint: str) -> str:
    if hint in TITLE_BLOCK_HINTS:
        return "başlık bloğu: çizim üst verisi, parça geometrisi değil"
    if hint in MARKER_HINTS:
        return "görünüş/bölüm işareti (SECTION B-B çizimi), parça geometrisi değil"
    if hint in FRAGMENT_HINTS:
        return "basılı ölçünün kendi kutusundaki parçası"
    return FALLBACK_REASON



def record(name: str, passed: bool, detail: dict) -> None:
    STEPS.append({"step": name, "passed": bool(passed), "detail": detail})
    print(("PASS " if passed else "FAIL ") + name + "  " + json.dumps(detail, ensure_ascii=False)[:220])


def _hints(record: dict) -> dict[str, list[str]]:
    """İpucu → callout kimlikleri: eşleşme kaydın KENDİ adaylarından okunur (uydurulmuş kimlik yok).

    Aynı ipucu birden çok satırda görünebilir (pafta aynı metni iki kez basar): o zaman hepsi karara
    girer — tek satırlık bir eşleşme diğerlerini sessizce açıkta bırakırdı.
    """
    found: dict[str, list[str]] = {}
    for row in record.get("callout_candidates") or []:
        found.setdefault((row.get("machine_text_hint") or "").strip(), []).append(row["id"])
    return found


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    """İki kip: tam kabul (varsayılan) ve `--prepare-only` (gerçek tarayıcı koşusu için oturum hazırlar).

    `--prepare-only --store-root <dizin>`: kararlar uygulamanın KENDİ deposuna yazılır, kapsam kapanır
    ve komut `{"token": …, "revision": …}` basıp çıkar — üretim biçimi ve üretim TARAYICIDA kalır
    (PLAN-25 §97/8: UX değiştiyse gerçek Chrome koşusu).
    """
    argv = sys.argv[1:]
    prepare_only = "--prepare-only" in argv
    landing = pathlib.Path(__file__).resolve().parent
    if prepare_only:
        out = pathlib.Path(argv[argv.index("--store-root") + 1]) if "--store-root" in argv \
            else landing / "out" / "store"
        out.mkdir(parents=True, exist_ok=True)
        store = GuidedStore(out)
    else:
        out = landing / "out"
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        store = GuidedStore(out / "store")
    opened = store.create(PLATE.read_bytes())
    token = opened["token"]
    options = opened["options"]

    # --- 0. geometri kararları: kontur, ölçek (100,00), kalınlık, izleme onayı -------------------
    profile_id = "outline_1"
    assert any(row["id"] == profile_id for row in options["profiles"]), "plate konturu bulunamadı"
    span = next((row for row in options["measurements"] if row.get("text", "").strip() == "1 00,00"), None)
    circles = {row["id"]: row for row in options["circles"]}
    first, second = circles["g9"]["center"], circles["g11"]["center"]
    decisions = {
        "calibration": {"first": list(first), "second": list(second), "value": 100.0, "unit": "mm",
                        "span_id": (span or {}).get("id")},
        "profile_id": profile_id, "thickness": 15.0, "trace_acknowledged": True, "bindings": [], "holes": []}
    revision = store.save(token, opened["revision"], decisions)["revision"]
    record("0: kontur + ölçek (100,00) + kalınlık (15) + izleme onayı kaydedildi",
           True, {"revision": revision, "profile_id": profile_id, "span_id": decisions["calibration"]["span_id"]})

    # --- 1. callout incelemesi: reçetedeki her satır kendi gerekçesiyle --------------------------
    rows = _hints(store.load(token))
    missing = [item["hint"] for item in CALL_RECIPE if item["hint"] not in rows]
    record("1: reçetedeki her ipucu bu paftanın callout'larından biriyle eşleşti",
           not missing, {"hints": len(rows), "missing": missing, "rows": rows})
    if missing:
        return _finish(landing, out, passed=False)

    def decide(callout_id: str, action: str, reason: str, text: str | None = None,
               target: dict | None = None, duplicate_of: str | None = None) -> None:
        revision = store.load(token)["revision"]
        if text is not None:
            store.edit_callout(token, revision, "transcribe", {"callout_id": callout_id, "raw_text": text})
            revision = store.load(token)["revision"]
        if action == "transcribe":
            target = target or {}
            if target.get("unbindable"):
                # Metin düzeltilir; hedefi YOK — satır "gerçek ölçü/not ama bu sürüm uygulayamıyor"
                # olarak adıyla işaretlenir (reçetenin kendi gerekçesiyle).
                store.edit_callout(token, store.load(token)["revision"], "set_disposition",
                                   {"callout_id": callout_id, "disposition": "build_relevant_unsupported",
                                    "disposition_reason": reason})
                return
            record_now = store.load(token)
            transcription = next(entry for entry in record_now["decisions"]["transcriptions"]
                                 if entry["callout_id"] == callout_id)
            parse_row = next((entry for entry in record_now.get("callout_parses") or []
                              if entry["callout_id"] == callout_id), {})
            payload = dict(record_now["decisions"])
            payload["callout_targets"] = [entry for entry in payload.get("callout_targets") or []
                                          if entry["callout_id"] != callout_id]
            payload["callout_targets"].append({
                "callout_id": callout_id, "target_kind": target["kind"], "target_ids": list(target["circles"]),
                "transcription_revision": transcription.get("revision"),
                "parser_version": parse_row.get("parser_version"),
                "evidence": [{"kind": "user_click",
                              "ref": f"{target['kind']} · {', '.join(target['circles'])}"}],
                "reconfirm": False})
            store.save(token, revision, payload)
            return
        payload = {"callout_id": callout_id, "disposition": action, "disposition_reason": reason}
        if action == "redundant":
            payload["duplicate_of"] = duplicate_of
        store.edit_callout(token, revision, "set_disposition", payload)

    def citation(item: dict) -> str | None:
        """Dayanak: başka bir callout'un kimliği ya da kullanıcının kendi kararı (`decision:<ad>`)."""
        if item.get("cite_hint"):
            cited = rows.get(item["cite_hint"]) or []
            assert cited, f"dayanak satırı bulunamadı: {item['cite_hint']}"
            return cited[0]
        return item.get("cite")

    for item in CALL_RECIPE:
        for callout_id in rows[item["hint"]]:
            decide(callout_id, item["action"], item["why"], text=item.get("text"),
                   target=item.get("target") if item["action"] == "transcribe" else None,
                   duplicate_of=citation(item))

    # --- 1b. reçetenin dışında kalan satırlar: kullanıcı onları da ADIYLA karara bağlar -----------
    decided = {row["callout_id"] for row in store.load(token)["decisions"]["callout_reviews"]}
    decided |= {row["callout_id"] for row in store.load(token)["decisions"].get("callout_targets") or []}
    remaining = {hint: [callout_id for callout_id in ids if callout_id not in decided]
                 for hint, ids in rows.items()}
    remaining = {hint: ids for hint, ids in remaining.items() if ids}
    open_ids = [callout_id for ids in remaining.values() for callout_id in ids]
    for hint, ids in remaining.items():
        for callout_id in ids:
            decide(callout_id, "not_model_input", _reason_for(hint))
    record("1b: reçete dışındaki satırlar da tek tek adıyla karara bağlandı (örtük kapatma yok)",
           True, {"remaining_rows": len(open_ids), "groups": sorted(remaining), "decided": len(decided)})

    readiness = callout_readiness.build_readiness(store.load(token))
    categories = readiness["categories"]
    record("2: kapsam kapandı — kalan tek madde ÜRETİM BİÇİMİ, hiçbir callout sorusu yok",
           categories == {"missing_build_strategy": 1} and not [q for q in readiness["questions"] if q["callout_id"]],
           {"categories": categories, "questions": len(readiness["questions"])})
    if prepare_only:
        # Tarayıcı koşusu buradan devam eder: ölçülen oturum, app'in kendi deposunda, tam bu hâlde.
        print(json.dumps({"token": token, "revision": store.load(token)["revision"],
                          "store": str(out), "categories": categories}, ensure_ascii=False))
        return 0
    record("3: strateji yokken üretim BAŞLAMAZ (örtük extrude yok)",
           not readiness["ready"], {"ready": readiness["ready"]})
    try:
        store.build(token, store.load(token)["revision"])
        refusal = None
    except ValueError as error:
        refusal = str(error)
    record("4: build çağrısı strateji yokken reddedildi (adı konmuş soruyla)",
           refusal is not None and "oluşturma biçimini seçin" in refusal,
           {"refusal": (refusal or "")[:180]})

    # --- 2. AÇIK strateji kararı ----------------------------------------------------------------
    store.set_strategy(token, store.load(token)["revision"], {"kind": "extrude_profile"})
    record_ = store.load(token)["decisions"]["build_strategy"]
    record("5: kullanıcı üretim biçimini onayladı — sunucu anahtarı ve geometri sürümünü sabitledi",
           build_strategy.strategy_state(store.load(token)) == "current"
           and record_["kind"] == "extrude_profile" and len(record_["strategy_key"]) == 64
           and record_["geometry_version"] == store.load(token)["geometry_version"],
           {"kind": record_["kind"], "strategy_key": record_["strategy_key"][:12] + "…",
            "geometry_version": record_["geometry_version"]})

    # --- 3. üretim ------------------------------------------------------------------------------
    state = store.build(token, store.load(token)["revision"])
    build = state.get("build") or store.load(token)["build"]
    step_path, _entry = store.artifact(token, "part.step")
    geometry = json.loads((pathlib.Path(build["folder"]) / "geometry.json").read_text())
    radii = sorted(round(row[0], 3) for row in geometry["cylinders"])
    record("6: üretim tamamlandı — STEP yazıldı",
           build["status"] == "complete" and geometry["valid"] and geometry["solids"] == 1,
           {"status": build["status"], "solids": geometry["solids"], "size": geometry["size"]})

    # --- 4. STEP'i yeniden aç + dondurulmuş evaluator -------------------------------------------
    shutil.copy(step_path, out / "part.step")
    verdict_path = out / "plate-regression-verdict.json"
    proc = subprocess.run([str(CAD_PYTHON), str(EVALUATOR), str(out / "part.step"), str(REFERENCE_STEP),
                           str(verdict_path)], capture_output=True, text=True, timeout=1200)
    verdict = json.loads(verdict_path.read_text()) if verdict_path.exists() else {}
    checks = verdict.get("checks") or {}
    failed_checks = sorted(name for name, row in checks.items() if not row.get("ok"))
    produced = verdict.get("produced") or {}
    record("7: STEP yeniden açıldı ve dondurulmuş evaluator PASS (9/9 kontrol)",
           proc.returncode == 0 and verdict.get("pass") is True and not failed_checks,
           {"exit": proc.returncode, "checks": len(checks), "failed": failed_checks,
            "stdout": (proc.stdout or "").strip()[-300:]})
    # §44: 120 × 80 × 15, DÖRT delik (Ø6,8) ve BİR cep (Ø50). Köşe yuvarlatmaları da silindir olarak
    # raporlanır (izlemeden gelir, r≈10); onları ayrı sayarız, delik/cep sayısı iddiası değişmez.
    cylinder_radii = [round(row["radius"], 3) for row in produced.get("cylinders") or []]
    holes = [value for value in cylinder_radii if abs(value - 3.4) < 0.05]
    pockets = [value for value in cylinder_radii if abs(value - 25.0) < 0.1]
    record("8: parça dondurulmuş toleranslarda 120 × 80 × 15, 4 delik, 1 cep",
           [round(value, 3) for value in (produced.get("lengths") or [])] == [120.011, 80.002, 15.0]
           and len(holes) == 4 and len(pockets) == 1,
           {"lengths": produced.get("lengths"), "radii": cylinder_radii, "holes": len(holes),
            "pockets": len(pockets), "step_sha256": _sha256(out / "part.step")})

    passed = all(step["passed"] for step in STEPS)
    return _finish(landing, out, passed=passed)


def _finish(landing: pathlib.Path, out: pathlib.Path, *, passed: bool) -> int:
    payload = {"case": "plate-pocket-vector", "phase": "G12.2", "plan": "PLAN-25 §44",
               "passed": passed, "steps": STEPS}
    (landing / "g12-strategy-plate-steps.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(("TÜMÜ GEÇTİ " if passed else "KALAN VAR ") + f"{sum(1 for s in STEPS if s['passed'])}/{len(STEPS)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
