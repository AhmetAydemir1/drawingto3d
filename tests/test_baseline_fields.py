"""Baseline satırının alanları: her biri kendi kanıtından, cümleden değil.

S03'ün kabulü "komut çalıştı" ile "model çağrıldı"yı ayırmak ve görüntünün gidip gitmediğini iddia değil
kayıt olarak istemekti. T01 onun üstüne kayıt izolasyonunu ekledi (adım başına ayrı dosya; ikinci komut
birincinin kanıtını ezmemeli), T04 ise bütçeyi: süresi biten adım başlatılmaz ve bu yazılır.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("lab_baseline", ROOT / "eval" / "lab_baseline.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lab_baseline"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _log(path: Path, calls: list[dict], *, models: dict | None = None) -> None:
    """Adımın kendi çağrı kaydı; kayıtlar gerçek şemayla (v2) biçilmiş olarak yazılır."""
    from drawingto3d.inference_log import Recorder

    recorder = Recorder(path, label=path.name)
    if models:
        recorder.models = models
    for call in calls:
        call_id = recorder.started(call["kind"], image_attached=call.get("image_attached", False),
                                   image_bytes=call.get("image_bytes", 0), prompt_chars=100)
        if call.get("unfinished"):
            continue
        recorder.finished(call_id, server_ok=call.get("server_ok", True), error=call.get("error"))


def test_a_row_without_a_call_log_reports_no_evidence_rather_than_no_calls(tmp_path):
    """Kanıt dosyası yoksa alan `null`: "ölçülmedi" ile "çağrılmadı" aynı şey değil."""
    module = load_module()
    product = tmp_path / "product"
    product.mkdir(parents=True)

    fields = module._fields_from_disk(tmp_path, {"part_id": "p", "kind": "vector"},
                                      [{"command": ["propose"]}], [], None, None, None, tmp_path)

    assert fields["command_started"] is True
    assert fields["inference_called"] is None and fields["image_attached"] is None
    assert fields["unfinished"] is None, "kayıt yokken 'kesilen çağrı yok' denemez"
    assert fields["inference_logs"] == []
    assert fields["step_built"] is False and fields["evaluated"] is False


def test_a_zero_call_log_measures_that_no_model_was_asked(tmp_path):
    """Sıfır çağrılı kayıt `false` yazar: "model çağrılmadı" artık bir ölçüm."""
    module = load_module()
    (tmp_path / "product").mkdir(parents=True)
    _log(tmp_path / "product" / "inference-log-propose.json", [])

    fields = module._fields_from_disk(tmp_path, {"part_id": "p", "kind": "vector"}, [{}], [], None, None,
                                      None, tmp_path)

    assert fields["inference_called"] is False and fields["image_attached"] is False
    assert fields["unfinished"] == 0
    assert fields["inference_logs"][0].endswith("product/inference-log-propose.json")


def test_a_call_log_carries_the_model_and_whether_an_image_was_attached(tmp_path):
    module = load_module()
    (tmp_path / "product").mkdir(parents=True)
    _log(tmp_path / "product" / "inference-log-build.json",
         [{"kind": "coder", "image_attached": False}],
         models={"coder": {"kind": "coder", "model": "qwen2.5-coder:7b"}})

    fields = module._fields_from_disk(tmp_path, {"part_id": "p", "kind": "raster"}, [{}], [], None, None,
                                      None, tmp_path)

    assert fields["inference_called"] is True
    assert fields["image_attached"] is False, "görüntü gitmediyse gitmiş gibi yazılmamalı"
    assert fields["arms"]["product"]["models"]["coder"]["model"] == "qwen2.5-coder:7b"
    assert "serbest kod" in fields["arms"]["product"]["pipeline"], \
        "raster kolu yapılandırılmış ürün yolu gibi adlandırılmamalı"


def test_two_commands_keep_their_own_records_and_the_summary_unions_them(tmp_path):
    """T01: `read` görüntüyle bir çağrı yapar, `build` görüntüsüz bir çağrı; ikisi de kayıtta kalmalı.

    Aynı yolu paylaşan iki komut birbirinin kanıtını eziyordu: `build`'in kaydı `read`'in görüntülü
    çağrısını siliyor ve satır "hiç görüntü gitmedi" diye okunuyordu.
    """
    module = load_module()
    (tmp_path / "product").mkdir(parents=True)
    _log(tmp_path / "product" / "inference-log-read.json",
         [{"kind": "vision", "image_attached": True, "image_bytes": 4096}],
         models={"vision": {"kind": "vision", "model": "qwen2.5vl:3b"}})
    _log(tmp_path / "product" / "inference-log-build.json",
         [{"kind": "coder", "image_attached": False}],
         models={"coder": {"kind": "coder", "model": "qwen2.5-coder:7b"}})

    fields = module._fields_from_disk(tmp_path, {"part_id": "p", "kind": "raster"}, [{}], [], None, None,
                                      None, tmp_path)

    assert len(fields["inference_logs"]) == 2, "her komutun kaydı ayrı dosyada durmalı"
    assert fields["arms"]["product"]["records"] == 2
    assert fields["arms"]["product"]["attempts"] == 2
    assert fields["image_attached"] is True, "birleşik özet görüntülü çağrıyı kaybetmemeli"
    steps = {entry["step"]: entry for entry in fields["arms"]["product"]["per_step"]}
    assert set(steps) == {"read", "build"}
    assert steps["read"]["image_attached"] is True and steps["build"]["image_attached"] is False


def test_three_artifacts_are_not_merged_into_one_produced_flag(tmp_path):
    """`plan.json`, `records.json` ve üretilen program üç ayrı artefakt; tek bayrağa indirilmemeli."""
    module = load_module()
    product = tmp_path / "product"
    product.mkdir(parents=True)
    (product / "records.json").write_text("{}")
    (product / "geo_program.py").write_text("x = 1")

    fields = module._fields_from_disk(tmp_path, {"part_id": "p", "kind": "raster"}, [{}], [], None, None,
                                      None, tmp_path)

    assert fields["records_produced"] is True
    assert fields["program_produced"] is True
    assert fields["plan_produced"] is False, "raster kolunda plan.json yok; records.json plan yerine geçmez"


def test_a_case_with_no_time_left_does_not_start_a_step(tmp_path):
    """T04: bütçe bitmişse adım başlatılmaz ve gerekçe satıra yazılır (tavan sessizce yükseltilmez)."""
    module = load_module()
    budget = module.Budget(0.0)

    step = module._cli(["propose", str(tmp_path / "yok.pdf"), str(tmp_path)], tmp_path, budget=budget)

    assert step["started"] is False and step["exit_code"] is None
    assert "kalan süre yok" in step["not_started_reason"]
    assert budget.remaining() == 0.0


def test_the_case_budget_is_shared_between_steps():
    """Vaka bütçesi 600 s ve adımlar arasında paylaşılır; koşu bütçesi ondan büyük."""
    module = load_module()

    assert module.CASE_BUDGET_SECONDS == 600
    assert module.RUN_BUDGET_SECONDS > module.CASE_BUDGET_SECONDS
    budget = module.Budget(module.CASE_BUDGET_SECONDS, label="p")
    budget.note("read", 12.5)
    record = budget.as_record()
    assert record["budget_seconds"] == 600 and record["steps"][0]["step"] == "read"
    assert record["remaining_seconds"] <= 600


def test_the_model_build_gets_the_source_drawing(tmp_path):
    """T03: model planının derlenmesi `--drawing` ile aynı çizimi almalı.

    Kaynak çizim verilmediğinde `build-general` planın kaynağını doğrulayamıyor ve her model planı
    modelle ilgisi olmayan bir gerekçeyle düşüyordu.
    """
    module = load_module()
    seen = []

    def fake_cli(arguments, workdir, *, log=None, budget=None):
        seen.append({"arguments": list(arguments), "log": str(log) if log else None})
        if arguments[0] == "model-plan":
            plan = tmp_path / "model" / "plan.json"
            plan.parent.mkdir(parents=True, exist_ok=True)
            plan.write_text("{}")
            return {"command": ["python", "model-plan"], "started": True, "exit_code": 0, "seconds": 0.1,
                    "timed_out": False, "result": {"plan": str(plan)}, "stdout_tail": "", "stderr_tail": ""}
        return {"command": ["python", "build-general"], "started": True, "exit_code": 0, "seconds": 0.1,
                "timed_out": False, "result": {}, "stdout_tail": "", "stderr_tail": ""}

    module._cli = fake_cli
    drawing = tmp_path / "input" / "drawing.pdf"
    drawing.parent.mkdir(parents=True, exist_ok=True)
    drawing.write_bytes(b"%PDF-1.4")

    module._model_step(drawing, tmp_path)

    build = [entry for entry in seen if entry["arguments"][0] == "build-general"]
    assert build, "plan üretildiyse derleme adımı koşmalı"
    assert "--drawing" in build[0]["arguments"] and str(drawing) in build[0]["arguments"]
    assert build[0]["log"] is None, "model kolunun derlemesi model çağrısı yapmaz, kayıt yolu almaz"


def test_the_summary_keeps_attempts_and_distinct_parts_apart():
    """Beş satırın dördü ayrı parça: paydalar ayrı yazılmalı, kol başına da ayrı."""
    module = load_module()
    rows = [
        {"part_id": "a", "error_class": "kısıt/kalibrasyon", "evaluator": None, "product_step": None,
         "product_refusals": ["x"], "command_started": True, "inference_called": False,
         "image_attached": False, "plan_produced": False, "step_built": False, "evaluated": False,
         "arms": {"model": {"ran": False}, "product": {"unfinished": 0}}},
        {"part_id": "a", "error_class": "CAD işlemi", "evaluator": None, "product_step": None,
         "product_refusals": [], "command_started": True, "inference_called": True, "image_attached": False,
         "plan_produced": True, "step_built": False, "evaluated": False,
         "arms": {"model": {"ran": True, "inference_called": True, "plan_produced": False},
                  "product": {"unfinished": 1}}},
        {"part_id": "b", "error_class": "kısıt/kalibrasyon", "evaluator": None, "product_step": None,
         "product_refusals": [], "command_started": True, "inference_called": None, "image_attached": None,
         "plan_produced": False, "step_built": False, "evaluated": False, "arms": {}},
    ]
    summary = module._summary(rows)

    assert summary["attempt_count"] == 3 and summary["unique_part_count"] == 2
    assert summary["arms"]["product"]["inference_called"] == 1
    assert summary["arms"]["product"]["inference_log_missing"] == 1, \
        "kayıtsız satır ölçülmemiş sayılmalı, model kullanmamış gibi değil"
    assert summary["arms"]["product"]["unfinished_calls"] == 1, "kesilen çağrı özette görünmeli"
    assert summary["arms"]["model"]["ran"] == 1
