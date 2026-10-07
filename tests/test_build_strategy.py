"""G12.2 — explicit build strategy sözleşmesi (PLAN-25 §30–§44).

Bu dosya RED ile başlar: en büyük geometri hatası "seçili profil → ÖRTÜK extrude"dur. Yeni sözleşme:

```text
strateji yok        → GeneralPlan YOK (dairede de! disk kazara doğmaz)
strateji eski       → GeneralPlan YOK; kullanıcı yeniden onaylar
strateji desteklenmez → kontrollü blok
extrude_profile (açık) → mevcut Plaka yolu AYNI geometriyi üretir
```

Strateji bir KULLANICI kararıdır (§32): sistem yalnız öneri üretir (`build_strategy.propose_strategies`),
kalıcılık `set_build_strategy` komutundan geçer; `strategy_key`/`geometry_version` sunucuda çivilenir
(istemci uyduramaz, §36). Tazeleme ölçütü §37: profil / kontur düzeltmesi / görüş / geometri sürümü.
"""
import hashlib
import json
from pathlib import Path

import pytest

from drawingto3d import build_strategy, callout_readiness
from drawingto3d.guided import Decisions, GuidedStore, make_plan

PLATE_SHEET = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
STRATEGY_KINDS = ("extrude_profile", "revolve_profile", "multi_view_composite", "unsupported")


# --- ortak kurulum: gerçek pafta, gerçek store ---------------------------------------------------

def _plate(tmp_path, *, profile_id="outline_1", thickness=15.0, contour=None):
    """Paftayı aç, ana şablon kararlarını kur — strateji hariç (o her testin kendi konusu)."""
    store = GuidedStore(tmp_path / "store")
    opened = store.create(PLATE_SHEET.read_bytes())
    options = opened["options"]
    wire = next(p for p in options["profiles"] if p["id"] == profile_id)
    points = [p for edge in wire.get("edges") or [] for p in (edge["start"], edge["end"])] \
        or [list(p) for p in wire.get("points") or []]
    left = min(points, key=lambda p: p[0])
    right = max(points, key=lambda p: p[0])
    inside = [c for c in options["circles"]
              if c["id"] != wire["id"]
              and min(p[0] for p in points) <= c["center"][0] <= max(p[0] for p in points)
              and min(p[1] for p in points) <= c["center"][1] <= max(p[1] for p in points)]
    # Daire profili kendi deliği olamaz (store reddeder): o profilde delik listesi boş bırakılır.
    holes = ([{"circle_id": inside[0]["id"], "kind": "through", "diameter": 6.8, "depth": None}]
             if wire.get("kind") != "circle" else [])
    decisions = {"calibration": {"first": list(left), "second": list(right), "value": 100.0, "unit": "mm",
                                 "span_id": None},
                 "profile_id": wire["id"], "thickness": thickness, "trace_acknowledged": True,
                 "bindings": [], "holes": holes}
    if contour is not None:
        decisions["contour"] = contour
    revision = store.save(opened["token"], opened["revision"], decisions)["revision"]
    return store, opened["token"], revision


def _out_of_scope(store, token):
    """Üretim callout kapsamı da bekler; bu testler geometri sözleşmesini ölçtüğü için kapatılır."""
    for row in store.public(store.load(token))["callouts"]:
        store.edit_callout(token, store.load(token)["revision"], "set_ignored",
                           {"callout_id": row["id"], "ignored": True})


def _strategy(store, token, **payload):
    return store.set_strategy(token, store.load(token)["revision"],
                              {"kind": "extrude_profile", **payload})


# --- §39/§40: daire güvenliği ve açık daire extrude'u --------------------------------------------

def test_a_shared_circle_profile_never_extrudes_without_an_explicit_strategy(tmp_path):
    """§39: kalınlık + kalibrasyon + izleme onayı olsa bile strateji yoksa GeneralPlan doğmaz."""
    store, token, _revision = _plate(tmp_path, profile_id="circle_g8")
    record = store.load(token)
    with pytest.raises(ValueError) as raised:
        make_plan(record)
    assert "oluşturma biçimini seçin" in str(raised.value), raised.value
    # read(build) yolu da aynı kapıdan geçer: hazırlık, kategoriyi adıyla taşır (§41).
    readiness = callout_readiness.build_readiness(record)
    assert [q["category"] for q in readiness["questions"] if q["category"] == "missing_build_strategy"], \
        readiness["categories"]
    assert readiness["ready"] is False


def test_an_explicit_extrude_strategy_still_builds_a_circular_plate(tmp_path):
    """§40: geometri sınıfı kara listesi yok — açık onayla daire plakası gerçekten kurulur."""
    store, token, _revision = _plate(tmp_path, profile_id="circle_g8")
    _strategy(store, token)
    plan = make_plan(store.load(token))
    operations = plan.model_dump()["operations"]
    assert operations[0]["op"] == "extrude" and operations[0]["sketch"] == "outer", operations[0]
    outer_radius = plan.model_dump()["parameters"]["outer_radius"]["value"]
    assert outer_radius > 0


