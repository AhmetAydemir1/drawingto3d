"""Baseline satırının alanları: her biri kendi kanıtından, cümleden değil.

S03'ün kabulü "komut çalıştı" ile "model çağrıldı"yı ayırmak ve görüntünün gidip gitmediğini iddia değil
kayıt olarak istemekti. T01 onun üstüne kayıt izolasyonunu ekledi (adım başına ayrı dosya; ikinci komut
birincinin kanıtını ezmemeli), T04 ise bütçeyi: süresi biten adım başlatılmaz ve bu yazılır.
"""

from __future__ import annotations

import importlib.util
import json
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


# --- U01/U02 regresyonu: review4'ün karşı örnekleri ------------------------------------------
#
# `eval/audits/20260929-hermes-review4/observations.json` iki sınıflama hatasını kaydetti:
# `classification_probe` bilinmeyen kararı (`not_evaluated`, `error`, `null`) positive sayıyordu ve
# `trace_probe` hiç çalışmamış `verdict_pass` adımını terminal hata yazıyordu. Aşağıdaki testler bu
# karşı örnekleri sabit tutar.

REVIEW4_OBSERVATIONS = ROOT / "eval" / "audits" / "20260929-hermes-review4" / "observations.json"


def _row(**overrides) -> dict:
    """Sınıflamanın okuduğu alanları taşıyan asgari satır; varsayılanı 'hiç çıktı yok'."""
    row = {
        "part_id": "p", "error_class": "girdi/sayfa/görünüş", "step_built": False,
        "product_refusals": ["okunamadı"], "product_step": None, "not_started": [],
        "input_file": "drawing.pdf", "input_sha256": "a" * 64, "reference_sha256": "b" * 64,
        "product_input_leakage": "none", "evaluator": None,
        "arms": {"product": {"arm": "rule"}, "model": {"inference_called": None,
                                                       "plan_produced": False, "step_built": False,
                                                       "evaluated": False, "verdict": None,
                                                       "trace": {}}},
    }
    arms = overrides.pop("arms", None)
    row.update(overrides)
    if arms:
        row["arms"] = {**row["arms"], **arms}
    return row


def _probe_rows(module) -> list[dict]:
    """review4 `classification_probe` satırlarını gerçek satır biçiminde yeniden kurar.

    Denetimde her karşı örnek "model kolu çıktı verdi, kararı bilinmiyor" durumuydu: çağrı yapılmış,
    plan kurulmuş ve değerlendirme denenmiş. Eski kod bu üç bayrağa bakıp satırı `positive` yapıyordu.
    """
    rows = []
    for index, probe in enumerate(json.loads(REVIEW4_OBSERVATIONS.read_text(encoding="utf-8"))[
            "classification_probe"]):
        rows.append(_row(part_id=f"probe-{index}", arms={"model": {
            "inference_called": True, "plan_produced": True, "step_built": True, "evaluated": True,
            "verdict": probe["verdict"]}}))
    return rows


def test_a_missing_or_invalid_verdict_is_unknown_and_never_positive():
    """U01: `not_evaluated`, `error` ve `null` kararı olan satır positive sayılamaz."""
    module = load_module()
    entries = module._row_classification(_probe_rows(module), "probe")["entries"]
    model = {entry["part_id"]: entry for entry in entries if entry["arm"] == "model"}

    assert model["probe-0"]["usable_as"] == "unknown"      # not_evaluated
    assert model["probe-1"]["usable_as"] == "unknown"      # error
    assert model["probe-2"]["usable_as"] == "unknown"      # null
    assert model["probe-3"]["usable_as"] == "negative"     # fail: yanlış çıktı, doğru hedef değil
    assert model["probe-4"]["usable_as"] == "positive"     # pass: tek gerçek positive
    assert all(entry["classified_verdict"] != "fail" or entry["usable_as"] == "negative"
               for entry in entries)


def test_the_recorded_classification_probe_still_shows_the_old_behaviour():
    """Denetim kanıtı yerinde duruyor: karşı örnekler silinmedi, yalnız kod düzeltildi."""
    recorded = json.loads(REVIEW4_OBSERVATIONS.read_text(encoding="utf-8"))["classification_probe"]
    assert [item["verdict"] for item in recorded] == ["not_evaluated", "error", None, "fail", "pass"]
    assert [item["classified"] for item in recorded] == ["positive", "positive", "positive",
                                                        "negative", "positive"]


