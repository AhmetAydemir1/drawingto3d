"""SEMREAD-001D — dev rapor aracının testleri (PLAN-16 §13–§29/§95).

Kapsam (hepsi 0 inference; deftere **yazılmaz**):

* §14/§15: yalnız güncel 001D kimlikli attempt'ler eligible; 001C/001B tarzı eski kimlik
  **yok sayılır** (fallback yok) ve gerekçesiyle görünür; attempt yoksa hücre `missing`;
* §16/§21: formal geçerli + semantik 0 → `semantic_valid_output` false; semantik > 0 → true;
* §19: sıfır-satırlı karşılaştırma ölçüm değildir; puanlanabilir satır varsa ölçüm vardır
  (001B `arms_with_measurement` ile aynı prensip — pin testi);
* §23: `empty_echo` vs `contentful_observation_supported` ayrımı; prompt yoksa sınıflama yok;
* §24: birebir / yakın / aynı-imza+hedef / callout-tekrarı sınıfları;
* §25: `candidate_count == MAX_ITEMS` → maxItems sinyali (tek hücre fail değil; çok hücre uyarı);
* §26: uydurulmuş ölçü/form/THRU/fiziksel yorum overclaim sayılır;
* §27/§95: araç defteri kurmaz/değiştirmez — `--write` yalnız `dev-report.json` + `dev-report.md`;
  boş kökte tüm hücreler `missing` ve `complete=false`; gold hash uyuşmazlığı fail-closed;
* Round 1 kapısı (§57/§62–§64): dört hücrenin tamamı eligible + formal + semantik-valid ve kol
  başına ≥1 gold-eşleşmeli semantik claim + alan doğruluğu > 0 ise GEÇER; aksi açık kalır.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "eval" / "semread_001d_dev_report.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("semread_001d_dev_report", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()

FAKE_IDENTITIES = {"experiment": "semread-001d",
                   "schema_version": "semread-candidates/3",
                   "reader_version": "semread-candidate-reader/3",
                   "contract_version": "semread-001d-run-contract/2",
                   "producer_identity": "p" * 64,
                   "preprocessing_identity": "q" * 64,
                   "evaluation_identity": "r" * 64}

REGION = {"x0": 0.10, "y0": 0.10, "x1": 0.20, "y1": 0.20}
REGION_FLANGE = {"x0": 0.30, "y0": 0.30, "x1": 0.40, "y1": 0.40}
CALLOUT_REGION = {"x0": 0.55, "y0": 0.55, "x1": 0.70, "y1": 0.62}
DEV_PAGE_IDS = ("dev-plate-pocket", "dev-flange-book", "dev-flange-elbow", "dev-drawing-2")


@pytest.fixture
def lab(tmp_path, monkeypatch):
    """Sahte 001D kökü + sabit kimlikler: testler gerçek deftere dokunmaz."""
    root = tmp_path / "lab"
    monkeypatch.setattr(tool, "LAB", root)
    monkeypatch.setattr(tool, "ATTEMPTS", root / "attempts")
    monkeypatch.setattr(tool, "current_identities", lambda: dict(FAKE_IDENTITIES))
    return root


@pytest.fixture
def gold_stub(monkeypatch):
    """Gold katmanını stub'lar (içeriksiz): formal/semantik odaklı testler için."""
    monkeypatch.setattr(tool, "load_dev_gold",
                        lambda: {page_id: {"reference": {"claims": []}, "reference_sha256": "x",
                                           "claim_count": 0} for page_id in DEV_PAGE_IDS})


# ------------------------------------------------------------------ yardımcılar


def _write(directory: Path, name: str, payload) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _good_options() -> dict:
    expected = tool.pilot.generation_settings("V")
    return {key: expected[key] for key in ("temperature", "num_predict", "num_ctx",
                                           "repeat_penalty", "repeat_last_n")}


def _good_gates() -> dict:
    return {"parse": {"ok": True}, "references": {"ok": True},
            "truncated": {"done_reason": "stop", "state": "complete", "metadata_complete": True,
                          "parse_eligible": True},
            "leakage": []}


