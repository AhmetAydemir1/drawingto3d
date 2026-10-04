"""SEMREAD-001B — PLAN-8 §3–§4/§13/§25: izlenen gold spec'ler ve P5 manifest kapısı.

Kapsam:

* izlenen manifest, diskteki spec / kaynak çizim / üretilmiş referans hash'leriyle tutuyor mu;
* izlenen spec'ten referans deterministik yeniden üretiliyor mu (`dev-plate-pocket`, PDF sayfa);
* eksik izlenen spec, izlenmeyen üretilmiş gold, kaynak hash uyuşmazlığı ve spec hash
  uyuşmazlığı → dondurma kapısı kapanır (§3, §13);
* raster kuralları: `vision_checked` + claim başına görsel doğrulama kanıtı (§16);
* ölçülen hedef kutusu doğrulaması (§10);
* §11 döngüsel ölçek kanıtının reddi ve ölçek çıkarılamayan sayfada ölçülmüş kutunun geçerli
  olması (frozen-exercise-17 dersi);
* §6 grafik düzeyi döngüsellik: karşılıklı (A→B, B→A) ya da claim seti içinde köklenen ölçek
  kanıtı reddedilir; setin dışındaki doğrusal datum kökü kabul edilir (PLAN-9 §4–§6);
* §15 kararlı `gold_content_identity`: üstveri (created_at) değişse de kimlik sabit; aynı içerik
  yeniden üretilince manifest bayt bayt aynı;
* §16–§17 atomik `--freeze`: kapsam + hash'ler + TÜM sayfaların yeniden üretim kanıtı + kimlik;
  saklanan referans geçerli olsa bile yeniden üretim sapıyorsa kapı kapanır.

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
    # 10/10 sonrası: frozen-views-exercise de izlenen kanonik spec'e kavuştu (§48).
    tracked, source = regions.resolve_spec("frozen-views-exercise", None)
    assert tracked == ROOT / "eval/semread_001b_gold/specs/frozen-views-exercise.json"
    assert source == "izlenen kanonik"
    with pytest.raises(SystemExit):
        # hiçbir yerde spec'i olmayan sayfa (§24 madde 5+): ne izlenen ne yerel kopya
        regions.resolve_spec("korpus-disi-sayfa", None)


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


# ------------------------------------------- §6 grafik düzeyi döngüsel kanıt (PLAN-9 §4–§6)


def _two_claim_spec() -> dict:
    """A (Ø20) dayanağı B (Ø22), B dayanağı A — ex17'de bulunan karşılıklı döngü deseni (§4)."""
    return {
        "page_type": "raster",
        "vision_checked": True,
        "scope": "test kapsamı",
        "exhaustiveness": {"scope": "test", "predicates": ["size"]},
        "claims": [
            {"claim_id": "mutual-a", "name": "Ø20 boru", "target_box_norm": [0.1, 0.1, 0.2, 0.2],
             "form": "diameter", "size": 20.0, "unit": "mm", "evidence": "ölçüldü",
             "source_evidence": "vision",
             "corroboration": {"kind": "independent_scale", "basis": "Ø22,00 kolon bandı",
                               "basis_value": 22.0, "scale_px_per_mm": 17.7}},
            {"claim_id": "mutual-b", "name": "Ø22 kolon", "target_box_norm": [0.2, 0.1, 0.3, 0.2],
             "form": "diameter", "size": 22.0, "unit": "mm", "evidence": "ölçüldü",
             "source_evidence": "vision",
             "corroboration": {"kind": "independent_scale", "basis": "Ø20,00 boru bandı",
                               "basis_value": 20.0, "scale_px_per_mm": 17.7}},
        ],
    }


