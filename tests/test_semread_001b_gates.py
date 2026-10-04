"""SEMREAD-001B — kapı (gate) testleri: bütçe fazı, VE girdisi, gönderim sınırı, yerel hata.

Bu testler **hiç model çağırmaz**: taşıma katmanı taklit edilir, bütçe ise scratch bir köke yazılır.
Amaç, inceleme raporundaki P0 bulgularının (faz karışıklığı, geçersiz overlay kimliği, yerel hatanın
gönderim gibi raporlanması) gerçek kod yollarında bağlanmasıdır.
"""

from __future__ import annotations

import hashlib
import importlib.util
import dataclasses
import json
import threading
from pathlib import Path

import pytest

from drawingto3d.observe import Frame, Observations, Primitive, SourceRef, TextObservation, BBox
from drawingto3d.semantic_candidate_reader import (OVERLAY_IMAGE_ID, RAW_IMAGE_ID, V_ARM, VE_ARM,
                                                   prepare_arm_inputs, read_page)
from drawingto3d.semantic_candidates import candidate_prompt
from drawingto3d.semantic_images import open_source
from drawingto3d.semantic_schema import IMAGE_ID_PATTERN, PreparedImage

ROOT = Path(__file__).resolve().parents[1]


def _load_pilot():
    spec = importlib.util.spec_from_file_location("semread_001b_pilot_module",
                                                  ROOT / "eval/semread_001b_pilot.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pilot sürücüsü yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot()


@pytest.fixture()
def scratch_budget(tmp_path, monkeypatch):
    """Bütçe sayacını geçici köke taşı: gerçek çalışma kaydı bu testlerde değişmez."""
    monkeypatch.setattr(pilot, "REPORT_ROOT", tmp_path)
    monkeypatch.setattr(pilot, "state_path", lambda: tmp_path / "state.json")
    return tmp_path


# ------------------------------------------------------------- P0: faz / bütçe


def test_split_and_phase_are_separate_and_invalid_phase_is_refused(scratch_budget):
    refused = pilot.reserve_live_call("x-V", phase="frozen", arm="V", split="frozen",
                                      attempt_dir=scratch_budget / "a")
    assert refused["reserved"] is False
    assert "geçersiz faz" in refused["reason"]
    assert not pilot.load_state().get("live_calls"), "geçersiz faz bütçe harcamamalı"

    ok = pilot.reserve_live_call("frozen-1-V", phase="final", arm="V", split="frozen",
                                 attempt_dir=scratch_budget / "a")
    assert ok["reserved"] is True
    record = pilot.load_state()["live_calls"][0]
    assert record["phase"] == "final" and record["split"] == "frozen", \
        "veri bölümü (split) ile çağrı fazı (phase) ayrı alanlarda tutulmalı"
    assert record["send_state"] == "reserved"


def test_invalid_arm_and_split_are_refused(scratch_budget):
    for kwargs, needle in (
        ({"phase": "dev", "arm": "X", "split": "dev"}, "geçersiz kol"),
        ({"phase": "dev", "arm": "V", "split": "training"}, "geçersiz veri bölümü"),
    ):
        out = pilot.reserve_live_call("y", attempt_dir=scratch_budget / "a", **kwargs)
        assert out["reserved"] is False and needle in out["reason"]
    assert not pilot.load_state().get("live_calls")


def test_dev_final_and_total_caps_are_enforced_together(scratch_budget):
    accepted = [pilot.reserve_live_call(f"dev-{index}", phase="dev", arm="V", split="dev",
                                        attempt_dir=scratch_budget / "a")["reserved"]
                for index in range(pilot.LIVE_CALL_LIMIT_DEV + 1)]
    assert accepted.count(True) == pilot.LIVE_CALL_LIMIT_DEV
    assert accepted[-1] is False, "11. development çağrısı reddedilmeli"

    final = [pilot.reserve_live_call(f"final-{index}", phase="final", arm="VE", split="frozen",
                                     attempt_dir=scratch_budget / "a")["reserved"]
             for index in range(pilot.LIVE_CALL_LIMIT_FINAL)]
    assert final.count(True) == pilot.LIVE_CALL_LIMIT_FINAL

    over = pilot.reserve_live_call("extra", phase="final", arm="V", split="frozen",
                                   attempt_dir=scratch_budget / "a")
    assert over["reserved"] is False and "bitti" in over["reason"]
    report = pilot.budget_report()
    assert report["total_used"] == pilot.LIVE_CALL_LIMIT_TOTAL
    assert report["over_budget"] is False
    assert report["invalid_phase_records"] == 0


def test_the_total_cap_is_a_backstop_even_when_a_phase_cap_is_not_full(scratch_budget):
    """Toplam tavan, faz tavanlarından bağımsız olarak da uygulanmalı (bozuk/göçmüş sayaç)."""
    state = pilot.load_state()
    state["live_calls"] = ([{"case_id": f"d{index}", "arm": "V", "phase": "dev", "split": "dev",
                             "send_state": "sent"} for index in range(5)]
                           + [{"case_id": f"f{index}", "arm": "VE", "phase": "final",
                               "split": "frozen", "send_state": "sent"} for index in range(25)])
    pilot.save_state(state)
    out = pilot.reserve_live_call("after-cap", phase="dev", arm="V", split="dev",
                                  attempt_dir=scratch_budget / "a")
    assert out["reserved"] is False and "toplam bütçe bitti" in out["reason"]
    assert pilot.budget_report()["total_used"] == 30


def test_a_reserved_but_never_sent_call_still_counts(scratch_budget):
    pilot.reserve_live_call("orphan-V", phase="final", arm="V", split="dev",
                            attempt_dir=scratch_budget / "a")
    assert pilot.budget_report()["final_used"] == 1, \
        "gönderilip gönderilmediği belirsiz rezervasyon bütçede kalmalı"
    assert pilot.budget_report()["by_send_state"] == {"reserved": 1}


def test_concurrent_reservations_cannot_exceed_the_cap(scratch_budget):
    outcomes: list[bool] = []
    lock = threading.Lock()

    def reserve(index: int) -> None:
        out = pilot.reserve_live_call(f"thread-{index}", phase="final", arm="V", split="frozen",
                                      attempt_dir=scratch_budget / "a")
        with lock:
            outcomes.append(bool(out.get("reserved")))

    threads = [threading.Thread(target=reserve, args=(index,)) for index in range(40)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(outcomes) == pilot.LIVE_CALL_LIMIT_FINAL
    assert pilot.budget_report()["total_used"] == pilot.LIVE_CALL_LIMIT_FINAL


def test_send_state_transitions_are_recorded(scratch_budget):
    pilot.reserve_live_call("state-V", phase="dev", arm="V", split="dev",
                            attempt_dir=scratch_budget / "a")
    pilot.mark_send_state("state-V", phase="dev", state_name="sent", detail="1.2 sn")
    record = pilot.load_state()["live_calls"][0]
    assert record["send_state"] == "sent" and record["send_detail"] == "1.2 sn"
    assert pilot.budget_report()["by_send_state"] == {"sent": 1}


# ------------------------------------------------------------- P0: VE girdisi


def _observations(frame: tuple[int, int] = (400, 300)) -> Observations:
    return Observations(
        source=SourceRef(ref="probe.png", sha256="b" * 64, page=0),
        frame=Frame(width=frame[0], height=frame[1]),
        text_placement="as-is",
        primitives=[Primitive(id="g0", path_id="p0", kind="circle", centre=[100.0, 80.0],
                             radius=12.0)],
        texts=[TextObservation(id="t0", text="\u00d88 THRU", value=8.0, unit="mm",
                               kind="diameter", bbox=BBox(x=120, y=70, w=30, h=10))])


@pytest.fixture()
def page_png() -> Path:
    path = pilot.PAGES_DIR / "dev-plate-pocket.png"
    if not path.exists():
        pytest.skip("corpus sayfası yok: önce --corpus koşmalı")
    return path


def test_ve_bundle_uses_neutral_valid_ids_and_identical_raw_bytes(page_png):
    source = open_source(page_png)
    observations = _observations()
    v_bundle = prepare_arm_inputs(source, observations, image_id=RAW_IMAGE_ID, arm=V_ARM)
    ve_bundle = prepare_arm_inputs(source, observations, image_id=RAW_IMAGE_ID, arm=VE_ARM)

    assert [image.image_id for image in v_bundle["images"]] == [RAW_IMAGE_ID]
    assert [image.image_id for image in ve_bundle["images"]] == [RAW_IMAGE_ID, OVERLAY_IMAGE_ID]
    for image in ve_bundle["images"]:
        assert IMAGE_ID_PATTERN.match(image.image_id), "overlay kimliği de nötr olmalı"
    assert isinstance(ve_bundle["images"][1], PreparedImage)

    raw_v = v_bundle["images"][0].png
    raw_ve = ve_bundle["images"][0].png
    assert raw_v == raw_ve, "VE'nin ham sayfası V ile byte düzeyinde aynı olmalı"
    assert ve_bundle["images"][1].png != raw_ve, "overlay ham sayfadan farklı bir görüntü olmalı"
    assert v_bundle["observations"] == [], "V kolu gözlem tablosu görmemeli"
    assert ve_bundle["observations"], "VE kolu adreslenebilir gözlem tablosu görmeli"
    assert set(ve_bundle["observations"][0]) <= {"id", "kind", "text", "value", "unit", "region"}, \
        "gözlem satırı yalnız nötr alanlar taşımalı"


def test_the_two_prompts_differ_only_by_the_observation_table(page_png):
    source = open_source(page_png)
    observations = _observations()
    v_bundle = prepare_arm_inputs(source, observations, image_id=RAW_IMAGE_ID, arm=V_ARM)
    ve_bundle = prepare_arm_inputs(source, observations, image_id=RAW_IMAGE_ID, arm=VE_ARM)
    v_prompt = candidate_prompt([RAW_IMAGE_ID], observations=v_bundle["observations"] or None)
    ve_prompt = candidate_prompt([RAW_IMAGE_ID], observations=ve_bundle["observations"] or None)
    assert "g0" not in v_prompt and "t0" not in v_prompt, "V prompt'unda gözlem kimliği olmamalı"
    assert "g0" in ve_prompt and "t0" in ve_prompt, "VE prompt'u gözlem kimliklerini taşımalı"


# ------------------------------------------------------------- gönderim sınırı


class _FakeTransport:
    """Taşıma sınırında duran taklit: ağ yok, ama tüm çağrı parametreleri kaydedilir."""

    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.calls: list[dict] = []

    def complete(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        kwargs["stats"].update({"done_reason": "stop", "eval_count": 12, "prompt_eval_count": 40})
        kwargs["trace"].update({"model": pilot.MODEL, "options": {"temperature": 0.0},
                                "messages": [{"role": "user", "content": prompt}]})
        kwargs["raw_response"].update({"done": True})
        return self.answer


def test_worker_to_payload_contract_without_network(page_png):
    source = open_source(page_png)
    observations = _observations()
    bundle = prepare_arm_inputs(source, observations, image_id=RAW_IMAGE_ID, arm=VE_ARM)
    transport = _FakeTransport(json.dumps({"items": []}))
    outcome = read_page(transport, bundle, forbidden=[pilot.GOLD_SENTINEL], num_predict=256)

    call = transport.calls[0]
    assert call["images"] == [image.png for image in bundle["images"]], "görüntü sırası korunmalı"
    assert call["image_labels"] == [RAW_IMAGE_ID, OVERLAY_IMAGE_ID]
    assert call["images_layout"] == "per_image_message_labeled"
    assert call["image_label_prefix"] == "Image ID: "
    assert call["response_format"]["type"] == "object", "çıktı şeması isteğe bağlanmalı"
    assert call["num_predict"] == 256
    expected_images = [{"image_id": image.image_id, "sha256": hashlib.sha256(image.png).hexdigest(),
                        "bytes": len(image.png)} for image in bundle["images"]]
    assert outcome["images"] == expected_images
    assert pilot.MODEL in json.dumps(outcome["request"])


def test_leakage_and_parse_failure_are_recorded_not_swallowed(page_png):
    source = open_source(page_png)
    bundle = prepare_arm_inputs(source, _observations(), image_id=RAW_IMAGE_ID, arm=V_ARM)
    transport = _FakeTransport("bu bir JSON değil " + pilot.GOLD_SENTINEL)
    outcome = read_page(transport, bundle, forbidden=[pilot.GOLD_SENTINEL])

    assert outcome["parse"]["ok"] is False and outcome["parse"]["error"]
    assert outcome["leakage"] == [pilot.GOLD_SENTINEL], "sızıntı işareti kayda geçmeli"
    assert outcome["truncated"]["state"] == "complete", "tamamlama meta verisi okunmalı"


def test_a_transport_failure_is_recorded_with_its_kind(page_png):
    class Boom:
        def complete(self, prompt, **kwargs):
            error = RuntimeError("bağlantı yok")
            setattr(error, "transport_kind", "unreachable")
            raise error

    bundle = prepare_arm_inputs(open_source(page_png), _observations(), image_id=RAW_IMAGE_ID,
                                arm=V_ARM)
    outcome = read_page(Boom(), bundle, forbidden=[])
    assert outcome["outcome"] == "error" and outcome["failure_kind"] == "unreachable"
    assert "bağlantı yok" in outcome["detail"]


def test_a_local_preparation_error_is_not_reported_as_a_sent_call(scratch_budget, page_png,
                                                                  monkeypatch):
    page = {"page_id": "dev-plate-pocket", "split": "dev", "group": "g", "path": str(page_png),
            "type": "raster", "source_sha256": "c" * 64}
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts")
    monkeypatch.setattr(pilot, "PAGES_DIR", scratch_budget / "pages")
    (scratch_budget / "pages").mkdir(parents=True, exist_ok=True)
    (scratch_budget / "pages" / "dev-plate-pocket.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    monkeypatch.setattr(pilot, "open_source", lambda _path: open_source(page_png))

    def broken(*_args, **_kwargs):
        raise ValueError("overlay kimliği geçersiz")

    monkeypatch.setattr(pilot, "prepare_arm_inputs", broken)
    outcome = pilot.write_live_attempt(page, "VE", phase="final")

    assert outcome["verdict"] == "fail" and "overlay" in outcome["local_error"]
    directory = Path(outcome["directory"])
    recorded = json.loads((directory / "local-error.json").read_text(encoding="utf-8"))
    assert recorded["send_attempted"] is False and recorded["inference_calls"] == 0
    assert pilot.budget_report()["total_used"] == 0, \
        "yerel hazırlama hatası gerçek bütçe harcamamalı"


def test_the_matrix_counts_cells_not_frozen_pages_only(scratch_budget):
    matrix = pilot.final_matrix(reuse=False)
    assert matrix["totals"]["cells"] == 30
    assert matrix["totals"]["vlm_cells"] == pilot.FINAL_VLM_CELLS == 20
    assert matrix["totals"]["d_cells"] == len(pilot.PAGES) == 10
    assert matrix["totals"]["new_vlm_calls"] == 20, "yeniden kullanım kapalıyken 20 yeni çağrı"
    assert matrix["totals"]["new_d_runs"] == 10, "reuse kapalıyken 10 D koşusu (0 inference)"
    assert all(cell["cell"] in ("ready", "not_run", "to_run", "reuse", "valid_reuse")
               for cell in matrix["cells"])
    assert all(cell["kind"] in ("vlm", "deterministic") for cell in matrix["cells"])
    frozen_cells = [cell for cell in matrix["cells"] if cell["split"] == "frozen"]
    assert len(frozen_cells) == 6 * 3, "frozen hücreleri 6 sayfa × 3 kol olmalı"


# ------------------------------------------------------------- P0: değişmez attempt + kimlik


def test_attempt_dirs_are_immutable_and_numbered(scratch_budget, monkeypatch):
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts")
    first = pilot.new_attempt_dir("page-V")
    (first / "payload.txt").write_text("ilk", encoding="utf-8")
    second = pilot.new_attempt_dir("page-V")
    assert first.name == "attempt-0001" and second.name == "attempt-0002"
    assert first != second
    third = pilot.new_attempt_dir("page-V")
    assert third.name == "attempt-0003"
    assert (first / "payload.txt").read_text(encoding="utf-8") == "ilk", \
        "yeni attempt eski attempt klasörünü değiştirmemeli"
    assert [path.name for path in pilot.attempt_dirs("page-V")] == \
        ["attempt-0001", "attempt-0002", "attempt-0003"]
    assert pilot.latest_attempt_dir("page-V") == third


def test_attempt_history_is_appended_not_overwritten(scratch_budget, monkeypatch):
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts")
    page = {"page_id": "page", "split": "dev", "group": "g", "path": "examples/README.md"}
    for index in (1, 2):
        directory = pilot.new_attempt_dir("page-V")
        pilot.write_json(directory / "manifest.json", {"created_at": f"t{index}",
                                                       "producer_identity": "p"})
        pilot.record_attempt(f"page-V/{directory.name}", directory, page, "V", phase="dev",
                             verdict="pass" if index == 1 else "fail", gates={}, seconds=1.0)
    history = pilot.load_state()["attempts"]["page-V"]
    assert [row["attempt_id"] for row in history] == ["page-V/attempt-0001", "page-V/attempt-0002"]
    assert [row["verdict"] for row in history] == ["pass", "fail"]
    assert history[1]["producer_identity"] == "p", "attempt kaydı kimlik alanlarını taşımalı"


def test_producer_and_evaluator_identities_are_separate(tmp_path, monkeypatch):
    """Tahmini etkileyen dosya üretici kimliğini, değerlendirici dosyası yalnız onu değiştirir (P0-7)."""
    root = tmp_path / "root"
    (root / "src").mkdir(parents=True)
    producer_file = root / "src" / "reader.py"
    eval_file = root / "src" / "evaluation.py"
    producer_file.write_text("v1", encoding="utf-8")
    eval_file.write_text("v1", encoding="utf-8")
    monkeypatch.setattr(pilot, "ROOT", root)
    monkeypatch.setattr(pilot, "PRODUCER_IDENTITY_FILES", ("src/reader.py",))
    monkeypatch.setattr(pilot, "EVALUATION_IDENTITY_FILES", ("src/evaluation.py",))

    for arm, target in (("producer", producer_file), ("evaluation", eval_file)):
        before = (pilot.producer_identity(), pilot.evaluation_identity())
        target.write_text("v2", encoding="utf-8")
        after = (pilot.producer_identity(), pilot.evaluation_identity())
        target.write_text("v1", encoding="utf-8")
        if arm == "producer":
            assert after[0] != before[0], "üretici dosyası üretici kimliğini değiştirmeli"
            assert after[1] == before[1], "üretici dosyası değerlendirme kimliğini değiştirmemeli"
        else:
            assert after[0] == before[0], \
                "evaluator/gold düzeltmesi ham tahmini geçersiz kılmamalı"
            assert after[1] != before[1], "değerlendirici dosyası değerlendirme kimliğini değiştirmeli"


def test_a_changed_page_png_makes_the_old_attempt_stale(scratch_budget, monkeypatch):
    pages = scratch_budget / "pages"
    pages.mkdir(parents=True, exist_ok=True)
    png = pages / "page.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"a" * 32)
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts")
    monkeypatch.setattr(pilot, "PAGES_DIR", pages)
    page = {"page_id": "page", "split": "dev", "group": "g", "path": "examples/README.md"}

    directory = pilot.new_attempt_dir("page-V")
    manifest = pilot._attempt_manifest(page, "V", attempt_id="page-V/attempt-0001", phase="final")
    pilot.write_json(directory / "manifest.json", manifest)
    pilot.write_json(directory / "result.json",
                     {"send_attempted": True, "gates": {"no_leakage": True},
                      "runtime_matches_expected": True, "arm": "V"})
    pilot.record_attempt("page-V/attempt-0001", directory, page, "V", phase="final",
                         verdict="pass", gates={}, seconds=1.0)
    assert pilot.reusable_attempt("page-V", page) is not None

    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"b" * 32)      # girdi değişti
    assert pilot.reusable_attempt("page-V", page) is None, \
        "girdi byte'ları değişen attempt yeniden kullanılmamalı"


def test_an_attempt_from_another_producer_identity_is_not_reused(scratch_budget, monkeypatch):
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts")
    monkeypatch.setattr(pilot, "PAGES_DIR", scratch_budget / "pages")
    (scratch_budget / "pages").mkdir(parents=True, exist_ok=True)
    page = {"page_id": "page", "split": "dev", "group": "g", "path": "examples/README.md"}
    directory = pilot.new_attempt_dir("page-V")
    pilot.write_json(directory / "manifest.json",
                     {"producer_identity": "eski", "evaluation_identity": "eski",
                      "expected_digest": pilot.EXPECTED_DIGEST, "settings": pilot.SETTINGS})
    pilot.write_json(directory / "result.json",
                     {"send_attempted": True, "gates": {"no_leakage": True},
                      "runtime_matches_expected": True, "arm": "V"})
    pilot.record_attempt("page-V/attempt-0001", directory, page, "V", phase="dev",
                         verdict="pass", gates={}, seconds=1.0)
    assert pilot.reusable_attempt("page-V", page) is None


def test_a_runtime_mismatch_blocks_the_send_but_stays_in_the_ledger(scratch_budget, monkeypatch):
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts")
    monkeypatch.setattr(pilot, "PAGES_DIR", scratch_budget / "pages")
    (scratch_budget / "pages").mkdir(parents=True, exist_ok=True)
    (scratch_budget / "pages" / "page.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"c" * 32)
    monkeypatch.setattr(pilot, "runtime_identity",
                        lambda: {"version": "0.31.0", "model": {}, "error": None})
    monkeypatch.setattr(pilot, "open_source", lambda _path: object())
    monkeypatch.setattr(pilot, "observe", lambda _path: object())
    monkeypatch.setattr(pilot, "prepare_arm_inputs",
                        lambda *a, **k: {"images": [], "observations": [], "page_image_id": "image-1",
                                         "arm": "V"})
    monkeypatch.setattr(pilot, "candidate_prompt", lambda *a, **k: "görev")
    page = {"page_id": "page", "split": "frozen", "group": "g", "path": "examples/README.md",
            "type": "raster", "source_sha256": "d" * 64}

    outcome = pilot.write_live_attempt(page, "V", phase="final")
    assert outcome["verdict"] == "blocked" and "runtime" in outcome["reason"]
    result = json.loads((Path(outcome["directory"]) / "result.json").read_text(encoding="utf-8"))
    assert result["blocking_kind"] == "runtime_mismatch" and result["send_attempted"] is False
    report = pilot.budget_report()
    assert report["by_send_state"] == {"not_sent_runtime_mismatch": 1}, \
        "gönderilmeyen rezervasyon sessizce silinmemeli"
    assert report["total_used"] == 1


# ------------------------------------------------------------- P0R: kimlik ve bayatlık


def _valid_attempt(scratch_budget, monkeypatch, tmp_path, *, arm="V", page_id="page"):
    """Geçerli (yeniden kullanılabilir) bir V attempt'i kur: gerçek kimliklerle."""
    pages = scratch_budget / "pages_ok"
    pages.mkdir(parents=True, exist_ok=True)
    (pages / f"{page_id}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"e" * 32)
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts_ok")
    monkeypatch.setattr(pilot, "PAGES_DIR", pages)
    page = {"page_id": page_id, "split": "dev", "group": "g", "path": "examples/README.md"}
    directory = pilot.new_attempt_dir(f"{page_id}-{arm}")
    attempt_id = f"{page_id}-{arm}/{directory.name}"
    pilot.write_json(directory / "manifest.json",
                     pilot._attempt_manifest(page, arm, attempt_id=attempt_id, phase="dev"))
    pilot.write_json(directory / "result.json",
                     {"send_attempted": True, "gates": {"no_leakage": True},
                      "runtime_matches_expected": True, "arm": arm})
    pilot.record_attempt(attempt_id, directory, page, arm, phase="dev", verdict="pass",
                         gates={}, seconds=1.0)
    return page, directory


def test_an_evaluator_change_does_not_invalidate_the_raw_prediction(scratch_budget, monkeypatch,
                                                                   tmp_path):
    """P0R-1: yalnız evaluator/gold düzeltmesi geçerli ham tahmini geçersiz kılmaz."""
    page, directory = _valid_attempt(scratch_budget, monkeypatch, tmp_path)
    assert pilot.reusable_attempt("page-V", page) is not None

    probe = tmp_path / "evaluator_probe.py"
    probe.write_text("v1", encoding="utf-8")
    monkeypatch.setattr(pilot, "EVALUATION_IDENTITY_FILES", (str(probe),))
    before_eval = pilot.evaluation_identity()
    probe.write_text("v2", encoding="utf-8")          # yalnız değerlendirici değişti
    assert pilot.evaluation_identity() != before_eval
    assert pilot.reusable_attempt("page-V", page) is not None, \
        "değerlendirme kimliği değişince ham tahmin bayatlamamalı"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["evaluation_identity"] != pilot.evaluation_identity(), \
        "eski değerlendirme artık bayat sayılmalı (yeni değerlendirme yeni inference istemez)"


def test_a_producer_change_does_invalidate_the_raw_prediction(scratch_budget, monkeypatch,
                                                              tmp_path):
    probe = tmp_path / "producer_probe.py"
    probe.write_text("v1", encoding="utf-8")
    monkeypatch.setattr(pilot, "PRODUCER_IDENTITY_FILES", (str(probe),))
    page, _directory = _valid_attempt(scratch_budget, monkeypatch, tmp_path)
    assert pilot.reusable_attempt("page-V", page) is not None
    probe.write_text("v2", encoding="utf-8")          # tahmini etkileyen dosya değişti
    assert pilot.reusable_attempt("page-V", page) is None, \
        "üretici kimliği değişince ham tahmin yeniden üretilmeli"


def test_pilot_file_is_not_part_of_producer_identity(scratch_budget):
    assert "eval/semread_001b_pilot.py" not in pilot.PRODUCER_IDENTITY_FILES
    assert "eval/semread_001b_pilot.py" in pilot.EVALUATION_IDENTITY_FILES
    assert "src/drawingto3d/semantic_run_contract.py" in pilot.PRODUCER_IDENTITY_FILES


def test_the_request_hash_fields_are_separate(scratch_budget):
    trace = {"request_sha256": "a" * 64, "model": "m", "messages": [{"role": "user"}]}
    hashes = pilot.request_hashes(trace)
    assert hashes["http_request_sha256"] == "a" * 64, "gerçek HTTP gövdesi hash'i taşınmalı"
    assert hashes["request_manifest_sha256"] != "a" * 64
    assert len(hashes["request_manifest_sha256"]) == 64
    assert pilot.request_hashes(None) == {"http_request_sha256": None,
                                          "request_manifest_sha256": None}


def test_every_created_attempt_directory_has_exactly_one_history_entry(scratch_budget, monkeypatch):
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts_hist")
    monkeypatch.setattr(pilot, "PAGES_DIR", scratch_budget / "pages_hist")
    (scratch_budget / "pages_hist").mkdir(parents=True, exist_ok=True)
    (scratch_budget / "pages_hist" / "page.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"f" * 32)
    monkeypatch.setattr(pilot, "runtime_identity",
                        lambda: {"version": "0.31.0", "model": {}, "error": None})
    monkeypatch.setattr(pilot, "prepare_arm_inputs",
                        lambda *a, **k: {"images": [], "observations": [],
                                         "page_image_id": "image-1", "arm": "V"})
    monkeypatch.setattr(pilot, "candidate_prompt", lambda *a, **k: "görev")
    monkeypatch.setattr(pilot, "open_source", lambda _path: object())
    monkeypatch.setattr(pilot, "observe", lambda _path: object())

    def broken(*_args, **_kwargs):
        raise ValueError("hazırlık hatası")

    page = {"page_id": "page", "split": "dev", "group": "g", "path": "examples/README.md",
            "type": "raster", "source_sha256": "9" * 64}
    monkeypatch.setattr(pilot, "prepare_arm_inputs", broken)
    outcomes = [pilot.write_live_attempt(page, "V", phase="dev") for _ in range(2)]
    monkeypatch.setattr(pilot, "prepare_arm_inputs",
                        lambda *a, **k: {"images": [], "observations": [],
                                         "page_image_id": "image-1", "arm": "V"})
    outcomes.append(pilot.write_live_attempt(page, "V", phase="dev"))   # runtime reddi

    directories = sorted(path.name for path in pilot.attempt_dirs("page-V"))
    history = pilot.load_state()["attempts"]["page-V"]
    assert len(directories) == len(history) == 3, "her attempt klasörü tek bir geçmiş kaydı olmalı"
    assert [row["state"] for row in history] == ["local_error", "local_error",
                                                 "blocked_runtime_mismatch"]
    assert all(row["attempt_id"].endswith(path) for row, path in zip(history, directories))


def test_a_stale_deterministic_attempt_is_not_matrix_ready(scratch_budget, monkeypatch):
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts_d")
    monkeypatch.setattr(pilot, "PAGES_DIR", scratch_budget / "pages_d")
    (scratch_budget / "pages_d").mkdir(parents=True, exist_ok=True)
    (scratch_budget / "pages_d" / "dev-plate-pocket.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"1" * 32)
    page = next(row for row in pilot.PAGES if row["page_id"] == "dev-plate-pocket")
    directory = pilot.new_attempt_dir("dev-plate-pocket-D")
    pilot.write_json(directory / "response-parsed.json", {"items": []})
    pilot.write_json(directory / "manifest.json", {"producer_identity": "eski"})
    pilot.record_attempt(f"dev-plate-pocket-D/{directory.name}", directory, page, "D",
                         phase="deterministic", verdict="pass", gates={}, seconds=0.5)
    assert pilot.reusable_d_attempt(page) is None, "bayat D attempt yeniden kullanılmamalı"

    cell = next(cell for cell in pilot.final_matrix()["cells"]
                if cell["page_id"] == "dev-plate-pocket" and cell["arm"] == "D")
    assert cell["cell"] == "to_run" and cell["stale_detected"] is True


# ------------------------------------------------- P0R-FINAL: donmuş sözleşme == gerçek istek


def test_every_frozen_setting_is_actually_sendable(scratch_budget):
    """PLAN-3 §4/§12: donmuş sözleşme, taşımanın gerçekten gönderebildiği ayarlardan oluşmalı."""
    supported = {field.name for field in dataclasses.fields(pilot.ChatSettings)}
    # `input_strategy` sözleşme-üstü kavram; `image_label_prefix` taşımaya ayrı kwarg olarak
    # gider (aşağıda okuyucu testi onu bağlar).
    sendable = set(pilot.SETTINGS) - {"input_strategy", "image_label_prefix"}
    assert sendable <= supported, f"taşımada karşılığı olmayan donmuş ayar: {sendable - supported}"
    assert "top_p" not in pilot.SETTINGS and "seed" not in pilot.SETTINGS, \
        "gönderilmeyen seçenek donmuş sözleşmede yer almamalı (PLAN-3 §4 alternatifi)"
    assert pilot.SETTINGS["images_layout"] == pilot.IMAGES_LAYOUT
    assert pilot.SETTINGS["image_label_prefix"] == pilot.IMAGE_LABEL_PREFIX


def test_reader_literals_come_from_the_run_contract(scratch_budget):
    """PLAN-3 §7: okuyucuda kopya literal kalmamalı."""
    source = (pilot.ROOT / "src/drawingto3d/semantic_candidate_reader.py").read_text(encoding="utf-8")
    assert "per_image_message_labeled" not in source.split("def read_page", 1)[1]
    assert '"Image ID: "' not in source
    assert "IMAGES_LAYOUT" in source and "IMAGE_LABEL_PREFIX" in source
    assert pilot.SETTINGS["images_layout"] == "per_image_message_labeled"


def test_an_unsupported_frozen_setting_blocks_the_send(scratch_budget, monkeypatch):
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", scratch_budget / "attempts_fs")
    monkeypatch.setattr(pilot, "PAGES_DIR", scratch_budget / "pages_fs")
    (scratch_budget / "pages_fs").mkdir(parents=True, exist_ok=True)
    (scratch_budget / "pages_fs" / "page.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"a" * 32)
    monkeypatch.setitem(pilot.SETTINGS, "top_k", 7)              # taşımada olmayan donmuş ayar
    sent = {"calls": 0}

    monkeypatch.setattr(pilot, "open_source", lambda _path: object())
    monkeypatch.setattr(pilot, "observe", lambda _path: object())
    monkeypatch.setattr(pilot, "prepare_arm_inputs",
                        lambda *a, **k: {"arm": "V", "images": [], "image_ids": [],
                                         "page_image_id": "image-1", "observations": []})

    def must_not_send(*_args, **_kwargs):
        sent["calls"] += 1
        raise AssertionError("desteklenmeyen donmuş ayarla gönderim yapılmamalı")

    monkeypatch.setattr(pilot, "read_page", must_not_send)
    page = {"page_id": "page", "split": "dev", "group": "g", "path": "examples/README.md",
            "type": "raster", "source_sha256": "8" * 64}
    outcome = pilot.write_live_attempt(page, "V", phase="dev")
    monkeypatch.delitem(pilot.SETTINGS, "top_k")
    assert outcome["verdict"] == "blocked" and sent["calls"] == 0
    result = json.loads((Path(outcome["directory"]) / "result.json").read_text(encoding="utf-8"))
    assert result["blocking_kind"] == "unsupported_frozen_setting"
    assert result["send_attempted"] is False and result["inference_calls"] == 0
    history = pilot.load_state()["attempts"]["page-V"]
    assert history[-1]["state"] == "blocked_unsupported_setting"
    ledger = pilot.budget_report()
    # Rezervasyon gönderimden önce yapılır; gönderilmemiş istek defterde **görünür** kalır
    # (runtime uyuşmazlığıyla aynı politika), sessizce silinmez.
    assert ledger["total_used"] == 1
    assert ledger["by_send_state"].get("not_sent_unsupported_setting") == 1
    assert ledger["by_send_state"].get("sent", 0) == 0


# ------------------------------------------- P0R-FINAL: kanonik meta veri + liste kabul kodu


def test_model_metadata_has_one_parser(scratch_budget):
    """PLAN-3 §8: elle /api/tags ayrıştırması kalmamalı."""
    source = (pilot.ROOT / "eval/semread_001b_pilot.py").read_text(encoding="utf-8")
    assert "/api/tags" not in source, "ikinci model meta verisi yolu kalmamalı"
    assert "as_dict()" in source and "find_model(" in source and "installed_models(" in source
    info = pilot.runtime_identity()
    assert info["parser"] == "installed_models/find_model/as_dict"
    if info["error"] is None:                     # yerel Ollama ayakta
        assert info["version"] == pilot.EXPECTED_RUNTIME
        assert (info["model_canonical"] or {}).get("digest") == pilot.EXPECTED_DIGEST
        assert info["model"] == info["model_canonical"]
    else:                                          # runtime yoksa da biçim aynı olmalı
        assert info["model"] == {} and info["model_canonical"] is None


def test_attempt_records_flattening_survives_every_state_shape(scratch_budget):
    """PLAN-3 §9: eski dict, yeni liste, karışık ve boş durum."""
    old = {"attempts": {"a-V": {"attempt_id": "a-V/attempt-0001", "verdict": "pass"}}}
    new = {"attempts": {"a-V": [{"attempt_id": "a-V/attempt-0001", "verdict": "fail"},
                                {"attempt_id": "a-V/attempt-0002", "verdict": "pass"}]}}
    mixed = {"attempts": {"a-V": {"attempt_id": "a-V/attempt-0001", "verdict": "pass"},
                          "b-V": [{"attempt_id": "b-V/attempt-0001", "verdict": "pass"}]}}
    assert [r["verdict"] for r in pilot.all_attempt_records(old)] == ["pass"]
    assert [r["verdict"] for r in pilot.all_attempt_records(new)] == ["fail", "pass"]
    assert sorted(r["attempt_id"] for r in pilot.all_attempt_records(mixed)) == \
        ["a-V/attempt-0001", "b-V/attempt-0001"]
    assert pilot.all_attempt_records({}) == []
    assert pilot.all_attempt_records(None) == []
    assert pilot.all_attempt_records({"attempts": {}}) == []


def test_acceptance_rows_consumes_flattened_records(scratch_budget, monkeypatch):
    """PLAN-3 §9: kabul üretimi dört geçmiş biçiminde de çalışmalı."""
    payload = pilot.evaluate(write_report=False)
    shapes = [{"attempts": {"a-V": {"verdict": "pass", "arm": "V", "split": "frozen"}}},
              {"attempts": {"a-V": [{"verdict": "fail", "arm": "V", "split": "dev"},
                                    {"verdict": "pass", "arm": "V", "split": "frozen"}]}},
              {"attempts": {}}, {}]
    for state in shapes:
        monkeypatch.setattr(pilot, "read_json", lambda _path, _s=state: _s)
        rows = pilot.acceptance_rows(payload)
        assert isinstance(rows, dict) and rows
