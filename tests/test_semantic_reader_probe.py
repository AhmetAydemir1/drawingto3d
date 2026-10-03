"""Probe entegrasyonu: ortak runner kökü, dry-run, önbellek kimliği, kanıt index'i, altın ayrımı.

Buradaki testler gerçek model çağrısı yapmaz. Sınanan şey sürücünün sözleşmesi: ortak kilidi ve
bütçeyi kullanmak, dry-run'da hiçbir şey çalıştırmamak, eksik girdiyi hash'ten önce reddetmek, yeni
untracked semantic kodunu önbellek kimliğine katmak, attempt kanıtını dosya dosya doğrulamak ve altın
cevabı reader'ın girdisinden uzak tutmak.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load_probe():
    spec = importlib.util.spec_from_file_location("semread_probe",
                                                 ROOT / "eval/semantic_reader_probe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load_probe()

from drawingto3d import llama  # noqa: E402
from drawingto3d.llama import ModelInfo  # noqa: E402
from drawingto3d_lab.runner import LabRunner  # noqa: E402
from drawingto3d_lab.state import code_fingerprint, read_json, write_json  # noqa: E402

READER = ModelInfo(name="qwen3-vl:8b-instruct", digest="d" * 64,
                   capabilities=("vision", "completion"))


@pytest.fixture
def no_inference(monkeypatch):
    """Model çağrısını ve model listesini yerelde taklit et: hiçbir gerçek çağrı olmasın."""
    def forbidden(*args, **kwargs):
        raise AssertionError("dry-run sırasında model çağrısı yapıldı")

    monkeypatch.setattr(llama, "_ollama_chat", forbidden)
    monkeypatch.setattr(llama, "installed_models", lambda host=None: [READER])
    monkeypatch.setattr(probe, "ollama_runtime_version", lambda host=None: "0.0.0-test")
    return True


@pytest.fixture
def roots(tmp_path):
    return {"lab": tmp_path / "lab", "report": tmp_path / "report"}


# -- dry-run ve ortak runner kökü ---------------------------------------------------


def test_a_dry_run_calls_no_model_and_writes_nothing(roots, no_inference):
    code = probe.main(["--dry-run", "--cases", "L1", "--lab-root", str(roots["lab"]),
                       "--report-root", str(roots["report"]),
                       "--model", READER.name])
    assert code == 0
    assert not (roots["lab"] / "state.json").exists()
    assert not (roots["lab"] / "settings.json").exists()
    assert not (roots["lab"] / "runs").exists()
    assert not (roots["lab"] / "heavy.lock").exists()
    # Fixture'lar çağrıdan önce sabitlenir: vaka, prompt ve şema diske yazılmış olmalı.
    assert (probe.cases_dir(roots["report"]) / "L1-prompt.txt").exists()
    assert (probe.fixtures_dir(roots["report"]) / "L1/shape-a.png").exists()


def test_the_probe_uses_the_shared_runner_root_and_its_own_report_dir_only(roots, no_inference):
    probe.main(["--dry-run", "--cases", "L1", "--lab-root", str(roots["lab"]),
                "--report-root", str(roots["report"]), "--model", READER.name])
    runner = LabRunner(roots["lab"], root_repository=ROOT, code_hash=probe.code_identity)
    assert runner.status()["root"] == str(roots["lab"])
    # İkinci bir kilif kurulmadı: rapor kökünde lock/guard dosyası yok.
    assert not (probe.report_root(roots["report"]) / "heavy.lock").exists()
    assert not (probe.report_root(roots["report"]) / "heavy.guard").exists()


def test_jobs_are_named_prefixed_and_stay_inside_the_case_and_run_budgets(roots, no_inference):
    case = probe.case_definition("L1", roots["report"])
    job = probe.make_jobs([case], {"model": READER.name, "digest": READER.digest,
                                   "runtime_version": "t"}, lab_root=roots["lab"],
                          base=roots["report"])[0]
    assert job.id == "semread-001a-l1"
    assert job.timeout_seconds == probe.CASE_TIMEOUT_SECONDS == 600
    assert probe.RUN_TIMEOUT_SECONDS == 7200
    assert "{run_dir}" in job.command and "{result}" in job.command
    assert any(str(roots["report"] / "cases" / "L1-prompt.txt") == str(path) for path in job.inputs)


def test_a_missing_required_input_is_refused_before_hashing(roots, no_inference):
    case = probe.case_definition("L1", roots["report"])
    probe.write_gold(roots["report"])
    probe.prepare_case_files([case], roots["report"])
    write_json(probe.model_lock_path(roots["report"]), {"model": READER.name,
                                                        "digest": READER.digest})
    jobs = probe.make_jobs([case], {"model": READER.name, "digest": READER.digest,
                                    "runtime_version": "t"}, lab_root=roots["lab"],
                           base=roots["report"])
    Path(case["sources"]["shape-a"]["path"]).unlink()
    with pytest.raises(SystemExit) as raised:
        probe.require_inputs(jobs)
    assert "shape-a.png" in str(raised.value)


def test_every_emitted_job_command_parses_with_the_probe_parser(roots, no_inference):
    """Üretilen komut gerçekten ayrıştırılabilmeli: canlı koşuyu argparse reddederse kanıt üretilemez."""
    case = probe.case_definition("L1", roots["report"])
    probe.write_gold(roots["report"])
    probe.prepare_case_files([case], roots["report"])
    write_json(probe.model_lock_path(roots["report"]), {"model": READER.name,
                                                        "digest": READER.digest})
    jobs = probe.make_jobs([case], {"model": READER.name, "digest": READER.digest,
                                    "runtime_version": "t"}, lab_root=roots["lab"],
                           base=roots["report"])
    for job in jobs:
        parsed = probe.build_parser().parse_args([str(item) for item in job.command[2:]])
        assert parsed.worker is True and parsed.case_file == str(
            roots["report"] / "cases" / "L1-case.json")
        assert isinstance(parsed.timeout, float) and parsed.timeout == 300.0
        assert isinstance(parsed.num_ctx, int) and isinstance(parsed.num_predict, int)
        assert isinstance(parsed.temperature, float)
        assert "{run_dir}" in parsed.attempt_dir and "{result}" in parsed.result


def test_every_case_command_parses_including_the_pdf_and_raster_cases(roots, no_inference):
    """Vaka ayarları değişince komut argümanları da geçerli kalmalı (L3/L4 dahil)."""
    cases = [probe.case_definition(case_id, roots["report"]) for case_id in ("L3", "L4")]
    probe.write_gold(roots["report"])
    probe.prepare_case_files(cases, roots["report"])
    write_json(probe.model_lock_path(roots["report"]), {"model": READER.name,
                                                        "digest": READER.digest})
    jobs = probe.make_jobs(cases, {"model": READER.name, "digest": READER.digest,
                                   "runtime_version": "t"}, lab_root=roots["lab"],
                           base=roots["report"])
    assert len(jobs) == 2
    for job in jobs:
        parsed = probe.build_parser().parse_args([str(item) for item in job.command[2:]])
        assert parsed.worker is True and parsed.timeout == float(
            probe.case_definition("L1", roots["report"])["settings"]["timeout_s"])
        assert parsed.num_ctx > 0 and parsed.num_predict > 0


# -- önbellek kimliği ---------------------------------------------------------------


def _prepare_case(roots) -> None:
    case = probe.case_definition("L1", roots["report"])
    probe.write_gold(roots["report"])
    probe.prepare_case_files([case], roots["report"])
    write_json(probe.model_lock_path(roots["report"]), {"model": READER.name,
                                                        "digest": READER.digest})
    return case


def _job_key(roots, digest: str | None = None) -> str:
    """Vaka dosyaları hazırken bir işin önbellek anahtarı (dosyaları yeniden yazmaz)."""
    case = probe.case_definition("L1", roots["report"])
    jobs = probe.make_jobs([case], {"model": READER.name, "digest": digest or READER.digest,
                                    "runtime_version": "t"}, lab_root=roots["lab"],
                           base=roots["report"])
    runner = LabRunner(roots["lab"], root_repository=ROOT, code_hash=lambda: "sabit-kod")
    return runner.key_for(jobs[0])


def test_changing_the_prompt_or_schema_changes_the_cache_key(roots, no_inference):
    _prepare_case(roots)
    first = _job_key(roots)
    prompt = probe.cases_dir(roots["report"]) / "L1-prompt.txt"
    prompt.write_text(prompt.read_text() + "\nek satır", encoding="utf-8")
    second = _job_key(roots)
    assert first != second, "prompt değişince önbellek geçersiz olmalı"

    schema = probe.cases_dir(roots["report"]) / "L1-response-schema.json"
    payload = read_json(schema, default={})
    payload["title"] = "değişti"
    write_json(schema, payload)
    assert _job_key(roots) != second, "şema değişince önbellek geçersiz olmalı"


def test_the_model_digest_is_part_of_the_cache_identity(roots, no_inference):
    _prepare_case(roots)
    first = _job_key(roots)
    assert _job_key(roots, digest="e" * 64) != first, "model digest'i kimliğe girmeli"


def test_untracked_semantic_code_is_watched(monkeypatch):
    """Yeni dosyalar `git ls-files`'a girmez: probe onları açık watched listesine katmalı."""
    seen = {}

    def capture(root, watched=None):
        seen["watched"] = [str(Path(path).relative_to(ROOT)) for path in watched or []]
        return "kimlik"

    monkeypatch.setattr(probe, "code_fingerprint", capture)
    assert probe.code_identity() == "kimlik"
    for name in probe.SEMANTIC_WATCHED:
        assert name in seen["watched"], f"{name} watched listesinde olmalı"


