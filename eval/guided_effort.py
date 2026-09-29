"""What the guided flow asks a user, next to what the sheet already answered.

PLAN section 23-A is built (session store, revisions, undo, draft STEP), but nothing measures the
cost side: how many questions the flow puts to the user on a sheet whose numbers are printed on it.
This tool reads that cost out of the files the flow itself wrote, so the improvement has a number to
move. Two halves:

    opening   a drawing is opened through the product path (`guided.GuidedStore.create`), and the
              record says what the flow asks before any decision, how large each candidate menu is,
              and which of those questions the sheet's own reading already answers
    run       a saved session's decisions, field by field, each one marked:

                  bound    a reading claim ties this value to the geometry the decision uses
                  present  the sheet prints the value but nothing identifies it as this feature
                  absent   the sheet does not print it

The third class is the point. "15,00 is printed somewhere" and "15,00 is the thickness" are
different statements, and only the second one is an answer. On the plate sheet every value the user
typed is `bound` or `present`; what no rule settles is which printed number is the thickness and
which is the pocket depth — an identity question, not a value question.

What this tool does not claim:

* The reference STEP is used only by `--reference`, for the independent comparison `eval/metrics.py`
  already makes. It never enters the product path (`guided.py` never sees it).
* A `bound` value is the reading agreeing with the user, not an independent check of either one.
  The independent check is the reference comparison, and it is reported separately.
* Pixel-measured geometry stays a draft. Nothing here promotes it to a validated dimension.

    PYTHONPATH=src .venv/bin/python eval/guided_effort.py \
        --session out/guided/91411e3ebeca454596d8bec4f4b1a1c5 \
        --reference "examples/pdf with steps/5/plate with a pocket.STEP" --label plate-run
    PYTHONPATH=src .venv/bin/python eval/guided_effort.py \
        --drawing "examples/pdf with steps/6/plastic enclosue.pdf" --label plastic-open
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from drawingto3d import guided, proposal  # noqa: E402
from drawingto3d.guided import Decisions, GuidedStore  # noqa: E402

CASES = json.loads((ROOT / "eval" / "cases.json").read_text())
CASES = {case["id"]: case for case in (CASES["cases"] if isinstance(CASES, dict) else CASES)}


def reading_of(drawing: Path) -> dict:
    """The sheet's own reading, or the reason it refused. A refusal is a result, not an error."""
    try:
        sheet = proposal.read_sheet(drawing)
    except ValueError as exc:
        return {"refused": str(exc)}
    return {"sheet_px_per_mm": sheet.sheet_px_per_mm, "printed": sheet.printed, "claims": sheet.claims,
            "outline_mm": sheet.outline_mm, "circles_mm": sheet.circles_mm, "refusals": sheet.refusals,
            "notes": sheet.notes}


def diameter_claim(reading: dict, circle_id: str, diameter: float) -> dict | None:
    for claim in reading.get("claims", []):
        if claim.get("form") != "diameter" or circle_id not in claim.get("matched_geometry", []):
            continue
        if abs(claim.get("printed_mm", 0) - diameter) <= max(0.05, 0.01 * diameter):
            return claim
    return None


def printed_value(reading: dict, value: float, span_ids: tuple[str, ...] = ()) -> dict | None:
    for row in reading.get("printed", []):
        if span_ids and row.get("span_id") in span_ids:
            return row
        if abs(row.get("value", 0) - value) <= max(0.005, 0.002 * value):
            return row
    return None


def printed_text(reading: dict, span_id: str) -> str:
    for row in reading.get("printed", []):
        if row.get("span_id") == span_id:
            return str(row.get("text", ""))
    return ""


def geometry_at(options: dict, point: list[float], tolerance: float = 2.0) -> set[str]:
    """Which of the sheet's named geometry sits on this point, in the flow's own pixel frame."""
    found = set()
    for circle in options["circles"]:
        if abs(circle["center"][0] - point[0]) <= tolerance and abs(circle["center"][1] - point[1]) <= tolerance:
            found.add(circle["id"])
    for profile in options["profiles"]:
        for edge in profile.get("edges", []):
            for end in (edge["start"], edge["end"]):
                if abs(end[0] - point[0]) <= tolerance and abs(end[1] - point[1]) <= tolerance:
                    found.add(edge["id"])
    return found


