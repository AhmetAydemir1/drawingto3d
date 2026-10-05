"""SEMREAD-001C — PLAN-12 §15 (P1): region contract v2.

Kapsam (PLAN-12 §15.3 / §49 kontrol listesi):

* `semread-candidates/2` + `semread-candidate-reader/2` sürüm bump'ı;
* region şeması `minimum: 0, maximum: 1` taşır ve `source.region`, `source.callout_region`,
  `target.region` **aynı** sözleşmeden gelir (kopya literal yok);
* ortak V/VE görev metni normalize koordinat kuralını açıkça öğretir (top-left/bottom-right,
  "Never return pixel coordinates", yalnız koordinat biçimi için örnek);
* piksel koordinatlı örnek şema/Pydantic tarafından **reddedilir**; normalize örnek kabul edilir;
* prompt'ta gold/sayfaya özel metin yok.

001D notu (§5 geçişi): wire sınırında semantik-içerik kuralı eklendi — yalnız `candidate_id` +
`source.region` taşıyan gövde artık `schema_semantic_empty` ile reddedilir. Bu dosyadaki kabul
testleri bu yüzden **tek semantic claim** taşıyan fixture kullanır; claimsiz reddin kendi kapsamı
`tests/test_semread_001d_semantic_content.py`'dedir. Şema/reader `/3` bump'ı ve prompt v3 bu
commit'te yapıldı; v3 sözleşmesinin kendi kapsamı `tests/test_semread_001d_prompt_v3.py`'dedir
(bu dosya 001C'nin `/2` sözleşmesini değil, sürüm ilerlemesini denetler).

Model çağrısı yok; yalnız şema + parser + prompt (saf fonksiyonlar).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from drawingto3d.semantic_candidates import (CANDIDATE_READER_VERSION, CANDIDATE_SCHEMA_VERSION,
                                             TASK_INSTRUCTIONS, CandidateParseError, Region,
                                             candidate_json_schema, candidate_prompt,
                                             parse_candidate_json)
from drawingto3d.observe import BBox, Frame, Observations, Primitive, SourceRef, TextObservation
from drawingto3d.semantic_candidate_reader import read_page
from drawingto3d.semantic_schema import PreparedImage

GOLD_SENTINEL = "semread-001b-gold-sentinel-4f21"

ROOT = Path(__file__).resolve().parents[1]


def _load_pilot():
    """001C sürücüsü: 001B pilot modülünü yükler (saf fonksiyonlar; çağrı yok)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("semread_001c_contract_pilot",
                                                  ROOT / "eval/semread_001b_pilot.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pilot yüklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

PIXEL_REGION = {"x0": 65, "y0": 287, "x1": 349, "y1": 450}
NORMALIZED_REGION = {"x0": 0.10, "y0": 0.20, "x1": 0.30, "y1": 0.40}


def _candidate_body(region: dict) -> str:
    return json.dumps({
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "items": [{
            "candidate_id": "c1",
            "source": {"image_id": "image-1", "region": region},
        }],
    })


def _semantic_candidate_body(region: dict) -> str:
    """Kabul fixture'ı: zorunlu alanlar + **bir** semantic claim (callout metni, 001D §5).

    Claimsiz gövde (`_candidate_body`) artık wire'dan geçmez; onu yalnız yapısal ret yolları
    (koordinat/anahtar/no-guess) kullanır — semantik ret o yolları **ezmez** çünkü yapısal
    doğrulama önce karara bağlanır.
    """
    payload = json.loads(_candidate_body(region))
    payload["items"][0]["callout"] = {"text": "Ø8", "state": "known"}
    return json.dumps(payload)


def _region_schemas() -> dict[str, dict]:
    items = candidate_json_schema()["properties"]["items"]["items"]["properties"]
    return {
        "source.region": items["source"]["properties"]["region"],
        "source.callout_region": items["source"]["properties"]["callout_region"],
        "target.region": items["target"]["properties"]["region"],
    }


def test_p1_versions_are_bumped():
    """PLAN-12 §13: çıktıyı etkileyen değişiklik sürümü ilerletir.

    001D §3/§61: semantik-içerik sözleşmesi modele de taşındığı için şema **ve** okuyucu birlikte
    `/3`'e çıktı (001C'nin `/2`'si history'de kalır). `/3`'ün anlamı `semantic_candidates`
    version notes'unda: semantic-empty aday geçersiz, semantic claim ≠ evidence-only,
    prompt semantic-first, no-guess korunur.
    """
    assert CANDIDATE_SCHEMA_VERSION == "semread-candidates/3"
    assert CANDIDATE_READER_VERSION == "semread-candidate-reader/3"


def test_p1_region_schema_declares_normalized_bounds_in_all_three_places():
    schemas = _region_schemas()
    for name, region in schemas.items():
        for key in ("x0", "y0", "x1", "y1"):
            prop = region["properties"][key]
            assert prop["minimum"] == 0.0, f"{name}.{key}"
            assert prop["maximum"] == 1.0, f"{name}.{key}"
        assert "Never use pixel coordinates." in region["description"], name
        assert "[0,1]" in region["description"], name
    # Aynı sözleşme: üç alanın property tanımları birebir aynı nesneden gelir.
    assert schemas["source.region"]["properties"] == schemas["source.callout_region"]["properties"]
    assert schemas["source.region"]["properties"] == schemas["target.region"]["properties"]
    assert schemas["source.region"]["required"] == ["x0", "y0", "x1", "y1"]


def test_p1_pixel_coordinates_are_rejected_not_repaired():
    """Sessiz normalize yok (PLAN-12 §38/§39): piksel bölge reddedilir."""
    with pytest.raises(ValueError):
        Region(x0=65.0, y0=287.0, x1=349.0, y1=450.0)
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(_candidate_body(PIXEL_REGION))
    assert "0..1" in str(excinfo.value)


def test_p1_normalized_example_is_accepted():
    region = Region(**NORMALIZED_REGION)
    assert region.as_list() == [0.10, 0.20, 0.30, 0.40]
    # 001D §5: kabul fixture'ı tek semantic claim taşır (claimsiz gövde wire'dan geçmez).
    response = parse_candidate_json(_semantic_candidate_body(NORMALIZED_REGION))
    assert response.items[0].source.region.as_list() == [0.10, 0.20, 0.30, 0.40]


def test_p1_common_prompt_teaches_the_normalized_convention_in_both_arms():
    """V ve VE aynı ortak metni görür; fark yalnız gözlem tablosudur (§15.2)."""
    v_prompt = candidate_prompt(["image-1"])
    ve_prompt = candidate_prompt(["image-1"], observations=[
        {"id": "t0", "kind": "text", "text": "Ø8", "value": 8.0, "unit": "mm",
         "region": [0.1, 0.2, 0.3, 0.4]},
    ])
    for prompt in (v_prompt, ve_prompt):
        assert TASK_INSTRUCTIONS in prompt
        assert "x0,y0,x1,y1 in [0,1]" in prompt
        assert "Top-left is (0,0), bottom-right is (1,1)." in prompt
        assert "Never return pixel coordinates." in prompt
        assert '{"x0":0.10,"y0":0.20,"x1":0.30,"y1":0.40}' in prompt
    assert "observation_id | kind | text" not in v_prompt
    assert "observation_id | kind | text" in ve_prompt
    # Ortak metin birebir aynı: koordinat bloğu iki kolda da TASK_INSTRUCTIONS'tan gelir.
    assert TASK_INSTRUCTIONS.rstrip("\n") == v_prompt.split("Image ids")[0].rstrip("\n")


def test_p1_prompt_carries_no_gold_or_page_specific_text():
    for prompt in (candidate_prompt(["image-1"]),
                   candidate_prompt(["image-1"], observations=[
                       {"id": "g0", "kind": "circle", "text": None, "value": None,
                        "unit": None, "region": [0.1, 0.1, 0.3, 0.3]},
                   ])):
        assert GOLD_SENTINEL not in prompt
        for marker in ("dev-plate-pocket", "Exercise", "Flange", "semread-001b-gold",
                       "frozen-"):
            assert marker not in prompt
        # Örnek yalnız koordinat biçimidir: piksel örneği yok.
        assert '"x0":65' not in prompt
        assert '"x0":0.10' in prompt


# ---------------------------------------------------------------- P2: compact output


def _minimal_body() -> str:
    """Yalnız zorunlu alanlar: candidate_id + source{image_id, region}.

    001D §5 notu: bu gövde artık **semantik-içeriksizdir** ve kabul yollarında kullanılmaz —
    yalnız yapısal ret örneklerinde (anahtar/koordinat/no-guess) kullanılır. Kabul fixture'ı
    `_semantic_candidate_body`; claimsiz reddin kapsamı `tests/test_semread_001d_semantic_content.py`.
    """
    return _candidate_body(NORMALIZED_REGION)


class _FakeChat:
    """Taşıma sınırında duran taklit: ağ yok; stats/trace/raw_response doldurulur."""

    def __init__(self, answer: str, *, done_reason: str = "stop",
                 metadata_complete: bool = True) -> None:
        self.answer = answer
        self.done_reason = done_reason
        self.metadata_complete = metadata_complete

    def complete(self, prompt, **kwargs):
        kwargs["stats"].update({"done_reason": self.done_reason, "eval_count": 12,
                                "prompt_eval_count": 40 if self.metadata_complete else None})
        kwargs["trace"].update({"model": "fake-model:1b", "options": {"temperature": 0.0},
                                "messages": [{"role": "user", "content": prompt}]})
        kwargs["raw_response"].update({"done": True})
        return self.answer


def _bundle() -> dict:
    return {"arm": "V", "page_image_id": "image-1",
            "images": [PreparedImage(image_id="image-1", kind="full_page",
                                     png=_tiny_png(), source_sha256="a" * 64,
                                     source_type="raster", render_mode="native_raster")],
            "image_ids": ["image-1"], "observations": [], "arm_input_variant": "V",
            "evidence_mode": "raw_only"}


def _tiny_png(width: int = 8, height: int = 6) -> bytes:
    """Gerçek PNG (cv2 çözebilir): sahte byte'lar `PreparedImage` doğrulamasından geçmez."""
    import cv2
    import numpy as np

    ok, buffer = cv2.imencode(".png", np.zeros((height, width), dtype=np.uint8))
    assert ok
    return buffer.tobytes()


def test_p2_optional_defaults_are_deterministic():
    """001D §5: gövde tek semantic claim (callout metni) taşır; kalan opsiyoneller varsayılan kalır."""
    first = parse_candidate_json(_semantic_candidate_body(NORMALIZED_REGION))
    candidate = first.items[0]
    assert candidate.callout.state == "known" and candidate.callout.text == "Ø8"
    assert candidate.representation.kind == "unknown"
    assert candidate.physical.kind == "unknown"
    assert candidate.form.symbol == "unknown"
    assert candidate.size.state == "unknown" and candidate.size.value is None
    assert candidate.count.state == "unknown" and candidate.count.printed is None
    assert candidate.termination.kind == "unknown" and candidate.termination.stated is False
    assert candidate.depth.state == "not_stated" and candidate.depth.value is None
    assert candidate.target.state == "unknown" and candidate.target.region is None
    assert candidate.uncertainty.fields == {}
    second = parse_candidate_json(_semantic_candidate_body(NORMALIZED_REGION))
    assert second == first, "aynı gövde aynı varsayılanları vermeli"


def test_p2_provenance_is_not_part_of_the_wire_contract():
    schema = candidate_json_schema()
    assert "provenance" not in schema["properties"]["items"]["items"]["properties"]
    payload = json.loads(_minimal_body())
    payload["items"][0]["provenance"] = {"kind": "vlm", "method": "kendi kendine"}
    with pytest.raises(CandidateParseError) as excinfo:
        parse_candidate_json(json.dumps(payload))
    assert "provenance" in str(excinfo.value)
    assert excinfo.value.kind == "schema_error"


def test_p2_prompt_asks_to_omit_default_only_optional_fields():
    for prompt in (candidate_prompt(["image-1"]), candidate_prompt(["image-1"], observations=[
            {"id": "t0", "kind": "text", "text": "Ø8", "value": 8.0, "unit": "mm",
             "region": [0.1, 0.2, 0.3, 0.4]}])):
        assert "Omit optional fields that would only contain default unknown/not_stated values." \
            in prompt


def test_p2_read_page_injects_harness_owned_provenance():
    outcome = read_page(_FakeChat(_semantic_candidate_body(NORMALIZED_REGION)), _bundle(),
                        forbidden=[])
    assert outcome["parse"]["ok"] is True
    provenance = outcome["parsed"]["items"][0]["provenance"]
    assert provenance["kind"] == "vlm"
    assert provenance["method"] == "fake-model:1b", "method çağrıda görülen model olmalı"
    assert outcome["parsed"]["items"][0]["uncertainty"]["fields"] == {}


def test_p2_parse_error_kinds_are_machine_readable():
    with pytest.raises(CandidateParseError) as broken_json:
        parse_candidate_json("bu JSON değil")
    assert broken_json.value.kind == "invalid_json"
    with pytest.raises(CandidateParseError) as coordinate:
        parse_candidate_json(_candidate_body(PIXEL_REGION))
    assert coordinate.value.kind == "schema_coordinate"
    no_guess = json.loads(_minimal_body())
    no_guess["items"][0]["termination"] = {"kind": "finite", "stated": True}
    with pytest.raises(CandidateParseError) as guessed:
        parse_candidate_json(json.dumps(no_guess))
    assert guessed.value.kind == "schema_no_guess"


# ---------------------------------------------------------------- P3: VE evidence compression


def _observations_with_gaps() -> Observations:
    """3 dolu + 2 boş-kanıt satır: g0 (nokta+bölge) kalır; p1/g1 bölgesiz kalır; t1 bölgeli."""
    return Observations(
        source=SourceRef(ref="probe.png", sha256="b" * 64, page=0),
        frame=Frame(width=400, height=300), text_placement="as-is",
        primitives=[
            Primitive(id="g0", path_id="p0", kind="circle", centre=[100.0, 80.0], radius=12.0),
            Primitive(id="p1", path_id="p1", kind="line", start=[10.0, 10.0], end=[50.0, 50.0]),
            Primitive(id="g1", path_id="p2", kind="arc"),
        ],
        texts=[
            TextObservation(id="t0", text="Ø8", value=8.0, unit="mm", kind="diameter",
                            bbox=BBox(x=120, y=70, w=30, h=10)),
            TextObservation(id="t1", text="", value=None, kind="text",
                            bbox=BBox(x=200, y=150, w=40, h=12)),
        ])


def test_p3_empty_evidence_rows_are_pruned_with_stable_order_and_hash():
    from hashlib import sha256

    from drawingto3d.semantic_candidate_reader import (observation_table,
                                                       observation_table_with_counts)
    observations = _observations_with_gaps()
    rows, counts = observation_table_with_counts(observations)
    assert [row["id"] for row in rows] == ["g0", "t0", "t1"]
    assert counts == {"raw": 5, "sent": 3, "dropped": 2}
    rows_again, counts_again = observation_table_with_counts(observations)
    assert rows_again == rows and counts_again == counts
    dump = json.dumps(rows, sort_keys=True, ensure_ascii=False)
    dump_again = json.dumps(rows_again, sort_keys=True, ensure_ascii=False)
    assert sha256(dump.encode()).hexdigest() == sha256(dump_again.encode()).hexdigest()
    for row in rows:
        assert set(row) <= {"id", "kind", "text", "value", "unit", "region"}, "nötr alanlar"
        assert "gold" not in json.dumps(row).lower()
    # Kural sınırı: bölgesi olan boş metin satırı kalır — bölge adreslenebilir kanıttır.
    assert any(row["id"] == "t1" for row in rows)
    assert observation_table(observations) == rows


def test_p3_ve_bundle_records_raw_sent_dropped_and_prompt_follows_the_pruned_table(tmp_path):
    from drawingto3d.semantic_candidate_reader import prepare_arm_inputs
    from drawingto3d.semantic_images import open_source

    source = open_source(_write_page_png(tmp_path))
    observations = _observations_with_gaps()
    ve_bundle = prepare_arm_inputs(source, observations, image_id="image-1", arm="VE")
    assert ve_bundle["observation_counts"] == {"raw": 5, "sent": 3, "dropped": 2}
    assert len(ve_bundle["observations"]) == 3
    ve_prompt = candidate_prompt(["image-1"], observations=ve_bundle["observations"])
    assert "g0" in ve_prompt and "t0" in ve_prompt and "t1" in ve_prompt
    assert "| line |" not in ve_prompt and "| arc |" not in ve_prompt, \
        "boş kanıt satırı prompt'a girmemeli"
    v_bundle = prepare_arm_inputs(source, observations, image_id="image-1", arm="V")
    assert v_bundle["observations"] == []
    assert v_bundle["observation_counts"] == {"raw": 5, "sent": 0, "dropped": 0}


def test_p3_prediction_input_records_prompt_bytes_and_observation_counts():
    pilot = _load_pilot()
    bundle = {"observations": [], "images": [],
              "observation_counts": {"raw": 5, "sent": 0, "dropped": 0}}
    prompt = "örnek görev metni"
    record = pilot.prediction_input_record({"page_id": "page"}, "V", bundle=bundle, prompt=prompt)
    assert record["prompt_bytes"] == len(prompt.encode("utf-8"))
    assert record["observation_counts"] == {"raw": 5, "sent": 0, "dropped": 0}


def _write_page_png(tmp_path, width: int = 400, height: int = 300):
    import cv2
    import numpy as np

    path = tmp_path / "page.png"
    ok, buffer = cv2.imencode(".png", np.full((height, width), 255, dtype=np.uint8))
    assert ok
    path.write_bytes(buffer.tobytes())
    return path


# ---------------------------------------------------------------- P4: truncation first-class


def test_p4_length_done_reason_is_truncated_output_and_never_parsed():
    valid_body = _candidate_body(NORMALIZED_REGION)
    outcome = read_page(_FakeChat(valid_body, done_reason="length"), _bundle(), forbidden=[])
    assert outcome["failure_kind"] == "truncated_output"
    assert outcome["parse"]["ok"] is False and outcome["parse"]["kind"] == "truncated_output"
    assert outcome.get("parsed") is None, "kesilmiş yanıt semantik-geçerli olamaz"
    assert outcome["raw_response"] == valid_body, "ham yanıt korunur"
    assert outcome["truncated"] == {"done_reason": "length", "state": "truncated",
                                    "metadata_complete": True, "parse_eligible": False}


def test_p4_stop_with_incomplete_metadata_fails_closed():
    outcome = read_page(_FakeChat(_candidate_body(NORMALIZED_REGION), metadata_complete=False),
                        _bundle(), forbidden=[])
    assert outcome["failure_kind"] == "incomplete_metadata"
    assert outcome["parse"]["ok"] is False and outcome.get("parsed") is None
    assert outcome["truncated"]["state"] == "unknown"
    assert outcome["truncated"]["metadata_complete"] is False


def test_p4_parse_error_subtypes_survive_the_transport():
    broken = read_page(_FakeChat("bu JSON değil"), _bundle(), forbidden=[])
    assert broken["failure_kind"] == "invalid_json"
    assert broken["parse"]["kind"] == "invalid_json"
    coordinate = read_page(_FakeChat(_candidate_body(PIXEL_REGION)), _bundle(), forbidden=[])
    assert coordinate["failure_kind"] == "schema_coordinate"
    body = json.loads(_candidate_body(NORMALIZED_REGION))
    body["items"][0]["termination"] = {"kind": "finite", "stated": True}
    guessed = read_page(_FakeChat(json.dumps(body)), _bundle(), forbidden=[])
    assert guessed["failure_kind"] == "schema_no_guess"


def test_p4_attempt_state_keeps_truncation_apart_from_parse_error():
    pilot = _load_pilot()
    answered = {"outcome": "answered"}
    assert pilot.attempt_state({**answered, "failure_kind": "truncated_output"},
                               {"parsed": False}) == "truncated_output"
    assert pilot.attempt_state({**answered, "failure_kind": "incomplete_metadata"},
                               {"parsed": False}) == "incomplete_metadata"
    assert pilot.attempt_state({**answered, "failure_kind": "invalid_json"},
                               {"parsed": False}) == "parse_error"
    assert pilot.attempt_state({**answered, "failure_kind": None},
                               {"parsed": True, "gates_ok": True}) == "pass"
    assert pilot.attempt_state({**answered, "failure_kind": None},
                               {"parsed": True, "gates_ok": False}) == "failed_gates"
    assert pilot.attempt_state({"outcome": "error", "failure_kind": "http_error"},
                               {"parsed": False}) == "transport_error"
    assert {"truncated_output", "incomplete_metadata"} <= set(pilot.FINALIZED_STATES)
    assert {"truncated_output", "incomplete_metadata"} <= set(pilot.DISPATCHED_ATTEMPT_STATES)


# ---------------------------------------------------------------- P5/P6: zarf + deney kökü


def test_p5_run_contract_envelope_is_001d_and_measured():
    from drawingto3d.semantic_run_contract import (CONTRACT_VERSION, NUM_PREDICT,  # noqa: F401
                                                   REPEAT_LAST_N, REPEAT_PENALTY,
                                                   SETTINGS)

    # PLAN-15 §9/§10: kimlik 001D'ye ilerledi; **zarf ölçümü ve değerleri 001C kapanışından
    # birebir devralındı** — bu commit'te hiçbir üretim ayarı değişmedi.
    assert CONTRACT_VERSION == "semread-001d-run-contract/1"
    # Dev ölçümü zarfı dört kez ilerletti: plate-VE 3072'de kesildi → 4096 → 5120 (sınırda);
    # elbow-V 5120'de kesildi (≥41 aday!) → 8192; flange-VE 14.121 tok promptla 12288'de 400 aldı
    # → 20480 → 22528 (flange 14.121+8.192=22.313 ≤ 22.528).
    assert NUM_PREDICT == 8192 and SETTINGS["num_predict"] == NUM_PREDICT
    assert SETTINGS["num_ctx"] == 22528
    assert 14121 + SETTINGS["num_predict"] <= SETTINGS["num_ctx"]
    # PLAN-13 §4/§6: kol-başına repeat_penalty KALDIRILDI (zarf #7 → ortak zarf başlangıcı);
    # döngü sampling ile değil yapısal sözleşmeyle (maxItems + kopya kuralı) sınırlanır.
    # Ölçüm geçmişi (V 1.25 döngü / 1.6 boşalttı / 1.4 VE'yi kıstı) semantic_run_contract'ta.
    assert REPEAT_PENALTY == 1.25 and REPEAT_LAST_N == 512
    assert SETTINGS["temperature"] == 0.0


def test_plan13_shared_generation_invariant_v_equals_ve():
    """PLAN-13 §4/§8 otomatik invariantı: üretim ayarları kol-farkısız; kol farkı yalnız kanıttır."""
    import drawingto3d.semantic_run_contract as contract

    assert not hasattr(contract, "REPEAT_PENALTY_BY_ARM"), \
        "kol-başına ceza kaldırılmalı (PLAN-13 §39)"
    assert contract.generation_settings("V") == contract.generation_settings("VE")
    for arm in ("V", "VE"):
        settings = contract.generation_settings(arm)
        assert settings["repeat_penalty"] == contract.REPEAT_PENALTY
        assert settings["repeat_last_n"] == contract.REPEAT_LAST_N
        assert settings["num_ctx"] == contract.SETTINGS["num_ctx"]
        assert settings["num_predict"] == contract.SETTINGS["num_predict"]
        assert settings["temperature"] == contract.SETTINGS["temperature"]
    # İzin verilen tek sınıf fark kanıt katmanıdır (üretim ayarı değildir).
    assert contract.arm_evidence_mode("V") != contract.arm_evidence_mode("VE")
    with pytest.raises(ValueError):
        contract.generation_settings("X")


def test_p6_experiment_switch_moves_only_the_ledger(tmp_path, monkeypatch):
    pilot = _load_pilot()
    assert pilot.EXPERIMENT_NAME == "semread-001b"
    original_state = pilot.state_path()
    monkeypatch.setattr(pilot, "LAB_ROOT", tmp_path)
    info = pilot.use_experiment("semread-001c")
    assert info["experiment"] == "semread-001c"
    assert pilot.REPORT_ROOT == tmp_path / "semread-001c"
    assert pilot.CORPUS_DIR == tmp_path / "semread-001c" / "corpus"
    assert pilot.ATTEMPT_ROOT == tmp_path / "semread-001c" / "attempts"
    assert pilot.state_path() == tmp_path / "semread-001c" / "state.json"
    assert pilot.state_path() != original_state
    fresh = pilot.load_state()
    assert fresh["experiment"] == "semread-001c"
    # Taze defter **güncel deklare tavanları** taşır. 001C'nin TARİHSEL bütçesi (dev 10→…→32,
    # PLAN-13 §7 requalification'ıyla 52) kendi (READ-ONLY) state.json'unda donmuştur; canlı
    # sabitler PLAN-15 §31 ile 001D'nin deklare tavanlarıdır (dev 12 / final 20 / toplam 32).
    assert fresh["budget"] == {"dev": pilot.LIVE_CALL_LIMIT_DEV,
                               "final": pilot.LIVE_CALL_LIMIT_FINAL,
                               "total": pilot.LIVE_CALL_LIMIT_TOTAL}, "taze defter sabitlerden"
    # Geri dönüş: 001B adı yine 001B köküne çözülür; varsayılan kayıt yolu sabittir.
    pilot.use_experiment("semread-001b")
    assert pilot.EXPERIMENT_NAME == "semread-001b"
    assert pilot.REPORT_ROOT == tmp_path / "semread-001b"