def test_mutual_corroboration_is_rejected() -> None:
    """§32: A dayanağı B, B dayanağı A → iki claim de reddedilir (mutual circularity)."""
    page = _page("frozen-exercise-13")
    problems = tool.validate_spec(page, _two_claim_spec())
    graph = [problem for problem in problems if "döngüsel kanıt (grafik)" in problem]
    owners = [problem.split(":", 1)[0] for problem in graph]
    assert "frozen-exercise-13/mutual-a" in owners, graph
    assert "frozen-exercise-13/mutual-b" in owners, graph
    assert any("mutual-b = 22" in problem for problem in graph), graph
    assert any("mutual-a = 20" in problem for problem in graph), graph


def test_corroboration_claim_cannot_be_the_only_root() -> None:
    """§32: değerlendirilen Ø/R claim'i tek kök olamaz — B'nin bağımsız kökü olmasa da A→B reddedilir."""
    page = _page("frozen-exercise-13")
    spec = _two_claim_spec()
    spec["claims"][1]["corroboration"] = {"kind": "none"}
    problems = tool.validate_spec(page, spec)
    graph = [problem for problem in problems if "döngüsel kanıt (grafik)" in problem]
    assert len(graph) == 1, problems
    assert graph[0].startswith("frozen-exercise-13/mutual-a:")
    assert "mutual-b = 22" in graph[0]


def test_linear_dimension_basis_is_accepted_by_graph_rule() -> None:
    """§32: 10,00 mm doğrusal datum (claim seti dışı) kökü kabul edilir — iki claim aynı köke dayanabilir."""
    page = _page("frozen-exercise-13")
    spec = _two_claim_spec()
    for claim in spec["claims"]:
        claim["corroboration"] = {
            "kind": "independent_scale",
            "basis": "10,00 mm doğrusal ölçü (kolonlar arası boy; ≈177 px) → ≈17,7 px/mm",
            "basis_value": 10.0, "scale_px_per_mm": 17.7,
        }
    assert tool.validate_spec(page, spec) == []


def test_tracked_exercise_17_corroboration_roots_outside_claims() -> None:
    """PLAN-9 §5: ex17'nin üç Ø claim'i karşı çapa değil bağımsız doğrusal datuma dayanır."""
    page = _page("frozen-exercise-17")
    spec = tool.load_spec("frozen-exercise-17")
    assert spec is not None
    assert len(spec["claims"]) == 3
    sizes = [(claim["claim_id"], float(claim["size"])) for claim in spec["claims"]]
    for claim in spec["claims"]:
        corroboration = claim.get("corroboration") or {}
        assert corroboration.get("kind") == "independent_scale", claim["claim_id"]
        basis = float(corroboration["basis_value"])
        assert "doğrusal" in str(corroboration.get("basis")), claim["claim_id"]
        for other_id, other_size in sizes:
            assert abs(basis - other_size) > 1e-9, \
                f"{claim['claim_id']}: dayanak ({basis}) {other_id} değerine çözülüyor"
    problems = tool.validate_spec(page, spec, tool._frame_px("frozen-exercise-17"))
    assert problems == [], problems


# ------------------------------------------------- §15 kararlı gold kimliği (PLAN-9 §14–§15)


def test_gold_content_identity_is_stable_across_rebuilds() -> None:
    """§32: aynı içerikle tekrar üretim → aynı kimlik (ve created_at'sız tam bayt kararlılığı)."""
    first = tool.build_manifest()
    second = tool.build_manifest()
    assert first["gold_content_identity"] == second["gold_content_identity"]
    assert first == second  # zaman damgası yok: aynı içerik → aynı manifest (§14)


def test_gold_content_identity_ignores_metadata() -> None:
    entries = [dict(entry) for entry in tool.build_manifest()["pages"]]
    baseline = tool.gold_content_identity(entries)
    assert baseline == tool.gold_content_identity(list(reversed(entries)))  # sayfa sırası kanonik
    enriched = [dict(entry, created_at="2026-01-01T00:00:00+00:00", written_at="dün",
                     local_path="/Users/x/out") for entry in entries]
    assert tool.gold_content_identity(enriched) == baseline  # üstveri kimliğe girmez (§15)
    mutated = [dict(entries[0], reference_sha256="0" * 64), *entries[1:]]
    assert tool.gold_content_identity(mutated) != baseline   # gerçek değişince kimlik değişir