def test_a_watched_untracked_file_really_changes_the_fingerprint(tmp_path):
    """Mekanizma testi: `code_fingerprint` watched dosyanın *içeriğini* hash'liyor mu?"""
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src/tracked.py").write_text("a\n")
    watched = repo / "src/untracked_semantic.py"
    watched.write_text("birinci sürüm\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "src/tracked.py"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "x"],
                   cwd=repo, check=True)

    first = code_fingerprint(repo, [watched])
    watched.write_text("ikinci sürüm\n")
    assert code_fingerprint(repo, [watched]) != first


# -- şema sentinel'i ve altın ayrımı ----------------------------------------------


def test_a_case_carrying_a_gold_field_is_refused(roots, no_inference):
    case = probe.case_definition("L1", roots["report"])
    case["images"][0]["expected_shapes"] = "triangle"
    with pytest.raises(SystemExit) as raised:
        probe._validate_case(case)
    assert "expected_shapes" in str(raised.value)

    case = probe.case_definition("L1", roots["report"])
    case["gold"] = {"image-1": "triangle"}
    with pytest.raises(SystemExit):
        probe._validate_case(case)


def test_the_gold_file_never_enters_a_sentence_prompt_or_job_input(roots, no_inference):
    case = probe.case_definition("L3", roots["report"])
    probe.write_gold(roots["report"])
    probe.prepare_case_files([case], roots["report"])
    write_json(probe.model_lock_path(roots["report"]), {"model": READER.name,
                                                        "digest": READER.digest})
    jobs = probe.make_jobs([case], {"model": READER.name, "digest": READER.digest,
                                    "runtime_version": "t"}, lab_root=roots["lab"],
                           base=roots["report"])
    gold = probe.gold_dir(roots["report"]) / "L3.json"
    gold_text = gold.read_text(encoding="utf-8")
    prompt = (probe.cases_dir(roots["report"]) / "L3-prompt.txt").read_text(encoding="utf-8")
    case_text = (probe.cases_dir(roots["report"]) / "L3-case.json").read_text(encoding="utf-8")

    assert "gold-sentinel" in gold_text
    for text in (prompt, case_text):
        assert "gold-sentinel" not in text, "altın iz vakaya/prompt'a girmemeli"
        assert "part.step" not in text.lower()
    assert all(gold != Path(path) for path in jobs[0].inputs), "altın dosya iş girdisi olmamalı"
    assert "plate with a pocket.STEP" not in prompt


def test_the_gold_isolation_check_flags_a_real_leak(roots, no_inference, tmp_path):
    """Sentinel ve **eşleme** izi aranır; sınıf sözlüğünün kendisi sözleşme olduğu için altın sayılmaz."""
    gold = {"gold-sentinel": "gold-sentinel-7f3ac1", "shapes": {"image-1": "triangle"}}
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    # Sınıf adı prompt'ta meşru şekilde geçebilir (seçenek listesi): bu bir sızıntı değildir.
    (attempt / "prompt.txt").write_text("sınıflar: triangle, square, circle, other, unknown")
    (attempt / "request-manifest.json").write_text("{")
    (attempt / "input-manifest.json").write_text("{}")
    clean = probe._gold_isolation(attempt, gold, roots["report"], "L1")
    assert clean["clean"] is True, clean["found"]
    assert clean["pairs_checked"] == ["image-1=triangle"]

    # Eşleme (kimlik ↔ sınıf) yan yana geçerse altın sızmış sayılır.
    (attempt / "prompt.txt").write_text("image-1 bir triangle çizimi")
    leaked = probe._gold_isolation(attempt, gold, roots["report"], "L1")
    assert leaked["clean"] is False and any("eşleme izi" in problem for problem in leaked["found"])

    (attempt / "prompt.txt").write_text("no ipucu")
    (attempt / "request-manifest.json").write_text('{"note": "gold-sentinel-7f3ac1"}')
    leaked = probe._gold_isolation(attempt, gold, roots["report"], "L1")
    assert leaked["clean"] is False and any("sentinel" in problem for problem in leaked["found"])


