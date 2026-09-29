"""PLAN 8.6: the view is the user's own confirmation, and it is asked only where the page is not the sheet.

The product proposes (where the sheet's border is, which way its axes go); the decision records what the
user approved and against which geometry version. These tests drive the same functions the flow runs:
`drawing_options` for the product, `questions` for the ask, `validate_decisions` for the gate, and the
store for what actually lands in the record.
"""
from pathlib import Path

import pytest

from drawingto3d.guided import Decisions, GuidedStore, drawing_options, questions, validate_decisions
from drawingto3d.observe import Frame, Observations, Primitive, SourceRef

PLATE = Path("examples/pdf with steps/5/Plate With A Pocket Drawing.PDF")


def _line(pid, start, end):
    return Primitive(id=pid, path_id="synthetic", kind="line", start=list(start), end=list(end),
                     method="two-point")


def _options(*, border=True, rotation=0, width=1000, height=700):
    primitives = [
        _line("g4", (100, 100), (300, 100)), _line("g5", (300, 100), (300, 200)),
        _line("g6", (300, 200), (100, 200)), _line("g7", (100, 200), (100, 100)),
    ]
    if border:
        primitives = [
            _line("g0", (10, 10), (990, 10)), _line("g1", (990, 10), (990, 690)),
            _line("g2", (990, 690), (10, 690)), _line("g3", (10, 690), (10, 10)),
        ] + primitives
    observations = Observations(source=SourceRef(ref="synthetic.pdf", sha256="0" * 64, rotation=rotation),
                                frame=Frame(width=width, height=height), text_placement="as-is",
                                primitives=primitives)
    return drawing_options(observations)


def _view_questions(questions_list):
    return [row for row in questions_list if "Görüş" in row or "görüş" in row]


def test_an_upright_sheet_with_a_found_frame_is_not_asked_about():
    options = _options()

    assert options["sheet_frame"]["found"] is True and options["sheet_frame"]["aligned"] is True
    assert _view_questions(questions(Decisions(), None, options)) == []


def test_a_sheet_whose_frame_is_missing_is_asked_with_the_proposal():
    options = _options(border=False)
    asked = _view_questions(questions(Decisions(), None, options))

    assert len(asked) == 1, asked
    assert "öneri: X sağ, Y yukarı" in asked[0], asked[0]
    assert "kapalı çerçeve yolu bulunamadı" in asked[0], asked[0]


def test_a_rotated_source_is_asked_and_the_proposal_follows_the_rotation():
    options = _options(rotation=90)
    asked = _view_questions(questions(Decisions(), None, options))

    assert options["sheet_frame"]["rotation"] == 90
    assert len(asked) == 1 and "öneri: X aşağı, Y sağ" in asked[0], asked


def test_confirming_the_view_stops_the_question_and_survives_a_reopen(tmp_path):
    store = GuidedStore(tmp_path / "store")
    token = store.create(PLATE.read_bytes())["token"]
    state = store.load(token)
    product = state["options"]["sheet_frame"]
    assert product["found"] is True
    approved = {"x_page": product["axes"][0]["page"], "y_page": product["axes"][1]["page"],
                "frame_rect": product["rect"], "source": "sheet_frame",
                "geometry_version": state["geometry_version"]}
    saved = store.save(token, 0, {"view": approved, "trace_acknowledged": False})

    assert saved["decisions"]["view"]["x_page"] == [1.0, 0.0]
    assert saved["decisions"]["view"]["geometry_version"] == state["geometry_version"]
    reopened = store.load(token)
    assert reopened["decisions"]["view"]["frame_rect"] == product["rect"]
    # The sheet's own frame is published next to the decisions, so the interface can show what was approved.
    assert reopened["options"]["sheet_frame"]["rect"] == product["rect"]


def test_a_confirmed_view_is_not_asked_again_even_where_the_frame_is_odd():
    options = _options(border=False)
    product = options["sheet_frame"]
    confirmed = Decisions.model_validate({"view": {"x_page": product["axes"][0]["page"],
                                                  "y_page": product["axes"][1]["page"],
                                                  "source": "page_axes"}})

    assert _view_questions(questions(confirmed, None, options)) == []


def test_a_reading_that_moved_asks_for_the_view_again():
    options = _options()
    product = options["sheet_frame"]
    confirmed = Decisions.model_validate({"view": {"x_page": [0.0, 1.0], "y_page": [1.0, 0.0],
                                                   "frame_rect": product["rect"], "source": "sheet_frame"}})
    asked = _view_questions(questions(confirmed, None, options))

    assert len(asked) == 1 and "uyuşmuyor" in asked[0], asked