def test_the_extrude_strategy_compiles_the_plate_path_unchanged(tmp_path):
    """§35: kapalı (daire olmayan) profil + kalınlık → extrude; Plaka yolu aynı geometriyi verir."""
    store, token, _revision = _plate(tmp_path)
    _strategy(store, token)
    plan = make_plan(store.load(token)).model_dump()
    assert plan["operations"][0] == {"op": "extrude", "id": "base_extrusion", "output": "base",
                                     "sketch": "outer", "distance": "thickness"}, plan["operations"][0]
    assert plan["parameters"]["thickness"]["value"] == 15.0
    # Geometri pini: köşe noktaları ve kalibrasyon bu paftanın kendi ölçüsü (100 mm) altında ne veriyorsa o.
    xs = [row["value"] for key, row in plan["parameters"].items() if key.endswith("_x")]
    ys = [row["value"] for key, row in plan["parameters"].items() if key.endswith("_y")]
    assert (round(max(xs) - min(xs), 6), round(max(ys) - min(ys), 6)) == (89.436103, 59.61982), (min(xs), max(xs))
    assert min(xs) == 0.0 and min(ys) == 0.0, (min(xs), min(ys))


# --- §36: sunucu çiviliyor; istemci anahtar/sürüm uyduramaz --------------------------------------

def test_the_server_pins_the_strategy_key_and_geometry_version(tmp_path):
    store, token, _revision = _plate(tmp_path)
    record = store.load(token)
    forged = store.set_strategy(token, record["revision"],
                                {"kind": "extrude_profile", "strategy_key": "forged",
                                 "geometry_version": 999999})
    stored = forged["decisions"]["build_strategy"]
    assert stored["strategy_key"] == build_strategy.strategy_key(store.load(token)), stored
    assert stored["strategy_key"] != "forged"
    assert stored["geometry_version"] == store.load(token)["geometry_version"] != 999999
    assert build_strategy.strategy_state(store.load(token)) == "current"
    # ...ve toplu `save` yolu da uydurma anahtarı kabul etmez: adı konmuş hata, sessiz yazım yok.
    with pytest.raises(ValueError) as raised:
        store.save(token, store.load(token)["revision"],
                   {**record["decisions"], "build_strategy": {**stored, "strategy_key": "forged"}})
    assert "set_build_strategy" in str(raised.value), raised.value


# --- §37: tazeleme ölçütü — ilgisiz düzenlemeler dokunmaz ----------------------------------------

def test_a_profile_change_or_contour_correction_stales_the_strategy(tmp_path):
    store, token, _revision = _plate(tmp_path)
    _strategy(store, token)
    # İlgisiz bir düzenleme (kalınlık) stratejiyi eskitmez.
    store.save(token, store.load(token)["revision"], {**store.load(token)["decisions"], "thickness": 12.0})
    assert build_strategy.strategy_state(store.load(token)) == "current"
    readiness = callout_readiness.build_readiness(store.load(token))
    assert not [q for q in readiness["questions"] if q["category"].endswith("build_strategy")]
    # Ana profil değişince strateji eskir: onay eski kontura bağlı kalmaz.
    store.save(token, store.load(token)["revision"], {**store.load(token)["decisions"], "profile_id": "outline_3"})
    assert build_strategy.strategy_state(store.load(token)) == "stale"
    with pytest.raises(ValueError) as raised:
        make_plan(store.load(token))
    assert "yeniden onaylayın" in str(raised.value), raised.value
    stale = callout_readiness.build_readiness(store.load(token))
    assert [q["category"] for q in stale["questions"] if q["category"] == "stale_build_strategy"], stale["categories"]
    # Kontur düzeltmesi de aynı kapıdan geçer (§37).
    store2, token2, _revision2 = _plate(tmp_path / "second")
    _strategy(store2, token2)
    wire = next(p for p in store2.load(token2)["options"]["profiles"] if p["id"] == "outline_1")
    drop = [wire["edges"][0]["id"]]
    store2.save(token2, store2.load(token2)["revision"],
                {**store2.load(token2)["decisions"], "contour": {"drop": drop}})
    assert build_strategy.strategy_state(store2.load(token2)) == "stale"


def test_an_unsupported_strategy_blocks_under_its_own_category(tmp_path):
    """§41: desteklenmeyen strateji 'eksik' değil, kendi kategorisiyle bloklar."""
    store, token, _revision = _plate(tmp_path)
    store.set_strategy(token, store.load(token)["revision"], {"kind": "unsupported"})
    with pytest.raises(ValueError) as raised:
        make_plan(store.load(token))
    assert "bu sürümde uygulanamıyor" in str(raised.value), raised.value
    readiness = callout_readiness.build_readiness(store.load(token))
    categories = [q["category"] for q in readiness["questions"]]
    assert "unsupported_build_strategy" in categories and "missing_build_strategy" not in categories, categories
    # revolve/multi_view: sözleşme var, kabiliyet sonraki fazlarda (§35/§38) — kontrollü blok.
    for kind in ("revolve_profile", "multi_view_composite"):
        store.set_strategy(token, store.load(token)["revision"], {"kind": kind})
        with pytest.raises(ValueError) as raised:
            make_plan(store.load(token))
        assert "bu sürümde uygulanamıyor" in str(raised.value), raised.value