def _manifest(**overrides) -> dict:
    manifest = {"experiment": FAKE_IDENTITIES["experiment"],
                "schema_version": FAKE_IDENTITIES["schema_version"],
                "reader_version": FAKE_IDENTITIES["reader_version"],
                "contract_version": FAKE_IDENTITIES["contract_version"],
                "producer_identity": FAKE_IDENTITIES["producer_identity"],
                "preprocessing_identity": FAKE_IDENTITIES["preprocessing_identity"],
                "settings": dict(tool.pilot.SETTINGS)}
    manifest.update(overrides)
    return manifest


def _write_attempt(root: Path, cell: str, number: int = 1, *, manifest=None, state="pass",
                   gates=None, parsed=None, options=None, prompt=None, stats=None) -> Path:
    directory = root / cell / f"attempt-{number:04d}"
    _write(directory, "manifest.json", manifest if manifest is not None else _manifest())
    _write(directory, "result.json", {"attempt_id": f"{cell}/attempt-{number:04d}", "state": state,
                                      "send_attempted": state not in ("blocked_budget",),
                                      "inference_calls": 1, "seconds": 12.5})
    _write(directory, "gate-results.json", gates if gates is not None else _good_gates())
    _write(directory, "resources.json",
           {"stats": stats if stats is not None else {"done_reason": "stop", "eval_count": 100,
                                                      "prompt_eval_count": 1000}})
    _write(directory, "request-manifest.json", {"options": options if options is not None
                                                else _good_options()})
    if parsed is not None:
        _write(directory, "response-parsed.json", parsed)
    if prompt is not None:
        (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
    return directory


def _parsed(*items) -> dict:
    return {"schema_version": "semread-candidates/3", "items": list(items)}


def _claim_item(candidate_id="c1", region=None, text="Ø8", **overrides) -> dict:
    region = dict(region or REGION)
    item = {"candidate_id": candidate_id,
            "callout": {"text": text, "state": "known"},
            "representation": {"kind": "circle"},
            "physical": {"kind": "hole"},
            "form": {"symbol": "diameter"},
            "size": {"value": 8.0, "unit": "mm", "state": "known"},
            "count": {"printed": 4, "state": "known"},
            "termination": {"kind": "thru", "stated": True},
            "depth": {"value": None, "state": "not_stated"},
            "target": {"region": region, "state": "bound"},
            "source": {"image_id": "image-1", "region": dict(region)}}
    item.update(overrides)
    return item


def _claimless_item(candidate_id="e1", region=None) -> dict:
    region = dict(region or REGION)
    return {"candidate_id": candidate_id,
            "count": {"found_circles": 2},
            "source": {"image_id": "image-1", "region": region}}


def _gold_claim(claim_id, region=None, **overrides) -> dict:
    claim = {"claim_id": claim_id,
             "target": {"region": dict(region or REGION), "observation_id": "g1"},
             "callout": {"region": dict(CALLOUT_REGION)},
             "representation": "circle", "physical": "hole", "form": "diameter", "size": 8.0,
             "unit": "mm", "count_printed": 4, "termination": "thru", "depth": None}
    claim.update(overrides)
    return claim


def _write_gold(tmp_path, monkeypatch, claims_by_page: dict) -> None:
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    pages = []
    for page_id in DEV_PAGE_IDS:
        claims = claims_by_page.get(page_id, [])
        payload = {"schema": "semread-001b-gold/1", "page_id": page_id, "claims": claims,
                   "exhaustiveness": {"scope": "predicates",
                                      "predicates": ["representation", "physical", "form", "size",
                                                     "count_printed", "termination", "depth"]}}
        path = gold_dir / f"{page_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        pages.append({"page_id": page_id, "split": "dev", "claim_count": len(claims),
                      "reference_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    freeze = tmp_path / "FREEZE.json"
    freeze.write_text(json.dumps({"schema": "semread-001b-freeze/1", "pages": pages},
                                 ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(tool, "GOLD_001B", gold_dir)
    monkeypatch.setattr(tool, "FREEZE", freeze)


# ------------------------------------------------------------------ §14/§15 seçim

def test_a_cell_without_attempts_reports_missing_and_creates_no_ledger(lab):
    report = tool.build_report()
    assert [cell["attempt_state"] for cell in report["cells"]] == ["missing"] * 8
    assert all(cell["measurement"]["measured"] is False for cell in report["cells"])
    assert all(cell["semantic_valid_output"] is False for cell in report["cells"])
    assert report["completion"]["complete"] is False
    assert "eligible attempt yok" in " ".join(report["completion"]["reasons"])
    assert not lab.exists(), "rapor aracı çalıştı diye defter kurmaz (§27)"


def test_old_identity_attempts_are_ignored_without_fallback(lab):
    """001B/001C tarzı eski kimlik: experiment/schema/reader yok + eski contract → yok sayılır."""
    legacy = {"contract_version": "semread-001c-run-contract/1", "producer_identity": "old" * 21,
              "settings": dict(tool.pilot.SETTINGS)}
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1, manifest=legacy,
                   parsed=_parsed(_claim_item("legacy")))
    report = tool.build_report()
    cell = next(row for row in report["cells"] if row["cell"] == "dev-plate-pocket-V")
    assert cell["attempt_state"] == "missing"
    reasons = " ".join(reason for row in report["attempts"]["ignored_attempts"]
                       for reason in row["reasons"])
    assert "experiment" in reasons and "contract_version" in reasons
    assert report["completion"]["complete"] is False


def test_a_wrong_producer_identity_is_ignored(lab):
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1,
                   manifest=_manifest(producer_identity="x" * 64), parsed=_parsed(_claim_item()))
    report = tool.build_report()
    cell = next(row for row in report["cells"] if row["cell"] == "dev-plate-pocket-V")
    assert cell["attempt_state"] == "missing"
    assert any("producer_identity" in reason
               for row in report["attempts"]["ignored_attempts"] for reason in row["reasons"])


def test_a_wrong_contract_identity_is_ignored(lab):
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1,
                   manifest=_manifest(contract_version="semread-001c-run-contract/1"),
                   parsed=_parsed(_claim_item()))
    report = tool.build_report()
    assert next(row for row in report["cells"]
                if row["cell"] == "dev-plate-pocket-V")["attempt_state"] == "missing"