def hole_coverage(reading: dict, hole: dict) -> dict:
    claim = diameter_claim(reading, hole["circle_id"], hole["diameter"])
    if claim is None:
        row = printed_value(reading, hole["diameter"])
        return {"level": "present" if row else "absent", "span_id": (row or {}).get("span_id")}
    text = printed_text(reading, claim["span_id"]).upper()
    answer = {"level": "bound", "span_id": claim["span_id"], "claim_form": claim.get("form")}
    if hole["kind"] == "pocket":
        # A circular pocket is a diameter without THRU; nothing in the reading names its depth.
        answer["kind_from_text"] = "pocket" if "THRU" not in text else "through (pocket chosen by user)"
        depth = printed_value(reading, hole["depth"]) if hole.get("depth") else None
        answer["depth"] = {"level": "present" if depth else "absent", "span_id": (depth or {}).get("span_id")}
    else:
        answer["kind_from_text"] = "through" if "THRU" in text else "not stated"
    return answer


def run_half(session: Path) -> dict:
    """The decisions a saved session holds, and where each one stands against the sheet's reading."""
    record = json.loads(session.read_text(encoding="utf-8"))
    decisions = Decisions.model_validate(record["decisions"])
    options = record["options"]
    reading = reading_of(Path(record["source"]))
    covered = {}
    if decisions.calibration:
        cal = decisions.calibration
        row = printed_value(reading, cal.value, (cal.span_id,) if cal.span_id else ())
        answer = {"level": "present" if row else "absent", "span_id": (row or {}).get("span_id"),
                  "note": "kullanıcı iki nokta + değer girdi"}
        # The user's two clicks may be exactly the geometry the reading's own claim measures.
        first = geometry_at(options, cal.first)
        second = geometry_at(options, cal.second)
        for claim in reading.get("claims", []):
            if claim.get("form") != "distance" or abs(claim.get("printed_mm", 0) - cal.value) > 0.005:
                continue
            ids = {anchor["geometry_id"] for anchor in claim.get("anchors", [])}
            if len(ids) >= 2 and ids <= (first | second):
                answer.update(level="bound", span_id=claim["span_id"],
                              note="kullanıcının tıkladığı noktalar okumanın kendi çapalarıyla aynı geometri")
                break
        if row and not answer.get("span_id"):
            answer["span_id"] = row.get("span_id")
        covered["calibration"] = answer
    if decisions.thickness:
        row = printed_value(reading, decisions.thickness)
        covered["thickness"] = {"level": "present" if row else "absent", "span_id": (row or {}).get("span_id"),
                                "note": "basılı değer var; hiçbir kural onu kalınlık olarak adlandırmıyor"}
    covered["holes"] = [{"circle_id": hole.circle_id, "kind": hole.kind, "diameter": hole.diameter,
                         **hole_coverage(reading, hole.model_dump())} for hole in decisions.holes]
    fields = []
    if decisions.profile_id:
        fields.append("profile")
    if decisions.calibration:
        fields.extend(["calibration.value", "calibration.first", "calibration.second"])
    if decisions.thickness:
        fields.append("thickness")
    if decisions.trace_acknowledged:
        fields.append("trace_acknowledged")
    for hole in decisions.holes:
        fields.extend([f"hole:{hole.circle_id}.kind", f"hole:{hole.circle_id}.diameter"])
        if hole.depth:
            fields.append(f"hole:{hole.circle_id}.depth")
    history = record.get("history", [])
    tally = {"bound": 0, "present": 0, "absent": 0}
    for key, value in covered.items():
        rows = value if isinstance(value, list) else [value]
        for row in rows:
            tally[row["level"]] += 1
            if isinstance(row.get("depth"), dict):
                tally[row["depth"]["level"]] += 1
    return {"source": record["source"], "source_sha256": record["source_sha256"], "revision": record["revision"],
            "build_status": (record.get("build") or {}).get("status"), "revisions_before_final": len(history),
            "questions_still_open": guided.questions(decisions), "fields_supplied": fields,
            "field_count": len(fields), "coverage": covered, "coverage_tally": tally,
            "measurement_menu": {"offered": len(options["measurements"]),
                                 "named_not_dimensions": [row["text"] for row in options["measurements"]
                                                          if re.fullmatch(r"\d{1,2}", row["text"].strip())
                                                          or re.fullmatch(r"(19|20)\d{2}", row["text"].strip())]},
            "candidates": {"profiles": len(options["profiles"]), "circles": len(options["circles"])},
            "reading": {"printed_bound": len(reading.get("printed", [])), "refusals": reading.get("refusals", []),
                        "refused": reading.get("refused")}}


