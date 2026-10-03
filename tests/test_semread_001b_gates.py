"""SEMREAD-001B — kapı (gate) testleri: bütçe fazı, VE girdisi, gönderim sınırı, yerel hata.

Bu testler **hiç model çağırmaz**: taşıma katmanı taklit edilir, bütçe ise scratch bir köke yazılır.
Amaç, inceleme raporundaki P0 bulgularının (faz karışıklığı, geçersiz overlay kimliği, yerel hatanın
gönderim gibi raporlanması) gerçek kod yollarında bağlanmasıdır.
"""

from __future__ import annotations

import hashlib
import importlib.util
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
    assert all(cell["cell"] in ("ready", "not_run", "to_run", "reuse")
               for cell in matrix["cells"])
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