# ------------------------------------------------------------------ §16/§21 formal + semantik

def test_formal_pass_with_zero_semantic_claims_is_not_semantic_valid(lab, gold_stub):
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1,
                   parsed=_parsed(_claimless_item()))
    report = tool.build_report()
    cell = next(row for row in report["cells"] if row["cell"] == "dev-plate-pocket-V")
    assert tool.formal_valid(cell["formal"]) is True, "kayıtlı kapılar geçerli olmalı"
    assert cell["semantic"]["semantic_claim_count"] == 0
    assert cell["semantic"]["evidence_only_count"] == 1
    assert cell["semantic_valid_output"] is False


def test_formal_pass_with_a_semantic_claim_is_semantic_valid(lab, gold_stub):
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1, parsed=_parsed(_claim_item()))
    report = tool.build_report()
    cell = next(row for row in report["cells"] if row["cell"] == "dev-plate-pocket-V")
    assert tool.formal_valid(cell["formal"]) is True
    assert cell["semantic"]["semantic_candidate_count"] == 1
    assert cell["semantic_valid_output"] is True
    assert cell["cell"] in report["completion"]["semantic_valid_cells"]


def test_an_empty_items_response_stays_abstention_but_not_semantic_valid(lab, gold_stub):
    """§22: boş `items` parser açısından abstention'dır; dev sayfada semantik-valid değildir."""
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1, parsed=_parsed())
    report = tool.build_report()
    cell = next(row for row in report["cells"] if row["cell"] == "dev-plate-pocket-V")
    assert cell["formal"]["candidate_count"] == 0
    assert cell["semantic"]["semantic_claim_count"] == 0
    assert cell["semantic_valid_output"] is False