def open_half(drawing: Path, label: str) -> dict:
    """Open a sheet through the product path and report the questions and menus it puts up."""
    store = GuidedStore(ROOT / "out" / "guided-effort" / label / "store")
    store.recover_interrupted()
    payload = drawing.read_bytes()
    public = store.create(payload)
    record = store.load(public["token"])
    options = record["options"]
    reading = reading_of(Path(record["source"]))
    outlines = []
    if reading.get("outline_mm"):
        outlines = [{"width_mm": reading["outline_mm"]["width_mm"], "height_mm": reading["outline_mm"]["height_mm"],
                     "primitives": reading["outline_mm"]["primitives"]}]
    return {"drawing": str(drawing), "source_sha256": record["source_sha256"], "token": public["token"],
            "questions_at_open": public["questions"], "question_count": len(public["questions"]),
            "candidates": {"profiles": len(options["profiles"]), "circles": len(options["circles"]),
                           "measurements_offered": len(options["measurements"]),
                           "printed_names": [row["text"] for row in options["measurements"] if row["value"] is not None]},
            "reading": {"printed_bound": len(reading.get("printed", [])), "outline": outlines or None,
                        "refusals": reading.get("refusals", []), "refused": reading.get("refused")},
            "notes": options.get("notes", [])}


def reference_check(produced: Path, reference: Path) -> dict:
    """The independent half: does the draft STEP hold up against the reference geometry?"""
    sys.path.insert(0, str(ROOT / "eval"))
    try:
        import metrics  # noqa: E402  (cadquery lives in .venv-cad)
    except ImportError as exc:
        return {"skipped": f"cadquery yok ({exc}); bu yarıyı CAD ortamında koşun: "
                           f".venv-cad/bin/python eval/metrics.py {produced} {reference}"}
    return metrics.compare(metrics.describe(produced), metrics.describe(reference))


def latest_build(session: Path, record: dict) -> Path | None:
    folder = (record.get("build") or {}).get("folder")
    if not folder:
        return None
    step = Path(folder) / "part.step"
    return step if step.exists() else None


def accept_and_build(drawing: Path, label: str) -> dict:
    """The improvement's own number: how many user steps the plate takes when the reading leads.

    One accept for everything the sheet answered, one build. The decisions that come out are compared
    against the manual run's own choices, and the built STEP against the reference on the eval side.
    """
    store = GuidedStore(ROOT / "out" / "guided-effort" / label / "store")
    store.recover_interrupted()
    public = store.create(drawing.read_bytes())
    token = public["token"]
    fields = [item["field"] for item in public["proposals"]]
    steps: list[dict] = [{"step": "open", "actor": "reading", "fields": fields,
                          "questions_at_open": public["questions"]}]
    accepted = store.accept(token, public["revision"])
    steps.append({"step": "accept", "actor": "user", "fields": fields, "accepted": len(fields)})
    left = accepted["questions"]
    if left:
        # The sheet did not answer everything: without the missing field a build refuses, and saying so
        # is the honest record. These are the questions the model adviser (§24-C) or the user answer.
        return {"drawing": str(drawing), "proposal_count": len(fields), "proposal_fields": fields,
                "interactions": 1, "user_fields": 1 + len(left), "steps": steps,
                "decisions": accepted["decisions"], "questions_after": left, "build_status": "blocked",
                "error": " ".join(left), "step": None, "token": token,
                "log": [{"actor": entry["actor"], "action": entry["action"], "field": entry["field"],
                         "note": entry["note"]} for entry in accepted["log"]]}
    built = store.build(token, accepted["revision"])
    steps.append({"step": "build", "actor": "system", "status": built["build_status"],
                  "questions_after": built["questions"]})
    step_path = None
    if built["step"]:
        step_path = str(store.artifact(token, "part.step")[0])
    return {"drawing": str(drawing), "proposal_count": len(fields), "proposal_fields": fields,
            "interactions": len(steps) - 1, "steps": steps, "decisions": built["decisions"],
            "questions_after": built["questions"], "build_status": built["build_status"],
            "error": built.get("error"), "step": step_path, "token": token,
            "log": [{"actor": entry["actor"], "action": entry["action"], "field": entry["field"],
                     "note": entry["note"]} for entry in built["log"]]}