def test_stored_manifest_matches_a_fresh_build() -> None:
    """İzlenen manifest, taze üretimle bayt bayt aynı olmalı (§14 — `--write` sonrası commit)."""
    stored_text = tool.MANIFEST.read_text(encoding="utf-8")
    fresh = tool.build_manifest()
    assert stored_text == json.dumps(fresh, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------- §16–§17 atomik dondurma (PLAN-9 §31/4)


def _freeze_fixture(tmp_path: Path, monkeypatch) -> Path:
    """Tek gerçek sayfayla (ex17) temiz bir dondurma senaryosu kurar; lab köküne yazmaz."""
    page = _page("frozen-exercise-17")
    monkeypatch.setattr(tool, "pages", lambda: [page])
    document = tool.build_manifest()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def test_freeze_runs_regeneration_proof(tmp_path: Path, monkeypatch) -> None:
    """§17: freeze tek başına TÜM sayfaların yeniden üretim kanıtını koşar ve kaydı yazar."""
    manifest_path = _freeze_fixture(tmp_path, monkeypatch)
    outcome = tool.freeze(manifest_path=manifest_path)
    assert outcome["ok"], outcome["problems"]
    assert outcome["regenerated"] == 1
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert outcome["identity"] == stored["gold_content_identity"]
    artifact = json.loads((tmp_path / "FREEZE.json").read_text(encoding="utf-8"))
    assert artifact["schema"] == tool.FREEZE_SCHEMA
    assert artifact["gold_content_identity"] == stored["gold_content_identity"]
    assert [row["page_id"] for row in artifact["pages"]] == ["frozen-exercise-17"]


def test_freeze_fails_when_regeneration_diverges(tmp_path: Path, monkeypatch) -> None:
    """§16: saklanan referans geçerli olsa bile mevcut üretim sapıyorsa kapı kapanır."""
    manifest_path = _freeze_fixture(tmp_path, monkeypatch)

    def diverging(page_id: str) -> dict:
        result = tool.regenerate(page_id)
        result["reference"] = dict(result["reference"], notes=["sapma"])
        return result

    outcome = tool.freeze(manifest_path=manifest_path, regenerate_fn=diverging)
    assert not outcome["ok"]
    assert any("yeniden üretim manifestten sapıyor" in problem for problem in outcome["problems"])
    assert not (tmp_path / "FREEZE.json").exists()  # başarısız dondurma kayıt yazmaz


def test_freeze_fails_without_identity(tmp_path: Path, monkeypatch) -> None:
    page = _page("frozen-exercise-17")
    monkeypatch.setattr(tool, "pages", lambda: [page])
    document = tool.build_manifest()
    document.pop("gold_content_identity")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    outcome = tool.freeze(manifest_path=manifest_path, regenerate_fn=lambda page_id: {
        "reference": json.loads((tool.gold_dir() / f"{page_id}.json").read_text(encoding="utf-8"))})
    assert not outcome["ok"]
    assert any("gold_content_identity" in problem for problem in outcome["problems"])
    assert not (tmp_path / "FREEZE.json").exists()


def test_freeze_requires_full_coverage(tmp_path: Path, monkeypatch) -> None:
    """İzlenen spec'i olmayan sayfa varken dondurma kapalı kalır (PLAN-8 §13)."""
    ex17, enclosure = _page("frozen-exercise-17"), _page("frozen-enclosure")
    monkeypatch.setattr(tool, "pages", lambda: [ex17, enclosure])
    document = tool.build_manifest()
    document["pages"] = [row for row in document["pages"]
                         if row["page_id"] == "frozen-exercise-17"]
    document["gold_content_identity"] = tool.gold_content_identity(document["pages"])
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    outcome = tool.freeze(manifest_path=manifest_path)
    assert not outcome["ok"]
    assert any("izlenen spec yok" in problem for problem in outcome["problems"])
    assert not (tmp_path / "FREEZE.json").exists()
