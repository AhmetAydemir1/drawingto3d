"""SEMREAD-001B — PLAN-8 §3–§4/§13/§25: izlenen gold spec'ler ve P5 manifest kapısı.

Kapsam:

* izlenen manifest, diskteki spec / kaynak çizim / üretilmiş referans hash'leriyle tutuyor mu;
* izlenen spec'ten referans deterministik yeniden üretiliyor mu (`dev-plate-pocket`, PDF sayfa);
* eksik izlenen spec, izlenmeyen üretilmiş gold, kaynak hash uyuşmazlığı ve spec hash
  uyuşmazlığı → dondurma kapısı kapanır (§3, §13);
* raster kuralları: `vision_checked` + claim başına görsel doğrulama kanıtı (§16);
* ölçülen hedef kutusu doğrulaması (§10);
* §11 döngüsel ölçek kanıtının reddi ve ölçek çıkarılamayan sayfada ölçülmüş kutunun geçerli
  olması (frozen-exercise-17 dersi).

Testler gerçek lab köküne yazmaz; sentetik senaryolar `tmp_path` altında kurulur.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_TOOL = ROOT / "eval" / "semread_001b_gold_manifest.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("semread_001b_gold_manifest", MANIFEST_TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _page(page_id: str) -> dict:
    table = {page["page_id"]: page for page in tool.pages()}
    return table[page_id]


def _raster_spec(**changes) -> dict:
    spec = {
        "page_type": "raster",
        "vision_checked": True,
        "scope": "test kapsamı",
        "exhaustiveness": {"scope": "test", "predicates": ["representation"]},
        "claims": [{
            "claim_id": "test-01",
            "name": "test",
            "target_box_norm": [0.1, 0.1, 0.2, 0.2],
            "representation": "diameter",
            "evidence": "ölçüldü",
            "source_evidence": "vision",
        }],
    }
    spec.update(changes)
    return spec


# --------------------------------------------------------------- izlenen dizin (gerçek lab, salt okuma)


def test_tracked_manifest_matches_disk() -> None:
    result = tool.check_manifest(require_all=False)
    assert result["ok"], result["problems"]
    assert result["coverage"] == f"{result['pages']}/{result['total']}"
    assert result["pages"] >= 5  # frozen-enclosure/exercise-12 + PDF sayfaları (P3 ilerledikçe artar)


def test_tracked_specs_pass_validation() -> None:
    for page in tool.pages():
        spec = tool.load_spec(page["page_id"])
        if spec is None:
            continue
        problems = tool.validate_spec(page, spec, tool._frame_px(page["page_id"]))
        assert problems == [], problems


def test_manifest_entries_match_a_fresh_build() -> None:
    """Spec değişip `--write` çalıştırılmadıysa hash'ler sapar; build ile karşılaştır."""
    fresh = {entry["page_id"]: entry for entry in tool.build_manifest()["pages"]}
    stored = {entry["page_id"]: entry for entry in json.loads(
        tool.MANIFEST.read_text(encoding="utf-8"))["pages"]}
    assert set(fresh) == set(stored)
    for page_id, entry in fresh.items():
        assert entry["spec_sha256"] == stored[page_id]["spec_sha256"], page_id
        assert entry["reference_sha256"] == stored[page_id]["reference_sha256"], page_id
        assert entry["source_sha256"] == stored[page_id]["source_sha256"], page_id
        assert entry["claim_count"] == stored[page_id]["claim_count"], page_id


def test_tracked_spec_regenerates_the_same_reference() -> None:
    """PLAN-8 §17 çekirdeği: izlenen spec'ten üretilen referans, diskteki dosyayla aynı olmalı.

    PDF sayfada (dev-plate-pocket) gözlem çıkarımı hızlı ve deterministiktir; raster sayfalar
    için kanıt `--verify` ile ayrıca alınır (§24 madde 13).
    """
    page_id = "dev-plate-pocket"
    result = tool.regenerate(page_id)
    text = json.dumps(result["reference"], ensure_ascii=False, indent=2)
    assert tool._sha256_text(text) == tool._sha256(tool.gold_dir() / f"{page_id}.json")
    stored_src = tool.gold_src_dir() / f"{page_id}.json"
    src_text = json.dumps(result["short"], ensure_ascii=False, indent=2)
    assert tool._sha256_text(src_text) == tool._sha256(stored_src)