def test_the_record_completeness_flags_an_older_manifest():
    """Eksik alan sessizce yok sayılmaz: rapor kaydın hangi alanları taşıdığını söyler."""
    full = [{"image_id": "image-1", "sent_width_px": 12, "sent_height_px": 8}]
    assert probe._record_completeness(full) == {"request_has_image_ids": True,
                                                "request_has_sent_sizes": True}
    older = [{"index": 0, "sent_sha256": "a" * 64}]  # eski sürüm: kimlik/boyut yok, hash var
    assert probe._record_completeness(older) == {"request_has_image_ids": False,
                                                 "request_has_sent_sizes": False}
    assert probe._record_completeness([])["request_has_image_ids"] is False


def test_the_blocker_note_explains_an_open_row_from_evidence():
    """Engel uydurulmaz: açık satırın nedeni, ölçülmüş cevap eşleşmesinden okunur."""
    complete = {"request_has_image_ids": True, "request_has_sent_sizes": True}
    rows = {"A09": {"status": "open"}, "A01": {"status": "closed"}}
    evaluations = {"L1": {"present": True, "artifact_index": {"ok": True},
                          "record_completeness": complete, "code_fingerprint_matches": True,
                          "shapes": {"checked": True, "all_matched": False,
                                     "misses": ["image-2"], "missing_items": ["image-2"]}},
                   "L2": {"present": True, "artifact_index": {"ok": True},
                          "record_completeness": complete, "code_fingerprint_matches": True,
                          "shapes": {"checked": True, "all_matched": False,
                                     "misses": ["image-2"], "missing_items": []}},
                   "L3": {"present": False}, "L4": {"present": False}}
    note = probe._blocker_note(rows, evaluations)
    assert "L1" in note and "L2" in note and "A09" not in note
    assert "maddesi yok" in note and "kaçan=['image-2']" in note
    # Eksik kanıt da engel olarak adlandırılır: kapanmayan satırın nedeni yazılır.
    thin = dict(evaluations)
    thin["L1"] = {**evaluations["L1"], "record_completeness": {"request_has_image_ids": False,
                                                               "request_has_sent_sizes": True},
                  "code_fingerprint_matches": False}
    thin_note = probe._blocker_note(rows, thin)
    assert "image_id yok" in thin_note and "güncel kod kimliğiyle üretilmedi" in thin_note
    clean = {"L1": {"present": True, "artifact_index": {"ok": True}, "shapes": {"checked": False},
                    "record_completeness": complete, "code_fingerprint_matches": True},
             "L2": {"present": True, "artifact_index": {"ok": True}, "shapes": {"checked": False},
                    "record_completeness": complete, "code_fingerprint_matches": True},
             "L3": {"present": True, "artifact_index": {"ok": True}, "shapes": {"checked": False},
                    "record_completeness": complete, "code_fingerprint_matches": True},
             "L4": {"present": True, "artifact_index": {"ok": True}, "shapes": {"checked": False},
                    "record_completeness": complete, "code_fingerprint_matches": True}}
    all_closed = {f"A{index:02d}": {"status": "closed"} for index in range(1, 11)}
    assert probe._blocker_note(all_closed, clean) is None
    # Test kapısı açıkken neden de yazılır (eski ağacın testi kabul kapatmaz).
    stale = {**all_closed, "A02": {"status": "open", "problems": ["eski ağaç"]}}
    assert "eski ağaç" in probe._blocker_note(stale, clean)


def test_a_declared_overlay_resize_limit_is_really_applied(roots, no_inference):
    """Bildirilen ama uygulanmayan bir ayar yanıltıcıdır: overlay de limitini gerçekten uygular."""
    case = probe.case_definition("L3", roots["report"])
    for entry in case["images"]:
        if entry["kind"] in ("full_page", "overlay"):
            entry["resize_max_side"] = 700
    _, bundle = probe.build_bundle(case)
    manifest = bundle.manifest()
    limited = [image for image in manifest["images"] if image["kind"] in ("full_page", "overlay")]
    assert [image["kind"] for image in limited] == ["full_page", "overlay"]
    for image in limited:
        policy = image["resize_policy"]
        assert policy.get("max_side") == 700, f"{image['image_id']} limiti kayda geçmeli"
        assert policy.get("applied") is True, f"{image['image_id']} limiti gerçekten uygulanmalı"
        assert max(image["width_px"], image["height_px"]) == 700
    assert limited[1]["observation_snapshot_id"]


def test_the_crop_records_its_page_box_and_the_image_to_page_mapping(roots, no_inference):
    """Kırpma kaydı, kaynak sayfadaki kutuyu ve görsel→sayfa dönüşümünü taşımalı."""
    case = probe.case_definition("L3", roots["report"])
    _, bundle = probe.build_bundle(case)
    crop = [image for image in bundle.manifest()["images"] if image["kind"] == "crop"][0]
    assert crop["source_bbox_page_norm"] == case["images"][2]["bbox_page_norm"]
    matrix = crop["t_image_norm_to_page_norm"]
    assert matrix[0][0] == pytest.approx(0.12) and matrix[0][2] == pytest.approx(0.3)
    # Görselin sol üst köşesi sayfada (0.3, 0.3): dönüşüm gerçekten kırpma çerçevesini anlatıyor.
    assert crop["render_dpi"] == 600.0 and crop["render_mode"] == "pdf_rerender"
    assert crop["width_px"] < crop["height_px"] * 2


# -- kanıt index'i ----------------------------------------------------------------


def test_the_artifact_index_checks_every_file_not_just_the_result(tmp_path):
    directory = tmp_path / "attempt-1"
    (directory / "images").mkdir(parents=True)
    (directory / "result.json").write_text('{"product_verdict": "pass"}')
    (directory / "prompt.txt").write_text("prompt")
    (directory / "images/image-1.png").write_bytes(b"png")
    write_json(directory / "artifact-index.json", probe.artifact_index(directory))

    index = probe.verify_artifact_index(directory)
    assert index["ok"] is True and index["file_count"] == 3, "result dışındaki dosyalar da sayılmalı"

    (directory / "prompt.txt").write_text("değişti")
    index = probe.verify_artifact_index(directory)
    assert index["ok"] is False and any("hash" in problem for problem in index["problems"])

    (directory / "images/image-1.png").unlink()
    index = probe.verify_artifact_index(directory)
    assert index["ok"] is False and any("eksik" in problem for problem in index["problems"])


