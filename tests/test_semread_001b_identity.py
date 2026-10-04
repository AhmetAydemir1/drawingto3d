"""SEMREAD-001B — P0R-FINAL-C/D/E: gerçek hazırlanmış girdi kimliği, yeniden kullanım, koşu sürümü.

Bu testler **hiç model çağırmaz**. Kimlik testleri gerçek `prepare_arm_inputs` çıktısıyla (küçük
corpus PNG'si + sentetik gözlemler) çalışır; OCR/Hough koşmaz. Sınanan kural:

* C — `prediction_input_identity` modelin **gerçekten gördüğü** byte'lardan ve prompt'tan kurulur;
  prompt, görüntü byte'ı, görüntü sırası, overlay, gözlem tablosu, hazırlama kodu ve sözleşme sürümü
  değişince kimlik değişir; yalnız değerlendirici değişince değişmez.
* D — `reusable_attempt()` kayıtlı kimlik güncel kimliğe eşit değilse tahmini yeniden kullanmaz.
* E — değerlendirme kanıtı `evaluations/<evaluation_run_id>/` altında sürümlenir; eski koşu korunur.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from drawingto3d.observe import BBox, Frame, Observations, Primitive, SourceRef, TextObservation
from drawingto3d.semantic_candidate_reader import (OVERLAY_IMAGE_ID, RAW_IMAGE_ID, V_ARM, VE_ARM,
                                                   prepare_arm_inputs)
from drawingto3d.semantic_images import open_source
from drawingto3d.semantic_schema import PreparedImage

ROOT = Path(__file__).resolve().parents[1]


def _load_pilot():
    spec = importlib.util.spec_from_file_location("semread_001b_pilot_module_identity",
                                                  ROOT / "eval/semread_001b_pilot.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pilot sürücüsü yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot()

REAL_PAGES = pilot.PAGES_DIR            # yol düzeltmelerinden önceki gerçek corpus klasörü

PAGE = {"page_id": "page", "split": "dev", "group": "g", "path": "pyproject.toml",
        "type": "raster", "source_sha256": "a" * 64}


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, "REPORT_ROOT", tmp_path)
    monkeypatch.setattr(pilot, "state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", tmp_path / "attempts")
    monkeypatch.setattr(pilot, "PAGES_DIR", tmp_path / "pages")
    monkeypatch.setattr(pilot, "PREPARED_INPUT_DIR", tmp_path / "prepared")
    monkeypatch.setattr(pilot, "CORPUS_DIR", tmp_path / "corpus")
    monkeypatch.setattr(pilot, "GOLD_DIR", tmp_path / "corpus" / "gold")
    (tmp_path / "pages").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pages" / "page.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"p" * 32)
    return tmp_path


@pytest.fixture()
def page_png() -> Path:
    path = REAL_PAGES / "dev-plate-pocket.png"
    if not path.exists():
        pytest.skip("corpus sayfası yok: önce --corpus koşmalı")
    return path


@pytest.fixture()
def other_png() -> Path:
    """Byte'ları farklı, geçerli ikinci bir PNG (aynı corpus)."""
    for name in ("frozen-exercise-12.png", "dev-drawing-2.png", "frozen-enclosure.png"):
        path = REAL_PAGES / name
        if path.exists():
            return path
    pytest.skip("ikinci corpus sayfası yok: önce --corpus koşmalı")


def _observations() -> Observations:
    return Observations(source=SourceRef(ref="probe.png", sha256="b" * 64, page=0),
                        frame=Frame(width=400, height=300), text_placement="as-is",
                        primitives=[Primitive(id="g0", path_id="p0", kind="circle",
                                              centre=[100.0, 80.0], radius=12.0)],
                        texts=[TextObservation(id="t0", text="\u00d88 THRU", value=8.0, unit="mm",
                                               kind="diameter",
                                               bbox=BBox(x=120, y=70, w=30, h=10))])


def _identity(bundle: dict, prompt: str = "görev", arm: str = V_ARM,
              page: dict | None = None) -> str:
    record = pilot.prediction_input_record(page or PAGE, arm, bundle=bundle, prompt=prompt)
    return pilot.prediction_input_identity(record)


def _prepared(png: bytes, image_id: str = RAW_IMAGE_ID, kind: str = "full_page") -> PreparedImage:
    """Geçerli bir `PreparedImage`: byte'lar gerçek PNG, kimlik nötr."""
    if kind == "overlay":
        return PreparedImage(image_id=image_id, kind=kind, png=png, source_sha256="c" * 64,
                             render_mode="native_raster", observation_snapshot_id="snap-probe")
    return PreparedImage(image_id=image_id, kind=kind, png=png, source_sha256="c" * 64,
                         render_mode="native_raster")


