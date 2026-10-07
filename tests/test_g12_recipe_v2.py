"""G12.1b — koşucu v2: reçete şeması + blanket yasağının yapısal kanıtı (PLAN-25 §22–§26).

Üç soru mekanik olarak yanıtlanır:

1. §23 şemasındaki reçete doğrulanır; blanket alanlar (`ignore_rest`, `bulk_remaining`,
   `ignore_all_unhandled`) hangi derinlikte olursa olsun reddedilir; her eylem `callout_id` +
   `action` + `reason` taşır; toplu karar kimlikleri açıkça listeler.
2. §26: reçete referans alanı ve katı model dosyası adı taşıyamaz.
3. §24: koşucu YALNIZ reçetedeki kimliklere istek yollar — "kalanları kapat" diye bir istek
   üretilemez; hazır değilse build yok ve bu kayıtta açıkça yazar.
"""
import hashlib
import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "eval/g12_runner"


def _load(name: str, path: pathlib.Path):
    sys.path.insert(0, str(RUNNER))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECIPE_V2 = _load("g12_recipe_v2", RUNNER / "recipe_v2.py")
G12_RUNNER = _load("g12_runner_v2", RUNNER / "g12_runner.py")

SHA = "a" * 64


def base_recipe(**overrides) -> dict:
    recipe = {
        "case_id": "plate-pocket-vector",
        "source_sha256": SHA,
        "operator_basis": "source_drawing_only",
        "callout_actions": [{"callout_id": "k1", "action": "not_model_input",
                             "reason": "başlık bloğu: çizim numarası"}],
        "profile_actions": [], "view_decisions": [], "strategy_decision": None,
        "dimension_bindings": [], "feature_links": [], "notes": ["kaynak çizimden"],
    }
    recipe.update(overrides)
    return recipe


# --- §23 şema -------------------------------------------------------------------------------

def test_the_g23_schema_validates_and_normalizes():
    recipe = RECIPE_V2.validate(base_recipe())
    assert recipe["operator_basis"] == "source_drawing_only"
    assert recipe["callout_actions"][0]["callout_id"] == "k1"
    assert recipe["notes"] == ["kaynak çizimden"]


def test_recipe_refuses_non_source_basis_and_bad_sha():
    for overrides, needle in (({"operator_basis": "reference"}, "source_drawing_only"),
                              ({"source_sha256": "zz"}, "source_sha256"),
                              ({"case_id": ""}, "case_id")):
        with pytest.raises(RECIPE_V2.RecipeError) as error:
            RECIPE_V2.validate(base_recipe(**overrides))
        assert needle in str(error.value), overrides


def test_unknown_top_level_field_is_refused():
    with pytest.raises(RECIPE_V2.RecipeError) as error:
        RECIPE_V2.validate(base_recipe(surprise=True))
    assert "bilinmeyen reçete alanı" in str(error.value)


# --- §24 blanket yasağı ---------------------------------------------------------------------

@pytest.mark.parametrize("field", ["ignore_rest", "bulk_remaining", "ignore_all_unhandled"])
def test_blanket_fields_are_refused_in_any_shape(field):
    for shape in (base_recipe(**{field: True}),
                  base_recipe(callout_actions=[{"action": field, "callout_ids": ["k1"]}]),
                  base_recipe(notes=[{field: ["k1", "k2"]}])):
        with pytest.raises(RECIPE_V2.RecipeError) as error:
            RECIPE_V2.validate(shape)
        assert "blanket" in str(error.value), shape


def test_every_action_row_is_explicit():
    cases = (
        ([{"action": "not_model_input", "reason": "x"}], "callout_id"),
        ([{"callout_id": "k1", "action": "not_model_input"}], "gerekçe"),
        ([{"callout_id": "k1", "action": "ignore", "reason": "x"}], "bilinmeyen eylem"),
        ([{"callout_id": "k1", "action": "redundant", "reason": "x"}], "duplicate_of"),
        ([{"callout_id": "k1", "action": "not_model_input", "reason": "x",
           "duplicate_of": "k2"}], "yalnız 'redundant'"),
    )
    for actions, needle in cases:
        with pytest.raises(RECIPE_V2.RecipeError) as error:
            RECIPE_V2.validate(base_recipe(callout_actions=actions))
        assert needle in str(error.value), actions