@pytest.mark.parametrize("view,message", [
    ({"x_page": [2.0, 0.0], "y_page": [0.0, -1.0]}, "birim vektör"),
    ({"x_page": [1.0, 0.0], "y_page": [0.0, 0.0]}, "birim vektör"),
    # A unit vector that is *not* perpendicular to the other axis: length is fine, the angle is not.
    ({"x_page": [1.0, 0.0], "y_page": [0.6, -0.8]}, "dik olmalı"),
    ({"x_page": [1.0, 0.0], "y_page": [0.0, -1.0], "frame_rect": [-5.0, 0.0, 900.0, 600.0]},
     "çizim dışında"),
])
def test_a_malformed_view_is_refused(view, message):
    options = _options()
    decisions = Decisions.model_validate({"view": view})

    with pytest.raises(ValueError, match=message):
        validate_decisions(options, decisions)


def test_a_view_cannot_carry_fields_the_flow_does_not_run_on():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Decisions.model_validate({"view": {"x_page": [1.0, 0.0], "y_page": [0.0, -1.0],
                                           "rotation": 90.0}})


def test_the_build_stops_at_the_ask_when_the_view_cannot_be_derived(tmp_path):
    """PLAN 8.6's own line: page x is not read off part x. No border and no confirmation means no build.

    `view_transform` is the guard the build reads, and `questions()` is what the user meets first — the two
    agree by construction (both call the same product), so the guard is checked directly here and the
    message the user sees is the ask.
    """
    from drawingto3d.guided import make_plan, view_transform

    record = _record(tmp_path, border=False, decisions={})
    options = record["options"]
    assert view_transform(Decisions(), options) is None
    with pytest.raises(ValueError, match="Görüş eksenini ve çerçeveyi onaylayın"):
        make_plan(record)


def test_view_transform_follows_the_confirmation_first_and_the_product_second():
    from drawingto3d.guided import is_page_identity, view_transform

    obvious = _options()
    assert view_transform(Decisions(), obvious)["x"] == [1.0, 0.0]
    assert is_page_identity(view_transform(Decisions(), obvious)) is True
    confirmed = Decisions.model_validate({"view": {"x_page": [0.0, 1.0], "y_page": [1.0, 0.0],
                                                   "source": "sheet_frame"}})
    axes = view_transform(confirmed, obvious)
    assert axes["x"] == [0.0, 1.0] and axes["y"] == [1.0, 0.0]
    assert is_page_identity(axes) is False
    assert view_transform(Decisions(), _options(border=False)) is None



def test_an_upright_sheet_builds_with_the_page_axes_as_its_own(tmp_path):
    """The plate's own sheet is upright, so the view neither blocks nor changes the plan."""
    from drawingto3d.guided import make_plan
    from drawingto3d.observe import observe

    store = GuidedStore(tmp_path / "store")
    token = store.create(PLATE.read_bytes())["token"]
    state = store.load(token)
    product = state["options"]["sheet_frame"]
    assert product["found"] and product["aligned"] and product["rotation"] == 0
    record = dict(state)
    record["token"] = token
    record["decisions"] = dict(record["decisions"], trace_acknowledged=True,
                               thickness=15.0, profile_id=None, calibration=None, view=None)
    # No profile and no calibration yet: `questions` stops first — this checks the view is not what stops it.
    with pytest.raises(ValueError) as failure:
        make_plan(record)
    assert "görüş" not in str(failure.value), failure.value


def _record(tmp_path, *, border, decisions, rotation=0):
    """A synthetic session record whose sheet either has its own border or does not (PLAN 8.6's ask)."""
    from drawingto3d import guided
    from drawingto3d.guided import _atomic

    primitives = [_line("g0", (20, 20), (120, 20)), _line("g1", (120, 20), (120, 80)),
                  _line("g2", (120, 80), (20, 80)), _line("g3", (20, 80), (20, 20))]
    if border:
        for i, (start, end) in enumerate((((10, 10), (290, 10)), ((290, 10), (290, 190)),
                                          ((290, 190), (10, 190)), ((10, 190), (10, 10)))):
            primitives.append(_line(f"b{i}", start, end))
    source = tmp_path / "source.pdf"
    source.write_bytes(b"fixture-source-hash")
    observations = Observations(
        source=SourceRef(ref=str(source), sha256=__import__("hashlib").sha256(source.read_bytes()).hexdigest(),
                         rotation=rotation),
        frame=Frame(width=300, height=200), text_placement="as-is", primitives=primitives)
    options = drawing_options(observations)
    wire = next(p["id"] for p in options["profiles"] if p["kind"] == "wire")
    folder = tmp_path / "store" / ("a" * 32)
    folder.mkdir(parents=True, exist_ok=True)
    record = {"version": 1, "geometry_version": guided.GEOMETRY_VERSION, "token": "a" * 32, "revision": 0,
              "source": str(source), "source_sha256": observations.source.sha256, "options": options,
              "decisions": dict({"calibration": {"first": [20, 20], "second": [120, 20], "value": 50,
                                                 "unit": "mm"},
                                 "profile_id": wire, "thickness": 10.0, "trace_acknowledged": True},
                                **decisions),
              "history": [], "build": None}
    _atomic(folder / "session.json", record)
    return record