# ------------------------------------------------------------ C: kimlik gerçek girdiden


def test_the_prompt_is_part_of_the_prediction_identity(page_png):
    source = open_source(page_png)
    bundle = prepare_arm_inputs(source, _observations(), image_id=RAW_IMAGE_ID, arm=V_ARM)

    assert _identity(bundle, "görev A") == _identity(bundle, "görev A")
    assert _identity(bundle, "görev A") != _identity(bundle, "görev B"), \
        "prompt metni değişince tahmin girdisi kimliği değişmeli"


def test_the_actual_image_bytes_are_part_of_the_prediction_identity(page_png, other_png):
    raw, other = page_png.read_bytes(), other_png.read_bytes()
    first = {"images": [_prepared(raw)], "observations": []}
    second = {"images": [_prepared(other)], "observations": []}

    assert raw != other
    assert _identity(first) != _identity(second), "görüntü byte'ı değişince kimlik değişmeli"


def test_the_image_order_is_part_of_the_prediction_identity(page_png, other_png):
    raw, other = page_png.read_bytes(), other_png.read_bytes()
    first = {"images": [_prepared(raw, RAW_IMAGE_ID), _prepared(other, OVERLAY_IMAGE_ID)],
             "observations": []}
    second = {"images": [_prepared(other, OVERLAY_IMAGE_ID), _prepared(raw, RAW_IMAGE_ID)],
              "observations": []}

    assert _identity(first) != _identity(second), "görüntü sırası kimliğe girmeli"


def test_the_ve_observation_table_and_overlay_change_the_identity(page_png, other_png):
    source = open_source(page_png)
    observations = _observations()
    ve_bundle = prepare_arm_inputs(source, observations, image_id=RAW_IMAGE_ID, arm=VE_ARM)

    without_table = {**ve_bundle, "observations": []}
    assert _identity(ve_bundle, "görev", VE_ARM) != _identity(without_table, "görev", VE_ARM), \
        "gözlem tablosu VE kimliğine girmeli"

    other_overlay = _prepared(other_png.read_bytes(), OVERLAY_IMAGE_ID, kind="overlay")
    swapped = {**ve_bundle, "images": [ve_bundle["images"][0], other_overlay]}
    assert _identity(ve_bundle, "görev", VE_ARM) != _identity(swapped, "görev", VE_ARM), \
        "overlay byte'ı VE kimliğine girmeli"


def test_preprocessing_code_and_contract_version_change_the_identity(page_png, tmp_path,
                                                                    monkeypatch):
    bundle = prepare_arm_inputs(open_source(page_png), _observations(), image_id=RAW_IMAGE_ID,
                                arm=V_ARM)
    baseline = _identity(bundle)

    probe = tmp_path / "preprocessing_probe.py"
    probe.write_text("v1", encoding="utf-8")
    monkeypatch.setattr(pilot, "PREPROCESSING_FILES", (str(probe),))
    assert _identity(bundle) != baseline, "hazırlama kodu değişince kimlik değişmeli"
    first = _identity(bundle)
    probe.write_text("v2", encoding="utf-8")
    assert _identity(bundle) != first

    monkeypatch.setattr(pilot, "CONTRACT_VERSION", pilot.CONTRACT_VERSION + "-probe")
    assert _identity(bundle) != first, "sözleşme sürümü kimliğe girmeli"


def test_an_evaluator_only_change_keeps_the_prediction_identity(page_png, tmp_path, monkeypatch):
    bundle = prepare_arm_inputs(open_source(page_png), _observations(), image_id=RAW_IMAGE_ID,
                                arm=V_ARM)
    baseline = _identity(bundle)

    probe = tmp_path / "evaluator_probe.py"
    probe.write_text("v1", encoding="utf-8")
    monkeypatch.setattr(pilot, "EVALUATION_IDENTITY_FILES", (str(probe),))
    before = pilot.evaluation_identity()
    probe.write_text("v2", encoding="utf-8")

    assert pilot.evaluation_identity() != before, "evaluator değişikliği değerlendirme kimliğini değiştirir"
    assert _identity(bundle) == baseline, "yalnız evaluator değişikliği tahmin girdisini değiştirmemeli"


def test_v_and_ve_share_raw_page_bytes_but_not_the_full_identity(page_png, sandbox, monkeypatch):
    source = open_source(page_png)
    observations = _observations()
    monkeypatch.setattr(pilot, "open_source", lambda _path: source)
    monkeypatch.setattr(pilot, "observe", lambda _path: observations)

    report = pilot.v_ve_raw_page_invariant(PAGE)
    assert report["ok"] is True, "V/VE ham image-1 byte'ı aynı olmalı"
    assert report["identities_differ"] is True, "VE kanıt eklediği için tam kimlik farklı olmalı"
    assert report["v_observation_table"] is None and report["ve_observation_table"]