def test_bulk_allows_only_an_explicit_id_list():
    ok = RECIPE_V2.validate(base_recipe(callout_actions=[
        {"action": "bulk_not_model_input", "callout_ids": ["k1", "k2"], "reason": "başlık bloğu satırları"}]))
    assert ok["callout_actions"][0]["callout_ids"] == ["k1", "k2"]
    for bad, needle in (({"action": "bulk_not_model_input", "reason": "x"}, "kimlik listesi"),
                        ({"action": "bulk_not_model_input", "callout_ids": [], "reason": "x"}, "kimlik listesi"),
                        ({"action": "bulk_not_model_input", "callout_ids": ["k1", "k1"], "reason": "x"},
                         "yinelenen"),
                        ({"action": "bulk_not_model_input", "callout_ids": ["k1"], "callout_id": "k9",
                          "reason": "x"}, "bilinmeyen alan")):
        with pytest.raises(RECIPE_V2.RecipeError) as error:
            RECIPE_V2.validate(base_recipe(callout_actions=[bad]))
        assert needle in str(error.value), bad


def test_the_runner_never_invents_ids_for_the_remainder():
    """§24/§25: plandan gelen istekler TAM olarak reçetedeki kimliklerdir; 'kalan' hedefi yoktur."""
    recipe = RECIPE_V2.validate(base_recipe(callout_actions=[
        {"callout_id": "k2", "action": "redundant", "duplicate_of": "decision:calibration", "reason": "x"},
        {"action": "bulk_not_model_input", "callout_ids": ["k5"], "reason": "başlık satırı"}]))
    requests = RECIPE_V2.planned_actions(recipe)
    assert [row["http_action"] for row in requests] == ["set_disposition", "bulk_set_ignored"]
    ids = [row["payload"].get("callout_id") or row["payload"].get("callout_ids") for row in requests]
    assert ids == ["k2", ["k5"]]
    assert all("disposition" in row["payload"] or "callout_ids" in row["payload"] for row in requests)


# --- §26 referans sınırı --------------------------------------------------------------------

def test_recipe_refuses_reference_fields_and_model_file_names():
    for override in ({"reference_bbox": [1, 2, 3]}, {"reference_step_path": "x/y"},
                     {"callout_actions": [{"callout_id": "k1", "action": "not_model_input", "reason": "x",
                                           "reference_volume": 12}]},
                     {"callout_actions": [{"callout_id": "part.step", "action": "not_model_input",
                                           "reason": "x"}]}):
        recipe = base_recipe(**override)
        with pytest.raises(RECIPE_V2.RecipeError) as error:
            RECIPE_V2.validate(recipe)
        assert "referans" in str(error.value) or "katı model" in str(error.value), override
    # §26 listesinin tamamı modülde beyan edilmiş olmalı (statik şema sözleşmesi).
    for field in ("reference_bbox", "reference_volume", "reference_face_count", "reference_cylinders",
                  "expected_feature_count", "reference_step_path"):
        assert field in RECIPE_V2.REFERENCE_FIELDS, field


# --- koşucu davranışı (saplama taşıma) ------------------------------------------------------