def test_gold_generation_consumes_the_tracked_spec() -> None:
    """§24 madde 4: üretim aracı izlenen kanonik spec'i kullanır; `out/` kopyası yalnız yedek."""
    regions = tool._load("semread_001b_gold_regions_spec_source",
                         ROOT / "eval/semread_001b_gold_regions.py")
    path, source = regions.resolve_spec("frozen-enclosure", None)
    assert path == ROOT / "eval/semread_001b_gold/specs/frozen-enclosure.json"
    assert source == "izlenen kanonik"
    explicit, source = regions.resolve_spec("frozen-enclosure", str(path))
    assert explicit == path and source == "açık yol"
    with pytest.raises(SystemExit):
        # henüz hiçbir yerde spec'i olmayan sayfa (§24 madde 5+): ne izlenen ne yerel kopya
        regions.resolve_spec("frozen-views-exercise", None)


# ------------------------------------------------------------------------------- dondurma kapısı


def _manifest(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema": tool.MANIFEST_SCHEMA, "pages": entries},
                               ensure_ascii=False), encoding="utf-8")
    return path


def _entry(page_id: str, *, spec: str | None = None, gold: Path | None = None,
           **overrides) -> dict:
    page = _page(page_id)
    spec_file = ROOT / (spec or f"eval/semread_001b_gold/specs/{page_id}.json")
    source = ROOT / page["path"]
    reference = (gold or tool.gold_dir()) / f"{page_id}.json"
    generated = json.loads(reference.read_text(encoding="utf-8")) if reference.exists() else {}
    entry = {
        "page_id": page_id,
        "split": page.get("split"),
        "page_type": page.get("type"),
        "source": page["path"],
        "source_sha256": tool._sha256(source),
        "spec": str(spec_file.relative_to(ROOT)) if spec_file.is_relative_to(ROOT) else str(spec_file),
        "spec_sha256": tool._sha256(spec_file),
        "reference": str(reference.relative_to(ROOT)) if reference.is_relative_to(ROOT)
        else str(reference),
        "reference_sha256": tool._sha256(reference),
        "claim_count": len(generated.get("claims") or []),
        "annotator": generated.get("annotator"),
        "review_status": generated.get("review_status"),
        "vision_checked": bool(generated.get("vision_checked")),
        "exhaustiveness": "printed_features",
    }
    entry.update(overrides)
    return entry


def test_missing_tracked_spec_fails_freeze(tmp_path: Path) -> None:
    entry = _entry("frozen-exercise-13", spec="eval/semread_001b_gold/specs/frozen-exercise-13.json",
                   spec_sha256="0" * 64)
    path = _manifest(tmp_path, [entry])
    result = tool.check_manifest(require_all=True, manifest_path=path)
    assert not result["ok"]
    assert any("izlenen spec yok" in problem for problem in result["problems"])
    assert any("P5 dondurulamaz" in problem for problem in result["problems"])


def test_untracked_gold_fails_freeze(tmp_path: Path) -> None:
    """`out/` altında gold'u olup izlenen spec'i olmayan sayfa dondurmayı engeller (§3)."""
    entry = _entry("frozen-enclosure")
    path = _manifest(tmp_path, [entry])
    fake_gold = tmp_path / "gold"
    fake_gold.mkdir()
    (fake_gold / "frozen-exercise-13.json").write_text(
        (tool.gold_dir() / "frozen-enclosure.json").read_text(encoding="utf-8"), encoding="utf-8")
    result = tool.check_manifest(require_all=True, manifest_path=path, gold_directory=fake_gold)
    assert not result["ok"]
    assert any("izlenen spec'i olmayan üretilmiş gold" in problem for problem in result["problems"])
    # bilgilendirici mod: aynı durum uyarı olarak raporlanır, kapı kapanmaz
    relaxed = tool.check_manifest(require_all=False, manifest_path=path, gold_directory=fake_gold)
    assert any("izlenen spec'i olmayan üretilmiş gold" in warning for warning in relaxed["warnings"])


def test_source_hash_mismatch_fails_freeze(tmp_path: Path) -> None:
    entry = _entry("frozen-enclosure", source_sha256="0" * 64)
    path = _manifest(tmp_path, [entry])
    result = tool.check_manifest(require_all=True, manifest_path=path)
    assert not result["ok"]
    assert any("kaynak çizim hash'i uyuşmuyor" in problem for problem in result["problems"])


def test_spec_hash_mismatch_fails_freeze(tmp_path: Path) -> None:
    entry = _entry("frozen-enclosure", spec_sha256="0" * 64)
    path = _manifest(tmp_path, [entry])
    result = tool.check_manifest(require_all=True, manifest_path=path)
    assert not result["ok"]
    assert any("spec hash'i manifestle uyuşmuyor" in problem for problem in result["problems"])


