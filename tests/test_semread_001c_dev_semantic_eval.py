"""SEMREAD-001C (§37/§38) — dev semantik değerlendirme aracının testleri.

Kapsam:

* içerik-doluluk taraması yalnız **gerçek** semantik alanı sayar (unknown/boş sayılmaz);
* observation-tablo yankısı eşiklemesi (4 ondalık yuvarlama toleransı) doğru çalışır;
* kopya taraması erken üyeyi temsilci sayar (ilk aday kopya değildir);
* `determine_reading` ölçüme bağlı okuma üretir (içerik yok + boş flood → bastırma okuması
  desteklenmiyor);
* rapor bu çalışma ağacındaki gerçek defterden kurulur ve şunları kanıtlar: 12 hücre (4 sayfa ×
  D/V/VE) değerlendirildi, bölümleme toplamı aday sayısına eşit, **sıfır inference** (llama
  import edilmedi), araç defteri **değiştirmez** (salt-okur).

Testler defteri **yazmaz**; integration testi `out/` yoksa (temiz klon) atlanır.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "eval" / "semread_001c_dev_semantic_eval.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("semread_001c_dev_semantic_eval", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _region(x0, y0, x1, y1):
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}


def _empty_candidate(candidate_id: str, region: dict) -> dict:
    return {"candidate_id": candidate_id, "source": {"region": region},
            "target": {"region": None, "observation_id": None, "state": "unknown"}}


def _contentful_candidate(candidate_id: str, region: dict) -> dict:
    return {"candidate_id": candidate_id, "source": {"region": region},
            "callout": {"text": "Ø8 THRU"}, "representation": {"kind": "circle"},
            "size": {"value": 8.0, "state": "known"}, "target": {"observation_id": "g1"}}


def test_semantic_fill_counts_only_real_content():
    fill = tool.semantic_fill([_empty_candidate("a", _region(0.1, 0.1, 0.2, 0.2)),
                               _contentful_candidate("b", _region(0.3, 0.3, 0.4, 0.4))])
    assert fill["candidates"] == 2
    assert fill["contentful_candidates"] == 1
    assert fill["fields"]["callout_text"] == 1
    assert fill["fields"]["representation"] == 1
    assert fill["fields"]["size"] == 1
    assert fill["fields"]["target_observation_id"] == 1
    assert fill["fields"]["physical"] == 0


def test_prompt_table_rows_and_echo_tolerance():
    prompt = (
        "observation_id | kind | text | value | unit | region(x0,y0,x1,y1 normalized)\n"
        "g1 | circle | - | - | - | 0.1,0.2,0.3,0.4\n"
        "t0 | text | 4 x | - | mm | 0.0634,0.5021,0.0764,0.5560\n"
        "\nReply with JSON only, matching the response schema you were given.\n")
    rows = tool.prompt_table_rows(prompt)
    assert [row["observation_id"] for row in rows] == ["g1", "t0"]
    assert rows[1]["region"] == (0.0634, 0.5021, 0.0764, 0.5560)
    # Tam eşleşme (yuvarlatılmış) yankı sayılır; kaba fark sayılmaz.
    assert tool.echo_of(tool.Region(**_region(0.0634, 0.5021, 0.0764, 0.556)),
                        rows)["observation_id"] == "t0"
    assert tool.echo_of(tool.Region(**_region(0.0635, 0.5021, 0.0764, 0.556)), rows) is not None
    assert tool.echo_of(tool.Region(**_region(0.07, 0.5021, 0.0764, 0.556)), rows) is None


def test_duplicate_scan_first_member_is_not_a_duplicate():
    items = [_empty_candidate("a", _region(0.1, 0.1, 0.2, 0.2)),
             _empty_candidate("b", _region(0.1, 0.1, 0.2, 0.2)),          # birebir kopya
             _empty_candidate("c", _region(0.12, 0.12, 0.22, 0.22)),      # yakın (IoU ≥ 0.15)
             _empty_candidate("d", _region(0.6, 0.6, 0.7, 0.7))]          # bağımsız
    scan = tool.duplicate_scan(items)
    assert scan["exact_of"][0] is None and scan["exact_of"][1] == "a"
    assert scan["near_of"][0] is None and scan["near_of"][2] == "a"
    assert scan["near_of"][3] is None
    assert scan["exact_duplicates"] == 1 and scan["near_duplicates"] == 1
    assert scan["duplicates_total"] == 2


def test_classify_partition_precedence_and_total():
    echo = {"observation_id": "t2", "kind": "text"}
    flags = [
        {"matched": True, "exact_duplicate_of": None, "near_duplicate_of": None,
         "echo": {"observation_id": "g1", "kind": "circle"}, "extra_kind": None},
        {"matched": False, "exact_duplicate_of": "a", "near_duplicate_of": None,
         "echo": None, "extra_kind": None},                                  # birebir kopya
        {"matched": False, "exact_duplicate_of": None, "near_duplicate_of": "a",
         "echo": echo, "extra_kind": None},                                  # yakın kopya > yankı
        {"matched": False, "exact_duplicate_of": None, "near_duplicate_of": None,
         "echo": echo, "extra_kind": "unscorable_extra_candidate"},          # yankı > extra
        {"matched": False, "exact_duplicate_of": None, "near_duplicate_of": None,
         "echo": None, "extra_kind": "false_positive"},                      # kapsam içi FP
        {"matched": False, "exact_duplicate_of": None, "near_duplicate_of": None,
         "echo": None, "extra_kind": None},                                  # sınıfsız → other
    ]
    partition = tool.classify_partition(flags)
    assert partition == {"matched": 1, "duplicate": 2, "echo": 1, "false_positive": 1,
                         "unscorable_extra": 0, "other": 1}
    assert sum(partition.values()) == len(flags)


def test_determine_reading_suppression_unsupported_when_floods_are_empty():
    cell = {"cell": "x-V", "fill": {"contentful_candidates": 0}}
    priors = [{"state": "truncated_output",
               "raw_scan": {"candidate_id_occurrences": 40, "nonempty_callout_texts": 0}}]
    reading = tool.determine_reading(cell, priors)
    assert "desteklenmiyor" in reading["reading"]
    assert reading["prior_flood_candidate_occurrences"] == 40
    with_content = tool.determine_reading({"cell": "x-V",
                                           "fill": {"contentful_candidates": 1}}, priors)
    assert "içerik var" in with_content["reading"]


def _ledger_available() -> bool:
    return (ROOT / "out" / "lab" / "semread-001c" / "attempts").exists()


@pytest.mark.skipif(not _ledger_available(), reason="out/ defteri yok (temiz klon)")
def test_report_builds_from_real_ledger_with_zero_inference_and_read_only():
    state_path = tool.LAB / "state.json"
    watched = [state_path, ROOT / "eval" / "semread_001b_gold" / "FREEZE.json"]
    before = {str(path): tool.sha256_of(path) for path in watched}
    report = tool.build_report()
    after = {str(path): tool.sha256_of(path) for path in watched}
    assert before == after, "araç defteri/dondurulmuş gold'u değiştirmemeli (salt-okur)"
    assert report["schema"] == tool.REPORT_SCHEMA
    cells = report["cells"]
    assert len(cells) == 4 * 3
    evaluated = [row for row in cells if row.get("status") == "evaluated"]
    assert len(evaluated) == 12, [row["cell"] for row in cells
                                  if row.get("status") != "evaluated"]
    for row in evaluated:
        assert sum(row["partition"].values()) == row["fill"]["candidates"], row["cell"]
        assert row["fill"]["contentful_candidates"] <= row["fill"]["candidates"]
    assert report["identity"]["zero_inference"]["model_calls"] == 0
    assert report["plate_ve_analysis"] is not None
    assert report["identity"]["evaluation_identity"]


@pytest.mark.skipif(not _ledger_available(), reason="out/ defteri yok (temiz klon)")
def test_fresh_interpreter_build_never_imports_the_vlm_stack():
    """Sıfır-inference iddiası **temiz süreçte** kanıtlanır: pytest süreci başka testlerden
    `llama` import etmiş olabilir; ölçüm karışmasın diye yeni yorumlayıcıda koşulur."""
    import subprocess
    program = (
        "import importlib.util, json, sys\n"
        f"spec = importlib.util.spec_from_file_location('t', {str(TOOL_PATH)!r})\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "report = module.build_report()\n"
        "print(json.dumps({'llama_imported': report['identity']['zero_inference']"
        "['llama_imported'], 'model_calls': report['identity']['zero_inference']"
        "['model_calls'], 'cells': len(report['cells'])}))\n")
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True,
                            check=True, cwd=ROOT)
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["llama_imported"] is False
    assert payload["model_calls"] == 0
    assert payload["cells"] == 12


def test_eval_tool_never_imports_the_vlm_stack():
    source = TOOL_PATH.read_text(encoding="utf-8")
    forbidden = ("from drawingto3d.llama", "import llama", "from drawingto3d.semantic_reader",
                 "from drawingto3d.semantic_candidate_reader")
    assert not any(token in source for token in forbidden)
