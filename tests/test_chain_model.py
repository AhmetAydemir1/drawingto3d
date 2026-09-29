"""The product path: a real drawing, read by the chain, planned by a stand-in for the model.

No model is called here — the stand-in hands back the plan the rules-based reading already produces
for this sheet. That keeps these tests about what `model-plan` adds: the evidence comes from the
drawing's own measurements (every printed number with what it was measured against, and the geometry
in millimetres), the answer goes through the same validation a model's answer would, and every file
the run produced is written before the exit code speaks. A sheet the reading cannot put in
millimetres never reaches a planner at all.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from drawingto3d.cli import plan_from_drawing
from drawingto3d.planner import chain_evidence
from drawingto3d.proposal import propose_general, read_sheet

PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")
RASTER = Path("examples/504715c44a0f1b2bbb386bb7c387a8db.jpg")


class StandIn:
    """A model stand-in: one canned reply, and the prompts it was asked, so "never asked" is checkable."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.asks: list[str] = []
        self.model = "stand-in"

    def settings_record(self) -> dict:
        return {"model": self.model, "num_ctx": 16384, "num_predict": 4096, "temperature": 0}

    def complete(self, prompt, image_png=None, num_predict=None, response_format=None, stats=None) -> str:
        self.asks.append(prompt)
        if stats is not None:
            stats.update({"done_reason": "stop"})
        return self.reply

    def unload(self) -> None:
        return None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def reading():
    return read_sheet(PLATE)


@pytest.fixture(scope="module")
def evidence(reading):
    return chain_evidence(reading)


def test_read_sheet_preserves_original_printed_value_and_unit(monkeypatch):
    from drawingto3d import proposal
    meanings = proposal.meaning_page(PLATE)
    meanings.spans[0].printed_value = 2.345
    meanings.spans[0].printed_mm = 59.56
    meanings.spans[0].unit = "in"
    monkeypatch.setattr(proposal, "meaning_page", lambda path: meanings)
    reading = read_sheet(PLATE)
    printed = next(row for row in reading.printed if row["span_id"] == meanings.spans[0].span_id)
    assert printed["value"] == 2.345 and printed["unit"] == "in"


def test_the_plate_reads_into_millimetres(reading):
    assert reading.refusals == []
    assert reading.sheet_px_per_mm == pytest.approx(7.82, abs=0.05)
    assert reading.outline_mm["rounded_rectangle"] is True
    assert reading.outline_mm["width_mm"] == pytest.approx(120.87, abs=0.2)
    assert reading.outline_mm["height_mm"] == pytest.approx(80.56, abs=0.2)
    assert reading.outline_mm["corner_radius_mm"] == pytest.approx(10.05, abs=0.2)
    diameters = sorted(circle["diameter_mm"] for circle in reading.circles_mm)
    assert diameters[:4] == pytest.approx([6.84] * 4, abs=0.1)
    assert diameters[-1] == pytest.approx(50.36, abs=0.2)
    assert reading.components["frame_loops"] == 1


def test_every_printed_number_says_what_it_measures(evidence):
    assert len(evidence["printed"]) == 7
    assert len(evidence["claims"]) == 7
    by_id = {claim["span_id"]: claim for claim in evidence["claims"]}
    assert by_id["pdf-0"]["printed_mm"] == pytest.approx(100.0)
    assert [anchor["geometry_id"] for anchor in by_id["pdf-0"]["anchors"]] == ["g9", "g11"]
    assert by_id["pdf-0"]["anchors"][0]["point_mm"] == pytest.approx([-50.35, -30.21], abs=0.2)
    assert by_id["pdf-3"]["form"] == "diameter"
    assert sorted(by_id["pdf-3"]["matched_geometry"]) == ["g10", "g11", "g12", "g9"]
    assert by_id["pdf-3"]["count"] == 4
    assert evidence["geometry"]["circles"]
    assert evidence["sheet"]["scale_known"] is True


def test_the_evidence_carries_no_reference_part(evidence):
    blob = json.dumps(evidence, ensure_ascii=False)
    assert "STEP" not in blob
    assert "stp" not in blob.lower() and "step" not in blob.lower()
    assert "reference" not in blob
    assert "verified_by" not in blob


def test_the_product_path_writes_the_plan_a_model_would_have_to_earn(tmp_path):
    rules = propose_general(PLATE)
    assert rules.plan is not None, "kural planı yoksa stand-in'in cevabı da yok"
    stand_in = StandIn(rules.plan.model_dump_json())
    payload, reason = plan_from_drawing(PLATE, tmp_path, stand_in)

    assert reason is None
    assert stand_in.asks, "model sorulmadan plan yazılmamalı"
    assert "120" in stand_in.asks[0] and "STEP" not in stand_in.asks[0]
    assert json.loads((tmp_path / "evidence.json").read_text(encoding="utf-8"))["printed"]
    assert json.loads((tmp_path / "candidate.json").read_text(encoding="utf-8"))["status"] == "proposed"
    plan = json.loads((tmp_path / "plan.json").read_text(encoding="utf-8"))
    assert plan["source"]["sha256"] == _sha256(PLATE)
    assert payload["plan"].endswith("plan.json")


def test_a_sheet_the_reading_cannot_measure_never_reaches_a_planner(tmp_path):
    stand_in = StandIn("{}")
    payload, reason = plan_from_drawing(RASTER, tmp_path, stand_in)

    assert reason and "milimetreye" in reason
    assert stand_in.asks == []
    assert "candidate" not in payload
    assert not (tmp_path / "candidate.json").exists()
    assert read_sheet(RASTER).refusals


def test_a_bad_answer_is_recorded_and_not_turned_into_a_plan(tmp_path):
    reply = "elbette, plan şu: {\"version\": \"nope\"}"
    stand_in = StandIn(reply)
    payload, reason = plan_from_drawing(PLATE, tmp_path, stand_in)

    assert reason and "şemaya uyan plan vermedi" in reason
    assert not (tmp_path / "plan.json").exists()
    candidate = json.loads((tmp_path / "candidate.json").read_text(encoding="utf-8"))
    assert candidate["answer"] == reply
    assert candidate["errors"]