def test_reference_hash_mismatch_fails_freeze(tmp_path: Path) -> None:
    entry = _entry("frozen-enclosure", reference_sha256="0" * 64)
    path = _manifest(tmp_path, [entry])
    result = tool.check_manifest(require_all=True, manifest_path=path)
    assert not result["ok"]
    assert any("referans hash'i manifestle uyuşmuyor" in problem for problem in result["problems"])


def test_require_all_needs_every_page(tmp_path: Path) -> None:
    path = _manifest(tmp_path, [_entry("frozen-enclosure")])
    relaxed = tool.check_manifest(require_all=False, manifest_path=path)
    frozen = tool.check_manifest(require_all=True, manifest_path=path)
    assert relaxed["ok"], relaxed["problems"]
    assert not frozen["ok"]
    assert frozen["coverage"] == f"1/{len(tool.pages())}"


# ------------------------------------------------------------------------------- spec kuralları


def test_raster_requires_vision_checked_and_evidence() -> None:
    page = _page("frozen-exercise-13")
    assert page["type"] == "raster"
    problems = tool.validate_spec(page, _raster_spec(vision_checked=False))
    assert any("vision_checked=true değil" in problem for problem in problems)
    spec = _raster_spec()
    spec["claims"][0]["source_evidence"] = "ocr"
    problems = tool.validate_spec(page, spec)
    assert any("görsel doğrulama kanıtı yok" in problem for problem in problems)
    assert tool.validate_spec(page, _raster_spec()) == []


@pytest.mark.parametrize("box, expected", [
    ([0.5, 0.5, 0.4, 0.6], "sıralı olmalı"),
    ([0.0, 0.0, 1.5, 1.0], "0..1 aralığında"),
    ([float("nan"), 0.1, 0.2, 0.2], "NaN/inf"),
    ([0.1, 0.1, 0.2], "dört sayı olmalı"),
])
def test_measured_box_validation(box, expected) -> None:
    page = _page("frozen-exercise-13")
    spec = _raster_spec()
    spec["claims"][0]["target_box_norm"] = box
    problems = tool.validate_spec(page, spec)
    assert any(expected in problem for problem in problems), problems


def test_measured_box_needs_documented_reason() -> None:
    page = _page("frozen-exercise-13")
    spec = _raster_spec()
    spec["claims"][0]["evidence"] = "okundu"
    spec["claims"][0]["source_evidence"] = "vision"
    problems = tool.validate_spec(page, spec)
    assert any("gerekçesi yazılmamış" in problem for problem in problems), problems
    spec["claims"][0]["target_reason"] = "leader ızgaralı büyütmeyle ölçüldü"
    assert tool.validate_spec(page, spec) == []


def test_missing_target_is_reported() -> None:
    page = _page("frozen-exercise-13")
    spec = _raster_spec()
    spec["claims"][0].pop("target_box_norm")
    problems = tool.validate_spec(page, spec)
    assert any("hedef yok" in problem for problem in problems)


# --------------------------------------------------- §11 döngüsel ölçek kanıtı (frozen-exercise-17 dersi)


def test_circular_scale_evidence_is_rejected() -> None:
    page = _page("frozen-exercise-13")
    spec = _raster_spec()
    spec["claims"][0].update({
        "size": 20.0,
        "unit": "mm",
        "corroboration": {"kind": "independent_scale", "basis": "Ø20,00 yazılı çağrısı",
                          "basis_value": 20.0, "scale_px_per_mm": 14.25},
    })
    problems = tool.validate_spec(page, spec)
    assert any("döngüsel kanıt" in problem for problem in problems), problems


def test_independent_scale_evidence_is_accepted() -> None:
    page = _page("frozen-exercise-13")
    spec = _raster_spec()
    spec["claims"][0].update({
        "size": 20.0,
        "unit": "mm",
        "corroboration": {"kind": "independent_scale", "basis": "10,00 soket derinliği",
                          "basis_value": 10.0, "scale_px_per_mm": 14.25},
    })
    assert tool.validate_spec(page, spec) == []


def test_target_box_valid_without_metric_calibration() -> None:
    """Ölçek çıkarılamayan sayfada ölçülmüş kutu geçerlidir (§11, frozen-exercise-17)."""
    page = _page("frozen-exercise-13")
    spec = _raster_spec()
    spec["claims"][0]["corroboration"] = {"kind": "none"}
    problems = tool.validate_spec(page, spec)
    assert problems == [], problems


def test_unknown_corroboration_kind_is_rejected() -> None:
    page = _page("frozen-exercise-13")
    spec = _raster_spec()
    spec["claims"][0]["corroboration"] = {"kind": "self_reference"}
    problems = tool.validate_spec(page, spec)
    assert any("kapalı kümede değil" in problem for problem in problems)