def test_an_attempt_without_an_index_is_not_valid_evidence(tmp_path):
    directory = tmp_path / "attempt-2"
    directory.mkdir()
    (directory / "result.json").write_text('{"product_verdict": "pass"}')
    assert probe.verify_artifact_index(directory)["ok"] is False


def test_the_runner_owned_files_are_not_case_evidence_but_a_stray_file_is(tmp_path):
    """Runner işten sonra manifest/complete/raw ekler: bunlar vaka kanıtı sayılmaz, başkası sayılır."""
    directory = tmp_path / "attempt-3"
    (directory / "raw").mkdir(parents=True)
    (directory / "result.json").write_text('{"product_verdict": "pass"}')
    write_json(directory / "artifact-index.json", probe.artifact_index(directory))
    (directory / "manifest.json").write_text("{}")
    (directory / "complete.json").write_text("{}")
    (directory / "raw/job.stdout").write_text("çıktı")
    (directory / "raw/job.stderr").write_text("")
    assert probe.verify_artifact_index(directory)["ok"] is True

    (directory / "gold.json").write_text('{"image-1": "triangle"}')
    failed = probe.verify_artifact_index(directory)
    assert failed["ok"] is False and any("gold.json" in problem for problem in failed["problems"])


def test_a_missing_answer_item_counts_as_a_miss(roots):
    """Yarım cevap başarı sayılamaz: altın görsel için madde yoksa eşleşme tam sayılmaz."""
    gold = {"shapes": {"image-1": "triangle", "image-2": "square"}}
    one_item = {"items": [{"image_id": "image-1", "description": "a triangle", "shape": "triangle"}]}
    match = probe._shape_match(gold, one_item)
    assert match["all_matched"] is False and match["missing_items"] == ["image-2"]
    assert match["per_image"]["image-2"]["note"].startswith("yanıtta")

    both = {"items": [{"image_id": "image-1", "description": "a triangle", "shape": "triangle"},
                      {"image_id": "image-2", "description": "a square", "shape": "square"}]}
    assert probe._shape_match(gold, both)["all_matched"] is True


def test_shape_matching_is_exact_class_equality_not_substring_search(roots):
    """Açıklama metninde anahtar sözcük aramak, cevabı şaşırtan modeli doğru yazardı."""
    gold = {"shapes": {"image-1": "triangle", "image-2": "square"}}
    hedged = {"items": [{"image_id": "image-1", "description": "not a square, maybe nothing",
                         "shape": "square"},
                        {"image_id": "image-2", "description": "either a triangle or a square",
                         "shape": "triangle"}]}
    match = probe._shape_match(gold, hedged)
    assert match["method"] == "exact_class_equality"
    assert match["all_matched"] is False
    assert sorted(match["misses"]) == ["image-1", "image-2"]


def test_an_unknown_or_missing_class_is_not_a_visual_success(roots):
    """`unknown` geçerli bir beyandır ama görsel kontrolü başarısız/kararsız bırakır."""
    gold = {"shapes": {"image-1": "triangle", "image-2": "square"}}
    for shape in ("unknown", "other", None):
        parsed = {"items": [{"image_id": "image-1", "shape": shape},
                            {"image_id": "image-2", "shape": "square"}]}
        match = probe._shape_match(gold, parsed)
        assert match["all_matched"] is False and "image-1" in match["misses"]