def test_an_older_ineligible_pass_never_substitutes_for_an_eligible_attempt(lab, tmp_path,
                                                                            monkeypatch):
    """§15: yeni ama eski kimlikli bir pass attempt seçilmez — eligible attempt kazanır."""
    _write_gold(tmp_path, monkeypatch, {"dev-plate-pocket": [_gold_claim("p1")]})
    root = lab / "attempts"
    _write_attempt(root, "dev-plate-pocket-V", 1, parsed=_parsed(_claim_item("eligible")))
    _write_attempt(root, "dev-plate-pocket-V", 2,
                   manifest={"contract_version": "semread-001c-run-contract/1"},
                   parsed=_parsed(_claim_item("legacy"), _claim_item("legacy-2")))
    report = tool.build_report()
    cell = next(row for row in report["cells"] if row["cell"] == "dev-plate-pocket-V")
    assert cell["attempt_id"].endswith("attempt-0001")
    assert cell["formal"]["candidate_count"] == 1


# ------------------------------------------------------------------ §19 ölçüm kapısı

def test_a_zero_scorable_evaluation_is_not_measurement():
    """Belirsiz eşleşme puanlanmaz: karşılaştırma olsa da ölçüm yoktur (§19)."""
    gold = {"claims": [_gold_claim("p1")]}
    response = {"response": _parsed(_claim_item("a"), _claim_item("b"))}  # eşit puan → belirsiz
    evaluation = tool.evaluate_page(gold, response)
    assert evaluation["matching"]["ambiguous"], "iki eşit aday belirsizlik üretmeli"
    measurement = tool.cell_measurement(evaluation, available=True)
    assert measurement["measured"] is False
    assert measurement["scorable_target_count"] == 0
    # Aynı prensip 001B'nin tek kaynağında da geçerlidir (sıfır satırlı vs_d ölçüm değildir).
    zero_rows = {"comparison": {"vs_d": {"V": {"predicate_rows": [{"scorable_target_count": 0}]}}}}
    assert tool.pilot.arms_with_measurement(zero_rows) == []


def test_a_scorable_evaluation_is_measurement():
    gold = {"claims": [_gold_claim("p1")]}
    evaluation = tool.evaluate_page(gold, {"response": _parsed(_claim_item("a"))})
    measurement = tool.cell_measurement(evaluation, available=True)
    assert measurement["measured"] is True
    assert measurement["scorable_target_count"] == 1
    assert measurement["scorable_field_rows"] >= 1
    # 001B tek kaynağı da puanlanmış satırı ölçüm sayar (parity).
    scored = {"comparison": {"vs_d": {"V": {"predicate_rows": [{"scorable_target_count": 1}]}}}}
    assert tool.pilot.arms_with_measurement(scored) == ["V"]


def test_measurement_is_absent_without_a_parsed_output():
    measurement = tool.cell_measurement(None, available=False)
    assert measurement["measured"] is False
    assert measurement["scorable_target_count"] is None


# ------------------------------------------------------------------ §23 echo v2

def _ve_prompt() -> str:
    return (
        "Task text\n"
        "observation_id | kind | text | value | unit | region(x0,y0,x1,y1 normalized)\n"
        "g1 | circle | - | - | - | 0.1000,0.1000,0.2000,0.2000\n"
        "\nReply with JSON only, matching the response schema you were given.\n")


def test_empty_echo_and_contentful_observation_support_are_two_classes():
    rows = tool.prompt_table_rows(_ve_prompt())
    assert [row["observation_id"] for row in rows] == ["g1"]
    items = [_claimless_item("copy", REGION),                     # bölge kopyası, claim yok
             _claim_item("supported", REGION),                    # kanıt + claim
             _claim_item("elsewhere", REGION_FLANGE)]             # yankı değil
    classification = tool.echo_v2(items, rows)
    assert classification["empty_echo"] == 1
    assert classification["contentful_observation_supported"] == 1
    assert classification["classified"] == 2
    classes = {row["candidate_id"]: row["class"] for row in classification["detail"]}
    assert classes == {"copy": "empty_echo", "supported": "contentful_observation_supported"}


def test_echo_classification_is_unavailable_without_the_sent_prompt():
    classification = tool.echo_v2([_claim_item()], None)
    assert classification["classified"] is None
    assert "kanıt eksik" in classification["note"]


# ------------------------------------------------------------------ §24 kopya

