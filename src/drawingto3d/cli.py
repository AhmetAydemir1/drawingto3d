"""Command line: read a sheet into dimension records, then build a STEP from those records.

    drawingto3d read  sheet.pdf out/                   read every printed dimension and its role
    drawingto3d build sheet.pdf out/records.json out/  build the solid from the (corrected) records

`propose` reads the sheet with the reading chain and proposes the plan the rules support;
`model-plan` asks the local model the same question from the same measurements, so a sheet the rules
refuse can still be planned. Nothing leaves the machine: the reader and the model are local only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from drawingto3d import reason
from drawingto3d.reason import reason_drawing
from drawingto3d.schema import DimensionRecord
from drawingto3d.ingest import load_page
from drawingto3d.plate import propose_plate
from drawingto3d.plan import PlatePlan, build_plan
from drawingto3d.cadrun import CadFailure
from drawingto3d.general import GeneralPlan, build_general
from drawingto3d.llama import (ChatSettings, OllamaChat, UnavailableModel, choose_text_model,
                                choose_vision_model, installed_models)
from drawingto3d.observe import observe
from drawingto3d.bind import bind_page
from drawingto3d.meaning import meaning_page
from drawingto3d.planner import chain_evidence, propose_plan, propose_plan_split
from drawingto3d.proposal import propose_general, read_sheet
from drawingto3d.catalog import build_catalog
from drawingto3d.planner import suggested_names
from drawingto3d.inference_log import Recorder, RecordedChat, recording_raster_models


def _add_log_flag(command) -> None:
    """`--inference-log`: model çağrılarının adapter sınırındaki kaydı (baseline kanıtı)."""
    command.add_argument("--inference-log", default=None, dest="inference_log",
                         help="model çağrılarının yazılacağı JSON kaydı")


def _recorder(args) -> "Recorder | None":
    """Komut başına **tek** kayıt nesnesi: aynı komut içinde yeniden kurulursa ilk kayıtları ezerdi."""
    path = getattr(args, "inference_log", None)
    if not path:
        return None
    existing = getattr(args, "_inference_recorder", None)
    if existing is not None:
        return existing
    recorder = Recorder(Path(path), label=f"{args.command}: {Path(args.drawing).name}")
    args._inference_recorder = recorder
    return recorder


def main() -> None:
    parser = argparse.ArgumentParser(prog="drawingto3d", description="PDF veya PNG teknik çizimden STEP")
    commands = parser.add_subparsers(dest="command", required=True)

    read = commands.add_parser("read", help="paftayı oku, ölçü kayıtlarını JSON olarak yaz")
    read.add_argument("drawing")
    read.add_argument("out_dir")
    _add_log_flag(read)

    build = commands.add_parser("build", help="düzeltilmiş kayıtlardan katıyı kur")
    build.add_argument("drawing")
    build.add_argument("records")
    build.add_argument("out_dir")
    _add_log_flag(build)

    plan = commands.add_parser("plan", help="desteklenen vektör paftadan model çağırmadan CAD planı çıkar")
    plan.add_argument("drawing")
    plan.add_argument("out_dir")
    replay = commands.add_parser("build-plan", help="incelenebilir CAD planından deterministik taslak STEP üret")
    replay.add_argument("drawing")
    replay.add_argument("plan")
    replay.add_argument("out_dir")
    general = commands.add_parser("build-general", help="sürümlü genel plandan deterministik taslak STEP üret")
    general.add_argument("plan")
    general.add_argument("out_dir")
    general.add_argument("--drawing", default=None,
                         help="plan.source.kind == 'drawing' ise kaynak çizim yolu")
    observe_command = commands.add_parser("observe", help="çizimden aile-bağımsız gözlem kayıtları çıkar (vektör PDF)")
    observe_command.add_argument("drawing")
    observe_command.add_argument("out_dir")
    bind_command = commands.add_parser("bind", help="basılı sayıları oklarının dokunduğu geometriye bağla (vektör PDF)")
    bind_command.add_argument("drawing")
    bind_command.add_argument("out_dir")
    meaning_command = commands.add_parser("meaning", help="bağlanan adaylardan her sayının ölçtüğü şeyi çöz (vektör PDF)")
    meaning_command.add_argument("drawing")
    meaning_command.add_argument("out_dir")
    propose_command = commands.add_parser("propose", help="okumalardan genel plan önerisi çıkar; reddedilirse nedenini yaz")
    propose_command.add_argument("drawing")
    propose_command.add_argument("out_dir")
    _add_log_flag(propose_command)
    catalog_command = commands.add_parser(
        "catalog", help="basılı ölçüleri kaynak/birim tablosu olarak incele; model çağrısı yapmaz")
    catalog_command.add_argument("drawing")
    catalog_command.add_argument("out_dir")
    model_plan_command = commands.add_parser(
        "model-plan", help="çizimin kendi ölçümlerinden yerel modelle genel plan çıkar (kanıt + ham plan kaydı)")
    model_plan_command.add_argument("drawing")
    model_plan_command.add_argument("out_dir")
    model_plan_command.add_argument("--model", default=None, help="yerel Ollama etiketi (varsayılan: kurulu talimat modeli)")
    _add_log_flag(model_plan_command)
    model_plan_command.add_argument("--num-ctx", type=int, default=16384)
    model_plan_command.add_argument("--predict", type=int, default=4096)
    model_plan_command.add_argument("--split", action="store_true",
                                    help="kanıtı üç dar soruya böl (PLAN §19.4); her adım ayrı çağrı")

    args = parser.parse_args()
    if args.command == "catalog":
        try:
            payload = catalog_from_drawing(Path(args.drawing), Path(args.out_dir))
        except (ValueError, OSError) as exc:
            parser.exit(2, f"Katalog çıkarılamadı: {exc}\n")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if args.command == "plan":
        proposal = propose_plate(load_page(args.drawing))
        if proposal is None:
            parser.exit(2, "Bu çizim desteklenen vektör plaka ailesiyle güvenilir biçimde eşleşmedi.\n")
        folder = Path(args.out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "plan.json"
        path.write_text(proposal.model_dump_json(indent=2), encoding="utf-8")
        print(json.dumps({"plan": str(path), "assumptions": proposal.assumptions}, ensure_ascii=False, indent=2))
        return
    if args.command == "build-plan":
        proposal = PlatePlan.model_validate_json(Path(args.plan).read_text(encoding="utf-8"))
        step, stl = build_plan(proposal, args.drawing, args.out_dir)
        print(json.dumps({"step": str(step), "stl": str(stl), "draft": True,
                          "audit": str(Path(args.out_dir) / "plan-audit.json")}, indent=2))
        return
    if args.command == "build-general":
        try:
            plan = GeneralPlan.model_validate_json(Path(args.plan).read_text(encoding="utf-8"))
            step, stl = build_general(plan, args.drawing, args.out_dir)
        except CadFailure as exc:
            parser.exit(2, f"Plan uygulanamadı: {exc}\n")
        except ValueError as exc:
            parser.exit(2, f"Geçersiz plan: {_readable(exc)}\n")
        print(json.dumps({"step": str(step), "stl": str(stl), "status": "draft",
                          "audit": str(Path(args.out_dir) / "plan-audit.json")}, indent=2))
        return
    if args.command == "observe":
        try:
            observations = observe(args.drawing)
        except ValueError as exc:
            parser.exit(2, f"Gözlem çıkarılamadı: {exc}\n")
        folder = Path(args.out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "observations.json"
        path.write_text(observations.model_dump_json(indent=2), encoding="utf-8")
        print(json.dumps({"observations": str(path), "paths": len(observations.paths),
                          "primitives": len(observations.primitives), "texts": len(observations.texts)},
                         indent=2))
        return
    if args.command == "bind":
        try:
            bindings = bind_page(args.drawing)
        except ValueError as exc:
            parser.exit(2, f"Bağlama çıkarılamadı: {exc}\n")
        folder = Path(args.out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "bindings.json"
        path.write_text(bindings.model_dump_json(indent=2), encoding="utf-8")
        counts: dict[str, int] = {}
        for span in bindings.spans:
            counts[span.status] = counts.get(span.status, 0) + 1
        print(json.dumps({"bindings": str(path), "spans": len(bindings.spans),
                          "status": counts, "sheet_px_per_mm": bindings.sheet_px_per_mm},
                         ensure_ascii=False, indent=2))
        return
    if args.command == "meaning":
        try:
            meanings = meaning_page(args.drawing)
        except ValueError as exc:
            parser.exit(2, f"Anlam çıkarılamadı: {exc}\n")
        folder = Path(args.out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "meaning.json"
        path.write_text(meanings.model_dump_json(indent=2), encoding="utf-8")
        forms: dict[str, int] = {}
        resolutions: dict[str, int] = {}
        for span in meanings.spans:
            forms[span.form] = forms.get(span.form, 0) + 1
            resolutions[span.resolution] = resolutions.get(span.resolution, 0) + 1
        print(json.dumps({"meaning": str(path), "spans": len(meanings.spans),
                          "forms": forms, "resolution": resolutions},
                         ensure_ascii=False, indent=2))
        return
    if getattr(args, "inference_log", None):
        # Çağrı kaydı komutun başında doğar: model hiç çağrılmazsa da "sıfır çağrı" ölçülmüş olur ve
        # satır `inference_called: null` (kanıt yok) yerine `false` yazar.
        _recorder(args)
    if args.command == "propose":
        try:
            proposal = propose_general(args.drawing)
        except ValueError as exc:
            parser.exit(2, f"Öneri çıkarılamadı: {exc}\n")
        folder = Path(args.out_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "proposal.json"
        path.write_text(proposal.model_dump_json(indent=2), encoding="utf-8")
        payload: dict = {"proposal": str(path), "status": proposal.status,
                         "readings": len(proposal.readings), "refusals": proposal.refusals}
        if proposal.plan is not None:
            plan_path = folder / "plan.json"
            plan_path.write_text(proposal.plan.model_dump_json(indent=2), encoding="utf-8")
            payload["plan"] = str(plan_path)
        else:
            parser.exit(2, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if args.command == "read":
        _read(args)
        return
    if args.command == "model-plan":
        _model_plan(args, parser)
        return
    _build(args)


def _read(args) -> None:
    recorder = _recorder(args)
    reader, coder = recording_raster_models(recorder) if recorder is not None else (None, None)
    result = reason_drawing(args.drawing, args.out_dir, coder=coder, reader=reader, progress=_tell)
    folder = Path(args.out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "records.json"
    payload = [record.model_dump(mode="json") for record in result.records]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Paftanın kendi ölçek kararı kayıtların yanında durur: sayılar paftanın kendi geometrisiyle
    # doğrulandı mı, doğrulanamadı mı, yoksa birbirini mi yalanlıyor. Bu bir cümle değil, kayıt.
    sheet = reason.sheet_scale(result.page)
    (folder / "scale.json").write_text(json.dumps(sheet, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    # Ölçekle çelişen okuma sessizce düzeltilmez, soruya çevrilir: ne yazdığı, ölçeğin ne dediği ve aday
    # değer birlikte yazılır (review6 W02). Kayıt olduğu gibi kalır; kararı kullanıcı verir.
    questions = reason.suspect_questions(result.page) if result.page else []
    (folder / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    print(json.dumps({"records": len(payload), "file": str(path), "scale": sheet,
                      "questions": questions},
                     ensure_ascii=False, indent=2))


def _build(args) -> None:
    raw = json.loads(Path(args.records).read_text(encoding="utf-8"))
    records = [DimensionRecord.model_validate(item) for item in raw]
    recorder = _recorder(args)
    reader, coder = recording_raster_models(recorder) if recorder is not None else (None, None)
    result = reason_drawing(args.drawing, args.out_dir, coder=coder, reader=reader, records=records,
                            progress=_tell)
    print(
        json.dumps(
            {"step": result.step_path, "stl": result.stl_path, "accepted": result.audit.accepted},
            ensure_ascii=False,
            indent=2,
        )
    )


def _tell(title: str, detail: str) -> None:
    print(f"{title}: {detail}", flush=True)


def catalog_from_drawing(drawing: Path, folder: Path) -> dict:
    """Expose fixed source quantities for review, including partial geometry readings."""
    paths = {name: folder / name for name in ("catalog.json", "evidence.json", "review.md")}
    if any(path.exists() for path in paths.values()):
        raise ValueError("bu klasörde katalog/kanıt kaydı var; yeni çıktı klasörü seçin")
    reading = read_sheet(drawing)
    evidence = chain_evidence(reading)
    errors = []
    catalog = None
    if evidence["printed"]:
        try:
            catalog = build_catalog(evidence, suggested_names(evidence))
        except ValueError as exc:
            errors.append(str(exc))
    else:
        errors.append("sayısal basılı ölçü okunamadı")
    status = "needs_input" if errors or reading.refusals else "needs_review"
    record = {"version": 1, "source_ref": reading.source_ref, "source_sha256": reading.source_sha256,
              "status": status, "catalog": None if catalog is None else catalog.model_dump(mode="json"),
              "geometry_refusals": reading.refusals, "errors": errors,
              "interpretation_verified": False, "geometry_verified": False}

    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    lines = ["# Basılı ölçü incelemesi", "", "Durum: " + (
        "Eksik bilgi var." if status == "needs_input" else "İnceleme gerekli."), "",
        "Bu tablo çizimden okunan sayıları ve kaynaklarını gösterir. Ölçülerin parçadaki anlamı",
        "ve geometri henüz doğrulanmadı. CAD üretmeden önce kaynak metnini ve eşleşmeleri inceleyin.", ""]
    if catalog:
        lines += ["| Ad | Değer | Birim | Kaynak | Metin | Geometri bağı |",
                  "|---|---:|---|---|---|---|"]
        for entry in catalog.entries:
            binding = "otomatik eşleşme" if entry.measurement.get("resolution") == "confirmed" else "çözülemedi"
            lines.append("| " + " | ".join(cell(value) for value in (
                entry.name, str(entry.value), entry.unit, entry.span_id, entry.text, binding)) + " |")
    if reading.refusals or errors:
        lines += ["", "## Eksikler", ""] + [f"- {cell(text)}" for text in reading.refusals + errors]
    folder.mkdir(parents=True, exist_ok=True)
    paths["evidence.json"].write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["catalog.json"].write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["review.md"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": status, "entries": len(catalog.entries) if catalog else 0,
            **{name.split(".")[0]: str(path) for name, path in paths.items()}}


def plan_from_drawing(drawing: Path, folder: Path, chat, *, split: bool = False) -> tuple[dict, str | None]:
    """One real drawing in, the evidence and the model's plan out.

    Returns the payload to print and, when the run stopped short, the one-line reason — the caller
    turns that into an exit code. Everything the run produced is written before returning, so a
    refusal can be read afterwards: the evidence the model was asked with, its raw reply, the plan.
    """
    folder.mkdir(parents=True, exist_ok=True)
    reading = read_sheet(drawing)
    evidence = chain_evidence(reading)
    evidence_path = folder / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {"evidence": str(evidence_path), "printed": len(evidence["printed"]),
               "claims": len(evidence["claims"]), "circles": len(evidence["geometry"]["circles"]),
               "scale_known": bool(evidence["sheet"]["scale_known"]),
               "model": getattr(chat, "model", "?")}
    if reading.refusals:
        return payload, "Çizim milimetreye çevrilemedi: " + "; ".join(reading.refusals)
    candidate = (propose_plan_split if split else propose_plan)(
        chat, evidence, ref=str(drawing), sha256=_sha256_file(drawing))
    candidate_path = folder / "candidate.json"
    candidate_path.write_text(candidate.model_dump_json(indent=2), encoding="utf-8")
    payload.update({"candidate": str(candidate_path), "prompt_version": candidate.prompt_version,
                    "seconds": candidate.seconds, "status": candidate.status, "errors": candidate.errors})
    if candidate.plan is None:
        return payload, "Model şemaya uyan plan vermedi; ham yanıt candidate.json içinde."
    plan_path = folder / "plan.json"
    plan_path.write_text(candidate.plan.model_dump_json(indent=2), encoding="utf-8")
    payload["plan"] = str(plan_path)
    return payload, None


def _model_plan(args, parser) -> None:
    drawing = Path(args.drawing)
    folder = Path(args.out_dir)
    chat = None
    payload: dict = {}
    reason: str | None = None
    try:
        label = args.model or _default_model()
        settings = ChatSettings(model=label, num_ctx=args.num_ctx, num_predict=args.predict)
        recorder = _recorder(args)
        # Çağrı kanıtı adapter sınırında: kayıt varsa sohbet nesnesi kaydeden sarmalayıcıdır.
        chat = (OllamaChat(label, settings=settings) if recorder is None else
                RecordedChat(label, settings=settings, recorder=recorder))
        payload, reason = plan_from_drawing(drawing, folder, chat, split=args.split)
    except (UnavailableModel, ValueError) as exc:
        reason = f"Plan çıkarılamadı: {_readable(exc)}"
    finally:
        if chat is not None:
            chat.unload()
    if payload:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    if reason is not None:
        parser.exit(2, reason + "\n")


def _default_model() -> str:
    """The model a plan request goes to when none was named: a reader if this box has one, else any
    installed model — the request carries an image, and the model's own answer says what it made of it."""
    try:
        return choose_vision_model()
    except UnavailableModel:
        pass
    models = installed_models()
    if not models:
        raise UnavailableModel("Ollama'da kurulu model yok; --model ile etiket ver")
    return choose_text_model()


def _sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _readable(exc: Exception) -> str:
    """Validation errors read as one line: location and message, no pydantic internals."""
    if isinstance(exc, ValidationError):
        parts = []
        for error in exc.errors(include_url=False, include_input=False):
            where = ".".join(str(item) for item in error["loc"])
            message = str(error["msg"]).removeprefix("Value error, ")
            parts.append(f"{where}: {message}" if where else message)
        if parts:
            return "; ".join(parts)
    return str(exc)


if __name__ == "__main__":
    main()