def test_the_sent_size_is_measured_even_when_no_resize_is_declared():
    """Boyut gidecek son byte'lardan okunur: yeniden boyutlandırma yokken de ölçü gerçek olmalı."""
    from drawingto3d.llama import _chat_request, _png_size

    import numpy as np
    import cv2
    canvas = np.full((8, 12, 3), 255, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", canvas)
    assert ok
    payload = encoded.tobytes()
    assert _png_size(payload) == (12, 8)

    _, manifest = _chat_request(model="m", prompt="p", images=[payload], temperature=0.0,
                                num_predict=8, num_ctx=1024, keep_alive="5m", response_format=None,
                                image_max_side=None, timeout=30.0)
    entry = manifest["images"][0]
    assert (entry["sent_width_px"], entry["sent_height_px"]) == (12, 8)
    assert entry["resize"]["applied"] is False
    assert entry["resize"]["to_px"] == [12, 8], "yeniden boyutlandırma yokken boyut kayda geçmeli"
    assert _png_size(b"png-degil") is None


def test_the_report_finds_the_image_id_by_matching_the_sent_hash_on_disk(tmp_path):
    """Eski kayıtta `image_id` alanı olmasa da kimlik, gönderilen hash ↔ diskteki dosya ile kurulur."""
    import cv2
    import numpy as np
    directory = tmp_path / "attempt"
    (directory / "images").mkdir(parents=True)
    ok, encoded = cv2.imencode(".png", np.full((8, 12, 3), 255, dtype=np.uint8))
    assert ok
    (directory / "images/image-2.png").write_bytes(encoded.tobytes())

    measured = probe._attempt_images(directory)
    assert measured["image-2"]["width_px"] == 12 and measured["image-2"]["height_px"] == 8
    # Kayıt yalnız hash taşıyor (eski sürüm): kimlik yine de bulunur.
    request = {"images": [{"index": 0, "sent_sha256": measured["image-2"]["sha256"]}]}
    join = probe.sent_image_join(request, measured)
    assert join["ids"] == ["image-2"] and join["all_bound"] is True
    assert "tek hash eşleşmesi" in (join["rows"][0]["note"] or "")


def test_identical_bytes_under_two_ids_are_not_merged_into_one_identity(tmp_path):
    """Aynı byte'lar iki farklı kimlikle gittiyse tek bir ad seçilmez: eşleme belirsiz yazılır."""
    directory = tmp_path / "attempt"
    (directory / "images").mkdir(parents=True)
    same = b"aynipng"
    (directory / "images/image-11.png").write_bytes(same)
    (directory / "images/image-27.png").write_bytes(same)
    on_disk = probe._attempt_images(directory)
    digest = next(iter(on_disk.values()))["sha256"]

    join = probe.sent_image_join({"images": [{"index": 0, "sent_sha256": digest}]}, on_disk)
    assert join["ids"] == [None] and join["all_bound"] is False
    assert join["ambiguous"] and "belirsiz" in join["ambiguous"][0]["note"]
    assert join["rows"][0]["hash_candidates"] == ["image-11", "image-27"]

    # Kimlik kayıtta varsa beyan kullanılır ve iki kayıt iki ayrı kimliğe bağlanır.
    declared = probe.sent_image_join(
        {"images": [{"index": 0, "sent_sha256": digest, "image_id": "image-11"},
                    {"index": 1, "sent_sha256": digest, "image_id": "image-27"}]}, on_disk)
    assert declared["ids"] == ["image-11", "image-27"] and declared["all_bound"] is True


def test_a_declared_identity_that_contradicts_the_bytes_is_not_a_join(tmp_path):
    """Beyan ölçümle çelişirse eşleme kurulmaz: kayıt kendini doğrulayamaz."""
    directory = tmp_path / "attempt"
    (directory / "images").mkdir(parents=True)
    (directory / "images/image-1.png").write_bytes(b"gercek-byte")
    on_disk = probe._attempt_images(directory)
    join = probe.sent_image_join(
        {"images": [{"index": 0, "sent_sha256": "f" * 64, "image_id": "image-1"}]}, on_disk)
    assert join["ids"] == [None] and join["all_bound"] is False
    assert "uyuşmuyor" in join["ambiguous"][0]["note"]


def test_the_request_record_names_each_image_at_its_position():
    """Actual-request kaydı tek başına hangi image_id'nin hangi sırada gittiğini söylemeli."""
    from drawingto3d.llama import _chat_request

    triangle, square = b"ucgen-bytes", b"kare-bytes"
    body, manifest = _chat_request(model="m", prompt="p", images=[square, triangle],
                                   temperature=0.0, num_predict=8, num_ctx=1024, keep_alive="5m",
                                   response_format=None, image_max_side=None, timeout=30.0,
                                   image_labels=["image-2", "image-1"])
    entries = manifest["images"]
    assert [entry["image_id"] for entry in entries] == ["image-2", "image-1"]
    assert entries[0]["index"] == 0 and entries[1]["index"] == 1
    # Sıra ile kimlik birlikte: ilk gönderilen görsel gerçekten karenin byte'ları olmalı.
    import base64
    import hashlib
    import json as _json
    sent = _json.loads(body)[0] if isinstance(_json.loads(body), list) else _json.loads(
        body)["messages"][0]["images"]
    decoded = [base64.standard_b64decode(item) for item in sent]
    assert decoded == [square, triangle]
    assert entries[0]["sent_sha256"] == hashlib.sha256(square).hexdigest()

    with pytest.raises(ValueError):
        _chat_request(model="m", prompt="p", images=[square, triangle], temperature=0.0,
                      num_predict=8, num_ctx=1024, keep_alive="5m", response_format=None,
                      image_max_side=None, timeout=30.0, image_labels=["image-1"])


# -- worker bütçesi ve girdi reddi ------------------------------------------------


def test_a_worker_refuses_when_the_live_budget_is_used_up(roots, no_inference, tmp_path):
    state = probe.load_state(roots["report"])
    state["live_calls"] = [{"case_id": "L1"}] * probe.LIVE_CALL_LIMIT
    probe.save_state(state, roots["report"])
    case = probe.case_definition("L1", roots["report"])
    case_file = roots["report"] / "L1-case.json"
    write_json(case_file, case)

    code = probe.main(["--worker", "--case-file", str(case_file),
                       "--attempt-dir", str(tmp_path / "attempt"),
                       "--result", str(tmp_path / "attempt/result.json"),
                       "--report-root", str(roots["report"]), "--model", READER.name,
                       "--model-digest", READER.digest])
    assert code == probe.EXIT_BUDGET
    assert not (tmp_path / "attempt/result.json").exists(), "bütçe dolunca çağrı yapılmaz"


def test_a_worker_refuses_a_missing_source_without_any_call(roots, no_inference, tmp_path):
    case = probe.case_definition("L1", roots["report"])
    case["sources"]["shape-a"]["path"] = str(tmp_path / "yok.png")
    case_file = roots["report"] / "L1-case.json"
    case_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(case_file, case)
    attempt = tmp_path / "attempt"

    code = probe.main(["--worker", "--case-file", str(case_file), "--attempt-dir", str(attempt),
                       "--result", str(attempt / "result.json"),
                       "--report-root", str(roots["report"]), "--model", READER.name,
                       "--model-digest", READER.digest])
    assert code == probe.EXIT_INPUT
    error = read_json(attempt / "response-error.json", default={})
    assert error["kind"] == "input_refused" and "yok.png" in error["detail"]
    assert read_json(attempt / "result.json", default=None) is None


# -- kabul tablosu -----------------------------------------------------------------


def test_the_transport_verdict_needs_every_gate():
    case = {"expected_images_per_call": 2}
    good = {"request": {"images_per_call": 2, "request_sha256": "a" * 64, "outcome": "ok",
                        "messages_layout": [{"index": 0, "image_ids": ["image-1"]}],
                        "images": [{"index": 0, "image_id": "image-1"},
                                   {"index": 1, "image_id": "image-2"}]},
            "raw_response": "{}", "parse": {"ok": True}, "schema": {"ok": True},
            "reference": {"ok": True, "coverage": {"exact": True}},
            "truncated": {"state": "complete", "metadata_complete": True}, "leakage": []}
    verdict, gates = probe.transport_verdict(case, good)
    assert verdict == "pass" and all(gates.values())

    for broken in ({"raw_response": None}, {"schema": {"ok": False}},
                   {"request": {"images_per_call": 1, "request_sha256": "a", "outcome": "ok"}},
                   {"truncated": {"state": "truncated", "metadata_complete": True}}, {"leakage": ["x"]},
                   {"request": {"images_per_call": 2, "request_sha256": "a", "outcome": "timeout"}}):
        verdict, gates = probe.transport_verdict(case, {**good, **broken})
        assert verdict == "fail" and not all(gates.values())


def test_an_unknown_truncation_cannot_pass_the_live_gate():
    """Kesilme durumu `unknown` (metadata gelmedi) canlı kabulü geçirmemeli."""
    case = {"expected_images_per_call": 1}
    outcome = {"request": {"images_per_call": 1, "request_sha256": "a", "outcome": "ok",
                           "messages_layout": [{"index": 0, "image_ids": ["image-1"]}],
                           "images": [{"index": 0, "image_id": "image-1"}]},
               "raw_response": "{}", "parse": {"ok": True}, "schema": {"ok": True},
               "reference": {"ok": True, "coverage": {"exact": True}},
               "truncated": {"state": "unknown", "metadata_complete": False}, "leakage": []}
    verdict, gates = probe.transport_verdict(case, outcome)
    assert verdict == "fail" and gates["not_truncated"] is False
    assert gates["completion_metadata"] is False
    # `stop` ama sayım metadata'sı yok: yine geçmez.
    partial = {**outcome, "truncated": {"state": "unknown", "metadata_complete": False,
                                        "done_reason": "stop"}}
    verdict, gates = probe.transport_verdict(case, partial)
    assert verdict == "fail" and gates["completion_metadata"] is False


def test_a_response_without_exact_coverage_cannot_pass_the_gate():
    case = {"expected_images_per_call": 2}
    outcome = {"request": {"images_per_call": 2, "request_sha256": "a", "outcome": "ok",
                           "messages_layout": [{"index": 0, "image_ids": ["image-1"]}],
                           "images": [{"index": 0, "image_id": "image-1"}]},
               "raw_response": "{}", "parse": {"ok": True}, "schema": {"ok": True},
               "reference": {"ok": True, "coverage": {"exact": False, "missing": ["image-2"]}},
               "truncated": {"state": "complete", "metadata_complete": True}, "leakage": []}
    verdict, gates = probe.transport_verdict(case, outcome)
    assert verdict == "fail" and gates["coverage_exact"] is False


def test_a_wrong_image_count_is_refused_by_the_verdict():
    case = {"expected_images_per_call": 3}
    outcome = {"request": {"images_per_call": 2, "request_sha256": "a", "outcome": "ok",
                           "messages_layout": [{"index": 0, "image_ids": ["image-1"]}],
                           "images": [{"index": 0, "image_id": "image-1"}]},
               "raw_response": "{}", "parse": {"ok": True}, "schema": {"ok": True},
               "reference": {"ok": True, "coverage": {"exact": True}},
               "truncated": {"state": "complete", "metadata_complete": True}, "leakage": []}
    verdict, gates = probe.transport_verdict(case, outcome)
    assert verdict == "fail" and gates["images_sent_as_expected"] is False


def _write_junit(report: Path, name: str, body: str, *, identity: str | None = None) -> Path:
    """Sentetik junit kanıtı: sidecar'ı da yazılır, yoksa kanıt (doğru şekilde) eski sayılır."""
    folder = probe.junit_dir(report)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.xml"
    path.write_text(body)
    write_json(folder / f"{name}.tree.json",
               {"identity": probe.evidence_identity() if identity is None else identity})
    return path


def _write_contract_junit(report: Path, row: str, *, package: str = "tests.test_semantic_reader_probe") -> Path:
    """Bir kabul satırının istediği sözleşme testlerini geçmiş gibi yaz (mekanizma testi)."""
    cases = "".join(f'<testcase classname="{package}" name="{name}"/>'
                    for name in probe.TEST_MAP[row]["cases"])
    return _write_junit(report, "semantic",
                        f'<testsuite tests="{len(probe.TEST_MAP[row]["cases"])}" failures="0">'
                        f'{cases}</testsuite>')


def _fake_live_attempt(roots, case_id="L1", *, labels=True, sizes=True, current_code=True,
                       layout=True, shapes=True, verdict="pass", gates=None,
                       state_verdict=None, duplicate_answer=False, answer_image_ids=None):
    """Canlı bir attempt'i diske taklit et (çağrı yok) — eksik alan bırakabilmek için alanlar seçilir."""
    probe.write_gold(roots["report"])
    case = probe.case_definition(case_id, roots["report"])
    probe.prepare_case_files([case], roots["report"])
    directory = roots["report"] / "runs" / "fake" / f"{case_id}-attempt"
    (directory / "images").mkdir(parents=True, exist_ok=True)
    (directory / "prompt.txt").write_text("prompt")
    ids = answer_image_ids or list(case["payload_order"])
    sent_ids = list(case["payload_order"])
    sent = []
    for index, image_id in enumerate(sent_ids):
        payload = f"png-{image_id}-{index}".encode()
        (directory / "images" / f"{image_id}.png").write_bytes(payload)
        entry = {"index": index, "sent_sha256": hashlib.sha256(payload).hexdigest()}
        if labels:
            entry["image_id"] = image_id
        if sizes:
            entry.update({"sent_width_px": 8, "sent_height_px": 8})
        sent.append(entry)
    gold = read_json(probe.gold_dir(roots["report"]) / f"{case_id}.json", default={})
    gold_shapes = gold.get("shapes") or {}
    items = []
    for image_id in ids:
        expected = gold_shapes.get(image_id, "other")
        items.append({"image_id": image_id, "description": f"a {expected}",
                      "shape": expected if shapes else "unknown", "region": None})
    if duplicate_answer and items:
        items = items + [dict(items[0])]
    write_json(directory / "response-parsed.json",
               {"schema_version": "semread-probe/2", "items": items})
    request = {"images_layout": "per_image_message_labeled" if layout else None, "images": sent}
    if layout:
        request["messages_layout"] = [{"index": index, "image_ids": [image_id],
                                       "label": f"Image ID: {image_id}"}
                                      for index, image_id in enumerate(ids)]
    write_json(directory / "request-manifest.json", request)
    write_json(directory / "manifest.json",
               {"code_fingerprint": probe.code_identity() if current_code else "eski-kod",
                "model": "qwen3-vl:8b-instruct"})
    default_gates = {"not_truncated": True, "completion_metadata": True, "transport_ok": True,
                     "coverage_exact": True}
    write_json(directory / "result.json",
               {"product_verdict": verdict, "case_id": case_id,
                "gates": default_gates if gates is None else gates})
    write_json(directory / "artifact-index.json", probe.artifact_index(directory))
    state = probe.load_state(roots["report"])
    state.setdefault("cases", {})[case_id] = {"attempt_dir": str(directory),
                                             "job": f"semread-001a-{case_id.lower()}",
                                             "product_verdict": state_verdict or verdict,
                                             "expected_images_per_call":
                                                 case["expected_images_per_call"],
                                             "gates": {"model_lock_matches": True}}
    probe.save_state(state, roots["report"])
    return directory


def test_an_attempt_without_image_ids_cannot_close_the_identity_row(roots):
    """Eksik istek kaydı kabul kapatmaz: kanıtın ne olduğu belli değilse satır açık kalır."""
    _fake_live_attempt(roots, "L1", labels=False)
    saved = read_json(probe.acceptance_path(roots["report"]), default={})
    probe.evaluate(roots["report"])
    saved = read_json(probe.acceptance_path(roots["report"]), default={})
    assert saved["acceptance"]["A09"]["status"] == "open", "image_id'siz kayıt kimlik satırını kapatmamalı"
    assert saved["acceptance"]["A12"]["status"] == "open"


def test_an_attempt_without_measured_sizes_cannot_close_the_identity_row(roots):
    _fake_live_attempt(roots, "L1", sizes=False)
    probe.evaluate(roots["report"])
    saved = read_json(probe.acceptance_path(roots["report"]), default={})
    assert saved["acceptance"]["A09"]["status"] == "open", "ölçülmemiş boyut kanıt sayılmaz"


def test_an_attempt_from_another_code_revision_cannot_close_a_row(roots):
    _fake_live_attempt(roots, "L1", current_code=False)
    probe.evaluate(roots["report"])
    saved = read_json(probe.acceptance_path(roots["report"]), default={})
    assert saved["acceptance"]["A09"]["status"] == "open", "başka revizyonun başarısı bugünü kapatmaz"


def test_a_complete_attempt_closes_the_identity_row(roots):
    """Kural kapatmayı imkânsız kılmamalı: alanlar tamsa ve ölçüm tuttuysa satır kapanır."""
    _fake_live_attempt(roots, "L1")
    _fake_live_attempt(roots, "L2")
    _write_contract_junit(roots["report"], "A09")
    probe.evaluate(roots["report"])
    saved = read_json(probe.acceptance_path(roots["report"]), default={})
    assert saved["acceptance"]["A09"]["status"] == "closed", saved["acceptance"]["A09"]
    assert saved["acceptance"]["A09"]["closure"] == "verdict"
    # A09 kapandı ama dört vaka yok: A10 ve A12 açık kalmalı (eksik kanıt kapatmaz).
    assert saved["acceptance"]["A10"]["status"] == "open"
    assert saved["acceptance"]["A12"]["status"] == "open"


def test_the_identity_row_needs_its_contract_tests_too(roots):
    """Canlı ölçüm tek başına yetmez: satırı koruyan sözleşme testleri de taze ve geçmiş olmalı."""
    _fake_live_attempt(roots, "L1")
    _fake_live_attempt(roots, "L2")
    saved = probe.evaluate(roots["report"])
    assert saved["acceptance"]["A09"]["status"] == "open"
    assert any("sözleşme testi" in item or "eksik kanıt dosyası" in item
               for item in saved["acceptance"]["A09"]["problems"])


def test_the_budget_can_be_raised_but_never_lowered(roots):
    """Tavan uzatması kayda geçer; düşürmek reddedilir (kanıt geriye küçülemez)."""
    probe.save_state(probe.load_state(roots["report"]), roots["report"])
    first = probe.extend_budget(roots["report"])
    assert first["limit"] == probe.LIVE_CALL_LIMIT_EXTENDED
    state = probe.load_state(roots["report"])
    assert probe.effective_limit(state) == probe.LIVE_CALL_LIMIT_EXTENDED
    assert state["budget_extensions"][0]["reason"] == probe.LIVE_CALL_LIMIT_REASON
    # Kaydetmek uzatmayı ezmemeli: tavan bir kez yükseltildiyse yükseltilmiş kalır.
    probe.save_state(state, roots["report"])
    assert probe.effective_limit(probe.load_state(roots["report"])) == probe.LIVE_CALL_LIMIT_EXTENDED
    with pytest.raises(SystemExit):
        probe.extend_budget(roots["report"], limit=2)


def test_every_case_declares_a_known_layout(roots):
    for case_id in probe.case_ids():
        case = probe.case_definition(case_id, roots["report"])
        assert case["settings"]["images_layout"] == "per_image_message_labeled", \
            "tüm vakalar tek kuralı kullanır: görsel başına mesaj + nötr kimlik metni"
        assert case["settings"]["images_layout"] in probe.LAYOUTS


def test_the_control_case_uses_new_neutral_ids_for_the_same_two_images(roots):
    """L5 kimlik kontrolü: aynı görseller, yeni kimlikler; beklenen eşleme yalnız altında."""
    l1 = probe.case_definition("L1", roots["report"])
    l5 = probe.case_definition("L5", roots["report"])
    assert l5["payload_order"] == ["image-11", "image-27"]
    assert {key: value["sha256"] for key, value in l5["sources"].items()} == \
           {key: value["sha256"] for key, value in l1["sources"].items()}
    gold = probe.write_gold(roots["report"])
    assert gold["L5"]["shapes"] == {"image-11": "triangle", "image-27": "square"}
    assert set(gold["L5"]["shapes"]) & set(l1["payload_order"]) == set()
    case_text = json.dumps(l5, ensure_ascii=False)
    assert "triangle" not in case_text and "square" not in case_text, "vaka altın sınıf taşımaz"


def test_a_missing_identity_in_the_answer_keeps_the_row_open(roots):
    _fake_live_attempt(roots, "L1", answer_image_ids=["image-1"])
    _fake_live_attempt(roots, "L2")
    probe.evaluate(roots["report"])
    saved = read_json(probe.acceptance_path(roots["report"]), default={})
    assert saved["acceptance"]["A09"]["status"] == "open"
    assert any("kapsam" in item for item in saved["acceptance"]["A09"]["problems"])


def test_a_duplicate_answer_item_keeps_the_row_open(roots):
    """Her görsele **tam bir** yanıt: aynı kimliği iki kez yazmak kabulü kapatmaz."""
    _fake_live_attempt(roots, "L1", duplicate_answer=True)
    _fake_live_attempt(roots, "L2")
    probe.evaluate(roots["report"])
    saved = read_json(probe.acceptance_path(roots["report"]), default={})
    assert saved["acceptance"]["A09"]["status"] == "open"


def test_a_state_attempt_verdict_contradiction_is_recorded_and_blocks_closure(roots):
    """State bayrağı ile attempt'in ham kanıtı çelişirse satır kapanmaz ve çelişki yazılır."""
    _fake_live_attempt(roots, "L1", verdict="fail", state_verdict="pass")
    _fake_live_attempt(roots, "L2")
    saved = probe.evaluate(roots["report"])
    entry = saved["evaluations"]["L1"]
    assert entry["state_attempt_contradiction"] is True
    assert entry["product_verdict"] == "fail", "karar ham kanıttan okunur"
    assert saved["acceptance"]["A09"]["status"] == "open"


def test_a_missing_message_layout_cannot_close_a_row(roots):
    _fake_live_attempt(roots, "L1", layout=False)
    _fake_live_attempt(roots, "L2")
    probe.evaluate(roots["report"])
    saved = read_json(probe.acceptance_path(roots["report"]), default={})
    assert saved["acceptance"]["A09"]["status"] == "open"
    assert any("mesaj düzeni" in item for item in saved["acceptance"]["A09"]["problems"])


def test_a_skipped_or_failing_sentinel_test_blocks_the_row(roots):
    """Sentinel/altın testi atlanmış ya da düşmüşse A11 kapanmaz."""
    for tag, expected in (("<skipped/>", "atlandı"), ("<failure>düştü</failure>", "geçmedi")):
        _write_junit(roots["report"], "semantic",
                     '<testsuite tests="1" failures="0">'
                     '<testcase classname="tests.test_semantic_reader" '
                     'name="test_the_gold_isolation_check_flags_a_real_leak">'
                     f'{tag}</testcase></testsuite>')
        _write_junit(roots["report"], "regression",
                     '<testsuite tests="1" failures="0">'
                     '<testcase classname="tests.test_inference_log" '
                     'name="test_a_single_image_call_still_counts_as_one"/></testsuite>')
        payload = probe.evaluate(roots["report"])
        assert payload["acceptance"]["A11"]["status"] == "open", tag
        assert any(expected in item for item in payload["acceptance"]["A11"]["problems"])


def test_adding_only_a_document_does_not_change_the_evidence_identity(tmp_path):
    """Yalnız bir Markdown eklemek test kanıtını bayatlatmamalı (kimlik git durumundan gelmez)."""
    before = probe.evidence_identity()
    docs = probe.ROOT / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    added = docs / "HERMES_GECICI_NOT.md"
    added.write_text("# geçici not\n", encoding="utf-8")
    try:
        assert probe.evidence_identity() == before
        assert "docs/HERMES_GECICI_NOT.md" not in probe.identity_detail()["files"]
    finally:
        added.unlink()


def test_changing_the_content_of_a_relevant_source_file_changes_the_evidence_identity(tmp_path):
    """İlgili bir kaynağın **içeriği** değişince kimlik değişmeli (M işareti değil, içerik)."""
    before = probe.evidence_identity()
    target = probe.ROOT / "src/drawingto3d/semantic_schema.py"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"\n# gecici-icerik-degisikligi\n")
        assert probe.evidence_identity() != before
    finally:
        target.write_bytes(original)
    assert probe.evidence_identity() == before, "içerik geri gelince kimlik de geri gelir"