def test_the_prepared_input_cache_is_bound_to_the_producer_identity(sandbox, monkeypatch):
    calls = {"source": 0}
    monkeypatch.setattr(pilot, "open_source",
                        lambda _path: (calls.__setitem__("source", calls["source"] + 1),
                                       object())[1])
    monkeypatch.setattr(pilot, "observe", lambda _path: object())
    monkeypatch.setattr(pilot, "prepare_arm_inputs",
                        lambda *_a, **_k: {"arm": V_ARM, "images": [], "observations": [],
                                           "arm_input_variant": V_ARM,
                                           "evidence_mode": pilot.arm_evidence_mode(V_ARM)})
    monkeypatch.setattr(pilot, "candidate_prompt", lambda *_a, **_k: "görev")

    first = pilot.prepared_input_record(PAGE, V_ARM)
    cached = pilot.prepared_input_record(PAGE, V_ARM)
    assert first == cached and calls["source"] == 1, "aynı üretici kimliğinde önbellek kullanılmalı"

    probe = sandbox / "producer_probe.py"
    probe.write_text("v1", encoding="utf-8")
    monkeypatch.setattr(pilot, "PRODUCER_IDENTITY_FILES", (str(probe),))
    fresh = pilot.prepared_input_record(PAGE, V_ARM)
    assert calls["source"] == 2, "üretici kimliği değişince kayıt yeniden hazırlanmalı"
    assert fresh == first, "yeniden hazırlanan kayıt aynı byte'lar için aynı olmalı"

    stored = json.loads((sandbox / "prepared" / "page-V.json").read_text(encoding="utf-8"))
    assert stored["key"] == pilot.prediction_input_cache_key(PAGE, V_ARM)


def test_a_missing_source_page_yields_no_prepared_input(sandbox):
    page = {**PAGE, "path": "examples/yok-boyle-dosya.pdf"}
    assert pilot.prepared_input_record(page, V_ARM) is None
    assert pilot.v_ve_raw_page_invariant(page)["ok"] is False


# ------------------------------------------------------------ D: yeniden kullanım kimliğe bağlı


def _record(page_id: str = "page", marker: str = "x") -> dict:
    return {"schema": pilot.PREDICTION_INPUT_SCHEMA, "contract_version": "probe",
            "page_id": page_id, "arm": V_ARM, "arm_input_variant": V_ARM, "evidence_mode": "none",
            "prompt_sha256": marker, "images": [], "observation_table_sha256": None,
            "preprocessing_identity": "probe"}


def _attempt(sandbox, monkeypatch, *, prediction_input: dict | None,
             send_attempted: bool = True) -> dict:
    monkeypatch.setattr(pilot, "prepared_input_record", lambda page, arm, refresh=False: prediction_input)
    page = {**PAGE, "page_id": "page"}
    directory = pilot.new_attempt_dir("page-V")
    attempt_id = f"page-V/{directory.name}"
    pilot.write_json(directory / "manifest.json",
                     pilot._attempt_manifest(page, V_ARM, attempt_id=attempt_id, phase="dev",
                                             prediction_input=prediction_input))
    pilot.write_json(directory / "result.json",
                     {"send_attempted": send_attempted, "gates": {"no_leakage": True},
                      "runtime_matches_expected": True, "arm": V_ARM})
    pilot.record_attempt(attempt_id, directory, page, V_ARM, phase="dev", verdict="pass",
                         gates={}, seconds=1.0)
    return page


def test_reuse_requires_the_stored_prediction_input_identity(sandbox, monkeypatch):
    """Kayıtlı kimlik == güncel kimlik ise tahmin yeniden kullanılabilir (P0R-FINAL-D)."""
    record = _record()
    page = _attempt(sandbox, monkeypatch, prediction_input=record)
    reused = pilot.reusable_attempt("page-V", page)

    assert reused is not None and reused["attempt_id"] == "page-V/attempt-0001"
    assert reused["prediction_input_identity"] == pilot.prediction_input_identity(record)
    directory = pilot.attempt_root("page-V") / "attempt-0001"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["prediction_input_identity"] == reused["prediction_input_identity"]
    assert manifest["prediction_input_record"] == "prediction-input.json"
    assert manifest["input_identity"], "eski sayfa-PNG kimliği meta veri olarak kalmalı"