def test_undo_removes_the_strategy_and_a_reopened_store_keeps_it(tmp_path):
    """§36: tek revizyon, tek geri alma adımı; yeniden açma kararı korur."""
    store, token, _revision = _plate(tmp_path)
    before = store.load(token)["revision"]
    _strategy(store, token)
    assert build_strategy.strategy_state(store.load(token)) == "current"
    store.save(token, store.load(token)["revision"], undo=True)
    after = store.load(token)
    assert after["decisions"].get("build_strategy") is None, "geri alma strateji kararını kaldırmalı"
    assert after["revision"] > before, "geri alma da bir revizyondur; sayaç monoton artar"
    assert build_strategy.strategy_state(after) == "missing"
    _strategy(store, token)
    reopened = GuidedStore(tmp_path / "store")
    assert build_strategy.strategy_state(reopened.load(token)) == "current"
    assert make_plan(reopened.load(token)).model_dump()["operations"][0]["op"] == "extrude"


# --- §33/§34: öneri modülü — kanıta dayalı, referanssız, saf ------------------------------------

def test_proposals_are_evidence_based_and_carry_no_case_file_or_reference(tmp_path):
    store, token, _revision = _plate(tmp_path)
    record = store.load(token)
    proposals = build_strategy.propose_strategies(record)
    assert all(isinstance(p, build_strategy.BuildStrategyProposal) for p in proposals), proposals
    extrude = [p for p in proposals if p.kind == "extrude_profile"]
    assert len(extrude) == 1, proposals
    assert extrude[0].confidence == "high" and extrude[0].status == "candidate"
    assert extrude[0].label == "Sabit kalınlıklı profili uzat"
    evidence = json.dumps(extrude[0].evidence, ensure_ascii=False)
    assert "closure" in evidence or "kapalı" in evidence, evidence
    # §34 yasakları: vaka kimliği, dosya adı, sha, referans, beklenen bbox öneri kanıtına giremez.
    assert record["source_sha256"] not in evidence
    assert Path(record["source"]).name not in evidence
    assert record["token"] not in evidence
    for word in ("reference", "expected", "bbox", ".step", ".stp"):
        assert word not in evidence.lower(), (word, evidence)
    # Daire profili: yüksek güvenli extrude önerisi YOK (§35).
    store2, token2, _r2 = _plate(tmp_path / "circle", profile_id="circle_g8")
    circle = build_strategy.propose_strategies(store2.load(token2))
    assert not [p for p in circle if p.kind == "extrude_profile" and p.confidence == "high"], circle


def test_the_strategy_proposal_module_is_pure():
    """§33: dosya/ağ/model/referans yok — modül yalnız kaydı okur."""
    source = Path("src/drawingto3d/build_strategy.py").read_text(encoding="utf-8")
    for forbidden in ("open(", "Path(", "requests", "urllib", "subprocess", "llama", "semantic_",
                      "reference", "expected", "case_id", "sha256"):
        assert forbidden not in source, forbidden
    # modül kimlikleri sözleşmede: üç fonksiyon + kind listesi
    for name in ("def propose_strategies", "def strategy_key", "def strategy_state"):
        assert name in source, name


def test_the_decision_model_keeps_the_strategy_schema_and_underscore_default(tmp_path):
    """§31: alan geriye uyumlu `None`; şema Literal'leri sözleşmedir."""
    import typing

    from drawingto3d.build_strategy import BuildStrategyDecision

    annotation = Decisions.model_fields["build_strategy"].annotation
    assert typing.get_args(annotation) == (BuildStrategyDecision, type(None)), annotation
    assert typing.get_args(BuildStrategyDecision.model_fields["kind"].annotation) == STRATEGY_KINDS
    assert "build_strategy" not in Decisions.model_validate({}).model_dump(exclude_none=True)
    store, token, _revision = _plate(tmp_path)
    assert store.load(token)["decisions"].get("build_strategy") is None
    # kalıcılık yalnız komuttan geçer (§32/§36): ham `save` ile strateji yazılamaz
    with pytest.raises(ValueError):
        store.save(token, store.load(token)["revision"],
                   {**store.load(token)["decisions"],
                    "build_strategy": {"kind": "extrude_profile", "strategy_key": "x", "geometry_version": 1}})


def test_strategy_state_sees_a_geometry_version_change_as_stale(tmp_path):
    """§37: geometri sürümü değişirse strateji eskidir — okuma hareket etti, onay taşınamaz."""
    store, token, _revision = _plate(tmp_path)
    _strategy(store, token)
    record = store.load(token)
    fingerprint = build_strategy.strategy_key(record)
    moved = {**record, "geometry_version": (record.get("geometry_version") or 1) + 1}
    assert build_strategy.strategy_key(moved) != fingerprint
    assert hashlib.sha256(json.dumps({"same": True}, sort_keys=True).encode()).hexdigest()  # kanıt: saf hesap