def test_the_identity_includes_the_command_and_the_environment():
    detail = probe.identity_detail()
    assert "semantic" in detail["commands"] and "regression" in detail["commands"]
    assert detail["environment"]["python"] and detail["environment"]["pytest"]
    assert detail["files"]["pyproject.toml"]
    assert probe.identity_detail()["commands"]["semantic"][:3] == \
           [sys.executable, "-m", "pytest"]


def test_an_unknown_layout_is_refused_before_any_call(roots):
    case = probe.case_definition("L1", roots["report"])
    case["settings"]["images_layout"] = "iki-mesaj"
    with pytest.raises(SystemExit):
        probe.build_bundle(case)


def test_a_failing_test_cannot_close_an_acceptance_row(roots):
    _write_junit(roots["report"], "semantic",
                 '<testsuite tests="2" failures="1">'
                 '<testcase classname="tests.test_semantic_transport" name="test_three_images_are_serialised"/>'
                 '<testcase classname="tests.test_semantic_transport" name="test_reversing_the_image_list">'
                 '<failure>kırıldı</failure></testcase></testsuite>')
    results = probe._read_junit(roots["report"])
    status, evidence, _files, _problems = probe._test_gate(probe.TEST_MAP["A02"], results,
                                                           roots["report"])
    assert status == "open" and len(evidence) == 2, "düşen test kabul satırını kapatamaz"