def main() -> None:
    parser = argparse.ArgumentParser(description="guided akışın kullanıcıya maliyetini ve çizimin zaten verdiğini ölç")
    parser.add_argument("--session", default=None, help="kayıtlı oturum klasörü ya da session.json")
    parser.add_argument("--drawing", default=None, help="ürün yolundan açılıp ölçülecek çizim")
    parser.add_argument("--accept-and-build", action="store_true",
                        help="çizimi ürün yolundan aç, önerileri tek adımda onayla, taslağı üret")
    parser.add_argument("--reference", default=None, help="bağımsız kontrol için referans STEP (değerlendirme tarafı)")
    parser.add_argument("--label", required=True, help="kayıt klasörü adı: out/guided-effort/<label>/run.json")
    args = parser.parse_args()
    if not (args.session or args.drawing):
        parser.error("--session ya da --drawing gerekli")
    if args.accept_and_build and not args.drawing:
        parser.error("--accept-and-build --drawing ister")

    out = ROOT / "out" / "guided-effort" / args.label
    out.mkdir(parents=True, exist_ok=True)
    record: dict = {"label": args.label, "tool": "eval/guided_effort.py",
                    "claims": {"opening": "ürün yolundan açılan oturumun soruları ve menüleri",
                               "run": "kayıtlı kararların alan alan çizimle karşılaştırılması",
                               "flow": "öneriler tek adımda onaylanıp üretilen taslak",
                               "reference": "yalnız --reference verildiğinde, değerlendirme tarafı"},
                    "session": None, "opening": None, "flow": None, "reference": None}

    if args.session:
        session = Path(args.session)
        session = session / "session.json" if session.is_dir() else session
        record["session"] = run_half(session)
        step = latest_build(session, json.loads(session.read_text(encoding="utf-8")))
        record["session"]["built_step"] = str(step) if step else None
        if args.reference and step:
            record["reference"] = reference_check(step, Path(args.reference))
    if args.drawing:
        record["opening"] = open_half(Path(args.drawing), args.label)
    if args.accept_and_build:
        record["flow"] = accept_and_build(Path(args.drawing), args.label)
        if args.reference and record["flow"].get("step"):
            record["reference"] = reference_check(Path(record["flow"]["step"]), Path(args.reference))

    (out / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    # The CAD half needs cadquery, which lives in .venv-cad: when the caller ran `eval/metrics.py` there
    # and left its output beside the record, the record carries the verdict instead of the skip note.
    if isinstance(record.get("reference"), dict) and "skipped" in record["reference"]:
        sibling = out / "reference-check.json"
        if sibling.exists():
            try:
                saved = json.loads(sibling.read_text(encoding="utf-8"))
                record["reference"] = {"ran_in": ".venv-cad (eval/metrics.py)", "file": str(sibling),
                                       "verdict": saved.get("verdict", saved)}
                (out / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            except (OSError, ValueError):
                pass
    if record["opening"]:
        half = record["opening"]
        print(f"açılış: {half['question_count']} soru {half['questions_at_open']}")
        print(f"menüler: {half['candidates']}")
        print(f"okuma: {half['reading']['printed_bound']} bağlı ölçü, kontur {half['reading']['outline']}")
    if record["flow"]:
        half = record["flow"]
        print(f"akış: {half['proposal_count']} öneri → {half['interactions']} etkileşim"
              f" · üretim {half['build_status']} · açık soru {len(half['questions_after'])}")
        for step in half["steps"]:
            print(f"  {step['step']}: {step.get('actor')} {step.get('fields') or step.get('status') or ''}")
        print(f"  kararlar: {json.dumps(half['decisions'], ensure_ascii=False)}")
    if record["session"]:
        half = record["session"]
        print(f"koşu: {half['field_count']} alan · {half['build_status']} · revizyon {half['revision']}"
              f" · menüde adı geçmeyen ölçü {len(half['measurement_menu']['named_not_dimensions'])}")
        print(f"  çizimin cevapladığı: {half['coverage_tally']}")
        for key, value in half["coverage"].items():
            if key == "holes":
                for row in value:
                    depth = row.get("depth") or {}
                    print(f"  delik {row['circle_id']}: {row['level']} {row.get('span_id')} tür={row.get('kind_from_text')}"
                          f" derinlik={depth.get('level')} {depth.get('span_id', '')}")
            else:
                print(f"  {key}: {value['level']} {value.get('span_id')} — {value.get('note', '')}")
    if record["reference"]:
        verdict = record["reference"]
        if "verdict" in verdict:
            verdict = verdict["verdict"]
        if "checks" in verdict:
            print(f"referans kontrolü: geçti={verdict.get('pass')} "
                  f"ölçü={verdict['checks']['vector']['got']} hedef={verdict['checks']['vector']['want']}")
        else:
            print(f"referans kontrolü: atlandı — {verdict.get('skipped', verdict)}")
    print(f"kayıt: {out / 'run.json'}")


if __name__ == "__main__":
    main()