class StubTransport:
    def __init__(self, *, state=None, ready=False, fail_at=None):
        self.calls = []
        self.state = state or {"token": "tok", "revision": 1,
                               "effective_callouts": [{"id": f"k{i}"} for i in range(1, 6)],
                               "callout_candidates": [{"id": f"k{i}"} for i in range(1, 6)],
                               "coverage": {"counts": {}}}
        self.ready = ready
        self.fail_at = fail_at

    def open(self, payload):
        self.calls.append(("open", len(payload)))
        return dict(self.state)

    def command(self, token, revision, action, payload):
        self.calls.append(("command", action, json.dumps(payload, sort_keys=True)))
        if self.fail_at is not None and len([c for c in self.calls if c[0] == "command"]) == self.fail_at:
            raise RuntimeError("callout yok: k9")
        self.state["revision"] = revision + 1
        return dict(self.state)

    def readiness(self, token):
        self.calls.append(("readiness",))
        return {"ready": self.ready, "questions": [{"category": "unsupported_build_relevant",
                                                    "callout_id": "k3"}],
                "coverage": {"counts": {"build_relevant_unsupported": 1}}}

    def build(self, token, revision):
        self.calls.append(("build", revision))
        return {"build_status": "complete", "step": "/guided-session/tok/part.step"}


def _source(tmp_path: pathlib.Path) -> pathlib.Path:
    path = tmp_path / "source.pdf"
    path.write_bytes(b"fixture-source")
    return path


def _recipe_for(source: pathlib.Path, actions, **overrides):
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    return RECIPE_V2.validate(base_recipe(source_sha256=digest, callout_actions=actions, **overrides))


def test_the_runner_applies_only_the_recipes_rows_and_reports_the_block(tmp_path):
    source = _source(tmp_path)
    recipe = _recipe_for(source, [{"callout_id": "k2", "action": "build_relevant_unsupported",
                                   "reason": "hedefi yok"}])
    transport = StubTransport(ready=False)
    record = G12_RUNNER.run_recipe(recipe, transport, source_path=source, out_dir=tmp_path / "run")
    commands = [call for call in transport.calls if call[0] == "command"]
    assert len(commands) == 1 and commands[0][1] == "set_disposition"
    assert json.loads(commands[0][2]) == {"callout_id": "k2", "disposition": "build_relevant_unsupported",
                                          "disposition_reason": "hedefi yok"}
    assert record["remaining_closed_automatically"] is False
    assert record["build_status"] == "skipped:not-ready"
    assert not [call for call in transport.calls if call[0] == "build"], "hazır değilken build denenmez"
    assert record["action_ids"] == ["k2"]
    # Kayıt dosyası koşu dizinine yazıldı (kanıt).
    written = json.loads((tmp_path / "run" / "g12-run.json").read_text(encoding="utf-8"))
    assert written["planned_requests"] == 1 and written["readiness_ready"] is False


def test_a_refused_action_stops_the_run_and_is_recorded(tmp_path):
    source = _source(tmp_path)
    recipe = _recipe_for(source, [{"callout_id": "k1", "action": "not_model_input", "reason": "x"},
                                  {"callout_id": "k9", "action": "not_model_input", "reason": "y"},
                                  {"callout_id": "k3", "action": "not_model_input", "reason": "z"}])
    transport = StubTransport(fail_at=2)
    record = G12_RUNNER.run_recipe(recipe, transport, source_path=source)
    commands = [call for call in transport.calls if call[0] == "command"]
    assert len(commands) == 2, "reddedilen eylemden sonra istek yok"
    assert [row["code"] for row in record["failures"]] == ["action-refused"]
    assert record["actions"][-1]["ok"] is False and "k9" in record["actions"][-1]["error"]


def test_a_source_hash_mismatch_stops_before_any_request(tmp_path):
    source = _source(tmp_path)
    recipe = RECIPE_V2.validate(base_recipe(source_sha256="b" * 64))
    transport = StubTransport()
    record = G12_RUNNER.run_recipe(recipe, transport, source_path=source)
    assert transport.calls == [], "sha uyuşmazsa oturum bile açılmaz"
    assert record["failures"][0]["code"] == "source-sha-mismatch"


def test_the_runner_builds_only_when_readiness_is_ready(tmp_path):
    source = _source(tmp_path)
    recipe = _recipe_for(source, [{"callout_id": "k1", "action": "not_model_input", "reason": "başlık"}])
    transport = StubTransport(ready=True)
    record = G12_RUNNER.run_recipe(recipe, transport, source_path=source)
    assert [call[0] for call in transport.calls] == ["open", "command", "readiness", "build"]
    assert record["build_status"] == "complete"