def test_a_changed_prepared_input_stops_reuse(sandbox, monkeypatch):
    """P0R-FINAL-D: kayıtlı kimlik != güncel kimlik → tahmin yeniden kullanılmaz."""
    stored = _record(marker="eski")
    page = _attempt(sandbox, monkeypatch, prediction_input=stored)
    directory = next(path for path in pilot.attempt_root("page-V").glob("attempt-*"))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["prediction_input_identity"] == pilot.prediction_input_identity(stored)
    assert pilot.reusable_attempt("page-V", page) is not None

    monkeypatch.setattr(pilot, "prepared_input_record",
                        lambda page, arm, refresh=False: _record(marker="yeni"))
    assert pilot.reusable_attempt("page-V", page) is None, \
        "girdi kimliği değişince (prompt/byte/tablo) tahmin yeniden üretilmeli"

    monkeypatch.setattr(pilot, "prepared_input_record", lambda page, arm, refresh=False: stored)
    assert pilot.reusable_attempt("page-V", page) is not None, \
        "girdi kimliği yeniden eşitlenirse tahmin yeniden kullanılabilmeli"


def test_an_attempt_that_was_never_sent_is_not_reused(sandbox, monkeypatch):
    page = _attempt(sandbox, monkeypatch, prediction_input=_record(), send_attempted=False)
    assert pilot.reusable_attempt("page-V", page) is None


def test_an_unprovable_prepared_input_fails_closed(sandbox, monkeypatch):
    page = _attempt(sandbox, monkeypatch, prediction_input=_record())
    monkeypatch.setattr(pilot, "prepared_input_record", lambda page, arm, refresh=False: None)
    assert pilot.reusable_attempt("page-V", page) is None, \
        "hazırlanmış girdi kanıtlanamıyorsa yeniden kullanım olmamalı"


# ------------------------------------------------------------ E: sürümlenmiş değerlendirme


def test_evaluation_artifacts_are_versioned_and_old_runs_survive(sandbox, monkeypatch):
    monkeypatch.setattr(pilot, "prepared_input_record", lambda page, arm, refresh=False: None)
    first = pilot.evaluate()
    run_a = pilot.REPORT_ROOT / "evaluations" / first["evaluation_run_id"]
    assert run_a.is_dir() and first["evaluation_artifacts"]["directory"] == str(run_a)
    assert sorted(path.name for path in run_a.iterdir()) == \
        ["acceptance.json", "evaluation.json", "report.md", "selected-attempts.json"]
    digest_a = hashlib.sha256((run_a / "evaluation.json").read_bytes()).hexdigest()

    probe = sandbox / "evaluator_probe.py"
    probe.write_text("v1", encoding="utf-8")
    monkeypatch.setattr(pilot, "EVALUATION_IDENTITY_FILES", (str(probe),))
    second = pilot.evaluate()
    assert second["evaluation_run_id"] != first["evaluation_run_id"], \
        "yeni evaluator/gold sürümü yeni koşu kimliği üretmeli"
    run_b = pilot.REPORT_ROOT / "evaluations" / second["evaluation_run_id"]
    assert run_b.is_dir() and run_b != run_a

    assert hashlib.sha256((run_a / "evaluation.json").read_bytes()).hexdigest() == digest_a, \
        "eski koşunun kanıtı korunmalı"
    assert (run_a / "selected-attempts.json").exists() and (run_b / "report.md").exists()
    pointer = json.loads((pilot.REPORT_ROOT / "final" / "pointer.json").read_text(encoding="utf-8"))
    assert pointer["evaluation_run_id"] == second["evaluation_run_id"]
    assert pointer["directory"] == str(run_b.relative_to(pilot.REPORT_ROOT))
    assert (pilot.REPORT_ROOT / "acceptance.json").exists()
    assert (pilot.REPORT_ROOT / "final" / "report.md").exists()


def test_a_foreign_run_in_the_same_directory_is_not_overwritten(sandbox):
    payload = {"schema": "semread-001b-evaluation/1", "evaluation_run_id": "abc",
               "evaluation_identity": "x", "created_at": "t"}
    target = pilot.REPORT_ROOT / "evaluations" / "abc"
    target.mkdir(parents=True)
    (target / "evaluation.json").write_text(json.dumps({"evaluation_run_id": "baska"}), encoding="utf-8")
    (target / "kanit.txt").write_text("dokunma", encoding="utf-8")

    artifacts = pilot.write_evaluation_artifacts(payload, None, None,
                                                 {"schema": "semread-001b-selected-attempts/1"})
    assert artifacts["directory"].endswith("abc-2"), "çakışan kimlik yeni klasöre yazılmalı"
    assert (target / "kanit.txt").read_text(encoding="utf-8") == "dokunma"
