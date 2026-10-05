"""SEMREAD-001D — girdi kurulum aracının testleri (PLAN-17 §31–§41, §93).

Kapsam (hepsi 0 inference; deftere **yazılmaz**):

* §35: dört dev sayfanın prepared raw page PNG'si + kayıt alanları (source path/sha256/boyut,
  page index/rotasyon, prepared sha256/width/height, `input_identity`, `preprocessing_identity`);
* §36/§37: V/VE ham sayfa byte'ı **aynı**; VE'nin overlay'i ve gözlem tablosu **ayrı hash'lenir**;
  tam girdi kimlikleri farklıdır;
* §33/§34: kurulum kaynaktan türetilir (kör kopya yok); 001B/001C yalnız byte-eşitlik kanıtı
  olarak karşılaştırılır;
* §39: araç gold/beklenen cevap/referans okumaz; model taşıma katmanına hiç dokunmaz (0-inference
  trap'i);
* §40: `--check` salt-okur ve **yeniden türeterek** doğrular — sayfa byte'ı, kimlik kaydı, kimlik
  bloğu (producer/preprocessing), ayarlar ve Round-1 deklarasyonu birebir olmalı; sapma kırmızıdır;
* §40/§41: kurulum sonrası `--dry-run --phase dev` Round 1 için `planned_real_calls = 4` verir;
  mevcut/çelişkili dosyanın üzerine yazılmaz; kaynak yoksa hiçbir şey yazılmaz (fail-closed);
  frozen sayfa kurulmaz (§32/§82: final holdout kullanıcıdan gelecek).
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "eval" / "semread_001d_inputs.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("semread_001d_inputs", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()
pilot = tool.pilot


def _canvas(width: int, height: int, shift: int = 0) -> np.ndarray:
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (width - 20, height - 20), (0, 0, 0), 2)
    cv2.circle(image, (width // 2 + shift, height // 2), min(width, height) // 5, (0, 0, 0), 2)
    cv2.putText(image, "O40", (width // 4, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2,
                cv2.LINE_AA)
    return image


@pytest.fixture
def lab(tmp_path, monkeypatch):
    """Sahte 001D kökü: iki dev (Round-1 adlarıyla) + bir frozen sayfa; kaynaklar sentetik PNG."""
    root = tmp_path / "repo"
    (root / "examples").mkdir(parents=True)
    source_a = root / "examples" / "synthetic-a.png"
    source_b = root / "examples" / "synthetic-b.png"
    cv2.imwrite(str(source_a), _canvas(300, 220))
    cv2.imwrite(str(source_b), _canvas(340, 240, shift=20))
    monkeypatch.setattr(pilot, "ROOT", root)
    monkeypatch.setattr(pilot, "EXPERIMENT_NAME", tool.EXPERIMENT)
    report_root = root / "out" / "lab" / tool.EXPERIMENT
    monkeypatch.setattr(pilot, "REPORT_ROOT", report_root)
    monkeypatch.setattr(pilot, "CORPUS_DIR", report_root / "corpus")
    monkeypatch.setattr(pilot, "GOLD_DIR", report_root / "corpus" / "gold")
    monkeypatch.setattr(pilot, "PAGES_DIR", report_root / "corpus" / "pages")
    monkeypatch.setattr(pilot, "PREPARED_INPUT_DIR", report_root / "corpus" / "prepared-inputs")
    monkeypatch.setattr(pilot, "ATTEMPT_ROOT", report_root / "attempts")
    monkeypatch.setattr(pilot, "PAGES", [
        {"page_id": "dev-plate-pocket", "path": "examples/synthetic-a.png", "split": "dev",
         "group": "synthetic"},
        {"page_id": "dev-flange-book", "path": "examples/synthetic-b.png", "split": "dev",
         "group": "synthetic"},
        {"page_id": "frozen-extra", "path": "examples/synthetic-a.png", "split": "frozen",
         "group": "synthetic"},
    ])
    return {"root": root, "report_root": report_root,
            "sources": {"dev-plate-pocket": source_a, "dev-flange-book": source_b}}


def _record(lab: dict) -> dict:
    return pilot.read_json(lab["report_root"] / "corpus" / tool.RECORD_NAME)


def _tree(lab: dict) -> dict:
    return {str(path.relative_to(lab["root"])): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(lab["root"].rglob("*")) if path.is_file()}


def test_write_materializes_dev_pages_and_records_identity(lab):
    result = tool.materialize()
    assert sorted(result["yazıldı"]) == ["dev-flange-book", "dev-plate-pocket"]
    record = _record(lab)
    assert record["schema"] == tool.SCHEMA
    assert record["experiment"] == tool.EXPERIMENT
    assert record["versions"]["contract_version"] == pilot.CONTRACT_VERSION
    assert record["identities"]["preprocessing_identity"] == pilot.preprocessing_identity()
    assert record["settings"]["image_max_side"] == pilot.IMAGE_MAX_SIDE
    # tmp kökte hazırlama dosyaları yok — kayıt bunu dürüstçe `None` yazar (pilot konvansiyonu).
    assert record["preprocessing_files"] == {relative: None for relative in pilot.PREPROCESSING_FILES}
    # §35: sayfa başına kaynak kimliği, prepared hash/boyut ve input_identity.
    assert [page["page_id"] for page in record["pages"]] == ["dev-plate-pocket", "dev-flange-book"]
    for page in record["pages"]:
        source = page["source"]
        assert source["path"] == f"examples/synthetic-{'a' if page['page_id'] == 'dev-plate-pocket' else 'b'}.png"
        assert source["sha256"] == hashlib.sha256(
            lab["sources"][page["page_id"]].read_bytes()).hexdigest()
        assert source["page_index"] == 0 and source["rotation"] == 0
        target = lab["report_root"] / "corpus" / "pages" / f"{page['page_id']}.png"
        assert page["raw_page"]["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
        frame = cv2.imread(str(target))
        assert frame is not None
        assert page["raw_page"]["height_px"] == frame.shape[0]
        assert page["raw_page"]["width_px"] == frame.shape[1]
        assert page["input_identity"] == pilot.input_identity(
            next(row for row in pilot.PAGES if row["page_id"] == page["page_id"]))
    # §32/§82: frozen sayfa kurulmaz; kayıt da onu taşımaz.
    pages_dir = lab["report_root"] / "corpus" / "pages"
    assert not (pages_dir / "frozen-extra.png").exists()
    assert {page["page_id"] for page in record["pages"]} == {"dev-plate-pocket", "dev-flange-book"}
    # §41: Round-1 deklarasyonu dört hücreyi görünür tutar.
    assert record["round1_cells"] == [
        {"page_id": "dev-plate-pocket", "arm": "V"}, {"page_id": "dev-plate-pocket", "arm": "VE"},
        {"page_id": "dev-flange-book", "arm": "V"}, {"page_id": "dev-flange-book", "arm": "VE"}]
    assert record["budget_snapshot"]["total_used"] == 0
    assert not (lab["report_root"] / "state.json").exists()


def test_v_and_ve_share_raw_page_bytes_but_ve_carries_separate_evidence(lab):
    tool.materialize()
    record = _record(lab)
    for page in record["pages"]:
        assert page["v_ve_raw_page_identical"] is True
        assert page["v_ve_identities_differ"] is True
        v, ve = page["arms"]["V"], page["arms"]["VE"]
        assert v["images"][0]["sha256"] == ve["images"][0]["sha256"]
        assert v["images"][0]["bytes"] == ve["images"][0]["bytes"]
        # §37: overlay ayrı ve ham sayfadan farklı; gözlem tablosu VE'de var, V'de yok.
        assert len(v["images"]) == 1
        assert len(ve["images"]) == 2
        overlay = ve["images"][1]
        assert overlay["sha256"] != ve["images"][0]["sha256"]
        assert overlay["bytes"] > 0
        assert ve["observation_table_sha256"] and ve["observation_table_sha256"] != \
            ve["images"][0]["sha256"]
        assert ve["observation_counts"]["sent"] > 0
        assert v["observation_table_sha256"] is None


def test_derived_arm_records_match_the_pilots_own_preparation(lab):
    """Tek kaynak: aracın türetimi pilot'un `prepared_input_record`'uyla birebir olmalı."""
    tool.materialize()
    page = next(row for row in pilot.PAGES if row["page_id"] == "dev-plate-pocket")
    recorded = next(row for row in _record(lab)["pages"] if row["page_id"] == "dev-plate-pocket")
    for arm in pilot.ARMS:
        assert recorded["arms"][arm] == pilot.prepared_input_record(page, arm, refresh=True)


def test_check_passes_after_write_and_does_not_touch_disk(lab):
    tool.materialize()
    before = _tree(lab)
    result = tool.check()
    assert result["ok"] is True
    assert result["problems"] == []
    assert result["pages_checked"] == 2
    assert _tree(lab) == before


def test_check_is_red_when_a_page_byte_changes(lab):
    tool.materialize()
    target = lab["report_root"] / "corpus" / "pages" / "dev-plate-pocket.png"
    data = bytearray(target.read_bytes())
    data[-1] ^= 0xFF
    target.write_bytes(bytes(data))
    result = tool.check()
    assert result["ok"] is False
    assert any("sayfa PNG kayıttan farklı" in problem for problem in result["problems"])
    assert any("input_identity değişmiş" in problem for problem in result["problems"])


def test_check_is_red_when_a_page_file_is_gone(lab):
    tool.materialize()
    (lab["report_root"] / "corpus" / "pages" / "dev-flange-book.png").unlink()
    result = tool.check()
    assert result["ok"] is False
    assert any("sayfa PNG yok" in problem for problem in result["problems"])


def test_check_is_red_when_the_preprocessing_identity_moves(lab, monkeypatch):
    """§40 'preprocessing identity current': ayar değişince kayıt bayatlar, doğrulama kırmızıdır."""
    tool.materialize()
    assert tool.check()["ok"] is True
    monkeypatch.setattr(pilot, "SETTINGS", {**pilot.SETTINGS, "image_max_side": 640})
    result = tool.check()
    assert result["ok"] is False
    assert any("preprocessing_identity" in problem for problem in result["problems"])


def test_check_without_a_record_is_red_not_silent(lab):
    result = tool.check()
    assert result["ok"] is False
    assert any("kimlik kaydı yok" in problem for problem in result["problems"])


def test_second_materialize_is_a_verified_no_op(lab):
    tool.materialize()
    before = {path: digest for path, digest in _tree(lab).items()
              if not path.endswith(tool.RECORD_NAME)}
    again = tool.materialize()
    assert again["yazıldı"] == []
    assert sorted(again["doğrulandı"]) == ["dev-flange-book", "dev-plate-pocket"]
    assert {path: digest for path, digest in _tree(lab).items()
            if not path.endswith(tool.RECORD_NAME)} == before  # sayfa byte'ları değişmedi
    assert tool.check()["ok"] is True


def test_materialize_refuses_to_overwrite_a_different_page(lab):
    pages_dir = lab["report_root"] / "corpus" / "pages"
    pages_dir.mkdir(parents=True)
    foreign = b"\x89PNG\r\n\x1a\n foreign-bytes"
    (pages_dir / "dev-plate-pocket.png").write_bytes(foreign)
    with pytest.raises(SystemExit, match="uyuşmuyor"):
        tool.materialize()
    assert (pages_dir / "dev-plate-pocket.png").read_bytes() == foreign
    assert not (pages_dir / "dev-flange-book.png").exists()  # all-or-nothing
    assert _record(lab) is None


def test_missing_source_fails_before_any_write(lab, monkeypatch):
    monkeypatch.setattr(pilot, "PAGES", [
        {"page_id": "dev-plate-pocket", "path": "examples/synthetic-a.png", "split": "dev",
         "group": "synthetic"},
        {"page_id": "dev-flange-book", "path": "examples/missing.png", "split": "dev",
         "group": "synthetic"},
    ])
    with pytest.raises(Exception, match="kaynak dosya yok"):
        tool.materialize()
    pages_dir = lab["report_root"] / "corpus" / "pages"
    assert not pages_dir.exists() or not list(pages_dir.glob("*.png"))
    assert _record(lab) is None


def test_round1_declaration_drift_is_detected(lab, monkeypatch):
    monkeypatch.setattr(pilot, "PAGES", [
        {"page_id": "dev-flange-book", "path": "examples/synthetic-b.png", "split": "dev",
         "group": "synthetic"}])
    with pytest.raises(SystemExit, match="Round 1"):
        tool.materialize()


def test_the_tool_reads_no_gold_and_never_calls_the_transport(lab, monkeypatch):
    source = TOOL_PATH.read_text(encoding="utf-8")
    for forbidden in ("GOLD_DIR", "semread_001b_gold", "FREEZE", "load_reference", "read_page(",
                      "OllamaChat", "LabRunner", "ollama"):
        assert forbidden not in source, f"girdi kurulumu {forbidden!r} içermemeli (§39)"
    monkeypatch.setattr(pilot, "read_page",
                        lambda *args, **kwargs: pytest.fail("girdi kurulumu gönderim yapamaz"))
    result = tool.materialize()
    assert sorted(result["doğrulandı"] + result["yazıldı"]) == ["dev-flange-book",
                                                                "dev-plate-pocket"]


def test_dry_run_plans_the_four_round1_calls_once_inputs_exist(lab):
    tool.materialize()
    result = pilot.run_live(phase="dev", dry_run=True,
                            pages=("dev-plate-pocket", "dev-flange-book"))
    plan = result["plan"]
    assert result["inference_calls"] == 0
    assert plan["planned_real_calls"] == 4
    assert all(cell["action"] == "call" for cell in plan["cells"])
    assert plan["budget"]["total_used"] == 0
    assert plan["budget"]["dev_used"] == 0