def test_duplicate_metrics_classify_exact_near_signature_and_callout_text():
    near = {"x0": 0.12, "y0": 0.12, "x1": 0.22, "y1": 0.22}
    far_d = {"x0": 0.60, "y0": 0.60, "x1": 0.70, "y1": 0.70}
    far_e = {"x0": 0.80, "y0": 0.80, "x1": 0.90, "y1": 0.90}
    first = _claim_item("a", REGION, target={"region": dict(REGION), "observation_id": "g1",
                                             "state": "bound"})
    items = [
        first,
        # b: birebir bölge; hedefsiz (imza+hedef eşleşmesi üretmez)
        _claim_item("b", REGION),
        # c: yakın bölge (IoU ≥ 0.15), farklı callout metni
        _claim_item("c", near, text="Ø9"),
        # d: uzak bölge; semantik imza a ile aynı + hedef (gözlem kimliği) aynı
        _claim_item("d", far_d, target={"region": dict(far_d), "observation_id": "g1",
                                        "state": "bound"}),
        # e: uzak bölge; yalnız aynı callout metni tekrarı
        _claim_item("e", far_e),
    ]
    metrics = tool.duplicate_metrics(items)
    assert metrics["exact_duplicates"] == 1
    assert metrics["near_duplicates"] == 1
    assert metrics["signature_target_duplicates"] == 1
    assert metrics["callout_text_repeats"] == 3
    assert metrics["duplicates_total"] == 4, "ilk üye (a) kopya sayılmaz"


def test_the_first_member_is_never_a_duplicate():
    metrics = tool.duplicate_metrics([_claim_item("a", REGION)])
    assert metrics["duplicates_total"] == 0


# ------------------------------------------------------------------ §25 maxItems

def test_max_items_flag_marks_32_candidates_and_warns_on_multiple_cells(lab, gold_stub):
    many = [_claim_item(f"c{index}", {"x0": 0.01 * index, "y0": 0.01, "x1": 0.01 * index + 0.01,
                                      "y1": 0.02}) for index in range(tool.MAX_ITEMS)]
    assert len(many) == 32
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1, parsed=_parsed(*many))
    _write_attempt(lab / "attempts", "dev-plate-pocket-VE", 1, parsed=_parsed(*many))
    report = tool.build_report()
    for cell_id in ("dev-plate-pocket-V", "dev-plate-pocket-VE"):
        cell = next(row for row in report["cells"] if row["cell"] == cell_id)
        assert cell["formal"]["max_items_hit"] is True
        assert cell["formal"]["candidate_count"] == tool.MAX_ITEMS
    assert report["degeneracy"]["degeneracy_warning"] is True
    assert len(report["degeneracy"]["max_items_cells"]) == 2


# ------------------------------------------------------------------ §26 overclaim

def test_overclaim_metrics_capture_invented_values():
    gold = {"claims": [_gold_claim("p1", size=None, termination="unknown", form="unknown",
                                   physical="unknown", count_printed=None, depth=None)]}
    candidate = _claim_item("a", termination={"kind": "thru", "stated": True})
    evaluation = tool.evaluate_page(gold, {"response": _parsed(candidate)})
    counts = tool.overclaim_metrics(evaluation)
    assert counts["invented_size"] == 1
    assert counts["invented_count"] == 1
    assert counts["invented_form"] == 1
    assert counts["invented_thru"] == 1
    assert counts["unsupported_physical_meaning"] == 1
    assert counts["total"] >= 5


def test_a_correct_pair_reports_no_overclaim():
    gold = {"claims": [_gold_claim("p1")]}
    evaluation = tool.evaluate_page(gold, {"response": _parsed(_claim_item("a"))})
    counts = tool.overclaim_metrics(evaluation)
    assert counts["total"] == 0


# ------------------------------------------------------------------ §27/§95 defter ve yazım