def test_a_test_from_another_tree_cannot_close_an_acceptance_row(roots):
    """Revizyon farkı sessizce kapanmaz: sidecar'daki içerik kimliği bugünkü içeriğe uymalı."""
    _write_junit(roots["report"], "semantic",
                 '<testsuite tests="1" failures="0">'
                 '<testcase classname="tests.test_semantic_transport" '
                 'name="test_three_images_are_serialised"/></testsuite>',
                 identity="başka-bir-içerik-kimliği")
    results = probe._read_junit(roots["report"])
    status, evidence, _files, problems = probe._test_gate(probe.TEST_MAP["A02"], results,
                                                          roots["report"])
    assert evidence and results, "test bulundu"
    assert status == "open", "eski ağacın testi bugünkü kodu kapatmaz"
    assert any("test_three_images_are_serialised" in item for item in problems)


def test_a_test_recorded_without_a_fingerprint_is_not_evidence(roots):
    folder = probe.junit_dir(roots["report"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "semantic.xml").write_text(
        '<testsuite tests="1" failures="0">'
        '<testcase classname="tests.test_semantic_transport" name="test_three_images_are_serialised"/>'
        '</testsuite>')
    status, _evidence, _files, problems = probe._test_gate(probe.TEST_MAP["A02"],
                                                           probe._read_junit(roots["report"]),
                                                           roots["report"])
    assert status == "open" and problems, "parmak izi olmayan junit kanıt değildir"


def test_a_row_whose_declared_file_is_missing_stays_open(roots):
    """Bildirilen dosya yoksa başka setin testi satırı kapatmaz (A01 regression ister)."""
    _write_junit(roots["report"], "semantic",
                 '<testsuite tests="1" failures="0">'
                 '<testcase classname="tests.test_semantic_reader" '
                 'name="test_the_reader_sends_the_bundle_images_in_order_with_a_schema"/>'
                 '</testsuite>')
    status, evidence, files, problems = probe._test_gate(probe.TEST_MAP["A01"],
                                                         probe._read_junit(roots["report"]),
                                                         roots["report"])
    assert status == "open" and not evidence, "yazılı dosya eşleşmezse kanıt sayılmaz"
    assert not files and any("eksik kanıt dosyası" in item for item in problems)


def test_the_acceptance_document_says_which_rows_are_open_and_never_claims_complete(roots, no_inference):
    probe.main(["--dry-run", "--cases", "L1", "--lab-root", str(roots["lab"]),
                "--report-root", str(roots["report"]), "--model", READER.name])
    payload = probe.evaluate(roots["report"])
    saved = read_json(probe.acceptance_path(roots["report"]), default={})

    assert saved["acceptance"]["A09"]["status"] == "open"
    assert saved["acceptance"]["A10"]["status"] == "open"
    assert saved["semantic_evaluation"] == "not_evaluated"
    assert saved["cad_evaluation"] == "not_evaluated"
    assert "complete" not in saved["conclusion"].lower()
    assert "A01" in saved["open"]
    assert payload["live_calls_used"] == 0
    assert json.dumps(saved)  # belge gerçekten yazıldı