def test_the_row_classification_counts_unknowns_apart_from_excluded():
    """Bilinmeyen karar ile öğrenilecek çıktı yokluğu ayrı sayılır; ikisi de positive değil."""
    module = load_module()
    rows = _probe_rows(module) + [_row(part_id="no-output")]
    classification = module._row_classification(rows, "probe")

    assert classification["schema"] == "drawingto3d.lab.row-classification/1"
    assert classification["counts"]["positive"] == 1
    assert classification["counts"]["negative"] == 1
    assert classification["counts"]["unknown"] == 3
    assert classification["counts"]["excluded"] == 7, "5 parça × 2 kol − 4 sınıflı çıktı + 1 çıktısız"


def test_the_training_decision_is_separate_and_needs_labelable_evidence():
    """Satır sınıflaması karar değil: `train_targeted` üç ayrı parçada etiketli çıktı ister."""
    module = load_module()
    rule_rows = [_row(part_id=f"r{index}", error_class="kısıt/kalibrasyon") for index in range(4)]
    classification = module._row_classification(rule_rows, "run")
    decision = module._training_decision(rule_rows, classification, "run")

    assert decision["schema"] == "drawingto3d.lab.training-decision/1"
    assert decision["decision"] == "fix_rules_first", "kural/okuma hatası için model eğitilmez"
    assert decision["narrow_task"] is None
    assert decision["root_error"]["error_layers"] == {"kısıt/kalibrasyon": 4}
    assert decision["threshold_evidence"]["labelable_parts"] == []
    assert set(decision["gates"].values()) == {"unverified"}, "ölçülmemiş kapı doğrulanmış yazılamaz"
    assert module._training_decision([], module._row_classification([], "run"), "run")["decision"] \
        == "need_data"

    labelable = [_row(part_id=f"m{index}", evaluator={"verdict": "pass"}, step_built=True,
                      product_step=f"/x/{index}.step") for index in range(3)]
    enough = module._row_classification(labelable, "run")
    assert module._training_decision(labelable, enough, "run")["decision"] == "train_targeted", \
        "model kolunda değil ürün kolunda olsa bile etiketlenebilir çıktı eşiği doldurur"


def test_a_stage_that_never_ran_is_not_a_terminal_failure():
    """U02: plan hiç oluşmadıysa terminal hata plan adımıdır, çalışılmamış `verdict_pass` değil."""
    module = load_module()

    trace = module._trace([("plan_produced", False, "not made", True),
                           ("step_built", False, "not run", False),
                           ("verdict_pass", False, "not evaluated", False)])
    stages = {stage["stage"]: stage["status"] for stage in trace["stages"]}

    assert stages == {"plan_produced": "failed", "step_built": "blocked_by_previous",
                      "verdict_pass": "blocked_by_previous"}
    assert trace["first_divergence"] == "plan_produced"
    assert trace["terminal_failure"] == "plan_produced", "çalışılmayan adım terminal hata olamaz"
    assert trace["last_stage_reached"] == "plan_produced"
    assert trace["counts"] == {"completed": 0, "failed": 1, "not_started": 0,
                               "blocked_by_previous": 2}


def test_the_recorded_trace_probe_still_shows_the_old_behaviour():
    """Denetimin iz kaydı korunuyor: eski kodun `terminal_failure`i kanıtta yazılı."""
    recorded = json.loads(REVIEW4_OBSERVATIONS.read_text(encoding="utf-8"))["trace_probe"]
    assert recorded["first_divergence"] == "plan_produced"
    assert recorded["terminal_failure"] == "verdict_pass"


def test_a_command_that_never_started_leaves_its_stages_unstarted():
    """Komut hiç çağrılmadıysa adımlar `not_started`; önceki düşüş yoksa `blocked_by_previous` değil."""
    module = load_module()

    trace = module._trace([("command_started", False, "model-plan", False),
                           ("plan_produced", False, "yok", False),
                           ("step_built", False, "yok", False),
                           ("evaluated", False, "step yok", False),
                           ("verdict_pass", False, "step yok", False)])

    assert trace["not_started"] == ["command_started", "plan_produced", "step_built", "evaluated",
                                    "verdict_pass"]
    assert trace["terminal_failure"] is None and trace["last_stage_reached"] is None


def test_a_failed_build_is_the_terminal_failure_and_the_verdict_stage_is_blocked():
    """Adımların ayrımı ürün kolunda da geçerli: derleme düştüyse değerlendirme koşmadı."""
    module = load_module()

    trace = module._trace([("command_started", True, "1 adım", True),
                           ("plan_produced", True, "plan.json", True),
                           ("step_built", False, "CadFailure", True),
                           ("evaluated", False, "değerlendirilecek STEP yok", False),
                           ("verdict_pass", False, "değerlendirilecek STEP yok", False)])

    assert trace["first_divergence"] == "step_built"
    assert trace["terminal_failure"] == "step_built"
    assert trace["last_stage_reached"] == "step_built"
    assert trace["blocked_by_previous"] == ["evaluated", "verdict_pass"]