def test_the_tool_is_read_only_and_writes_only_its_two_artifacts(lab):
    assert tool.main([]) == 0
    assert not lab.exists(), "salt-okur koşu hiçbir dosya yaratmaz"
    assert tool.main(["--write"]) == 0
    files = sorted(path.name for path in lab.iterdir())
    assert files == ["dev-report.json", "dev-report.md"]
    for forbidden in ("state.json", "attempts", "live-calls.guard", "budget.json"):
        assert not (lab / forbidden).exists(), f"rapor aracı ledger dosyası yaratmamalı: {forbidden}"
    payload = json.loads((lab / "dev-report.json").read_text(encoding="utf-8"))
    assert payload["schema"] == tool.REPORT_SCHEMA
    assert payload["identity"]["zero_inference"]["model_calls"] == 0
    assert "salt-okur" in (lab / "dev-report.md").read_text(encoding="utf-8")


def test_gold_hash_mismatch_fails_closed(lab, tmp_path, monkeypatch):
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1, parsed=_parsed(_claim_item()))
    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    for page_id in DEV_PAGE_IDS:
        (gold_dir / f"{page_id}.json").write_text('{"claims": []}', encoding="utf-8")
    freeze = tmp_path / "FREEZE.json"
    freeze.write_text(json.dumps({"pages": [{"page_id": page_id, "reference_sha256": "0" * 64}
                                            for page_id in DEV_PAGE_IDS]}), encoding="utf-8")
    monkeypatch.setattr(tool, "GOLD_001B", gold_dir)
    monkeypatch.setattr(tool, "FREEZE", freeze)
    with pytest.raises(SystemExit):
        tool.build_report()


def test_no_transport_call_happens_during_a_build(lab, tmp_path, monkeypatch):
    """0 inference kanıtı: gönderim yolu (read_page) trap'lenir; build hiç çağırmaz."""
    _write_gold(tmp_path, monkeypatch, {"dev-plate-pocket": [_gold_claim("p1")]})
    _write_attempt(lab / "attempts", "dev-plate-pocket-V", 1, parsed=_parsed(_claim_item()))

    def must_not_send(*_args, **_kwargs):
        raise AssertionError("dev raporu model çağrısı yapamaz (0 inference)")

    monkeypatch.setattr(tool.pilot, "read_page", must_not_send)
    report = tool.build_report()
    assert report["identity"]["zero_inference"]["model_calls"] == 0
    source = TOOL_PATH.read_text(encoding="utf-8")
    assert "read_page(" not in source and ".complete(" not in source


# ------------------------------------------------------------------ Round kapıları (§57/§62–§64)

def test_round_gates_open_when_cells_are_missing(lab):
    report = tool.build_report()
    assert report["rounds"]["round_1"]["passed"] is False
    assert "four_cells_present" in report["rounds"]["round_1"]["open"]
    assert report["rounds"]["round_2"]["passed"] is False


def test_a_full_semantic_round_1_passes_the_gate(lab, tmp_path, monkeypatch):
    _write_gold(tmp_path, monkeypatch,
                {"dev-plate-pocket": [_gold_claim("p1")],
                 "dev-flange-book": [_gold_claim("f1", region=REGION_FLANGE)]})
    root = lab / "attempts"
    _write_attempt(root, "dev-plate-pocket-V", 1, parsed=_parsed(_claim_item("v1", REGION)))
    _write_attempt(root, "dev-plate-pocket-VE", 1, parsed=_parsed(_claim_item("ve1", REGION)),
                   prompt=_ve_prompt())
    _write_attempt(root, "dev-flange-book-V", 1,
                   parsed=_parsed(_claim_item("v2", REGION_FLANGE)))
    _write_attempt(root, "dev-flange-book-VE", 1,
                   parsed=_parsed(_claim_item("ve2", REGION_FLANGE)))
    report = tool.build_report()
    gate = report["rounds"]["round_1"]
    assert gate["passed"] is True, gate["open"]
    for row in gate["cells"]:
        assert row["formal_valid"] and row["semantic_valid"]
        assert row["gold_matched_semantic_claims"] == 1
    assert gate["per_arm"]["V"]["semantic_field_accuracy"] > 0
    assert gate["per_arm"]["VE"]["semantic_field_accuracy"] > 0
    assert report["rounds"]["round_2"]["passed"] is False
    assert report["completion"]["complete"] is True, report["completion"]["reasons"]
    assert all(cell["measurement"]["measured"] for cell in report["cells"]
               if cell["attempt_id"])
