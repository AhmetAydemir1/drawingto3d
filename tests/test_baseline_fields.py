"""Baseline satırının altı alanı: her biri kendi kanıtından, cümleden değil.

S03'ün kabulü "komut çalıştı" ile "model çağrıldı"yı ayırmak ve görüntünün gidip gitmediğini iddia
değil kayıt olarak istemekti. Bu test, alanların kaynaksız bir satırda uydurulmadığını (kanıt yoksa
`null`), sıfır çağrılı bir kaydın ise `false` yazdığını doğrular.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location("lab_baseline", ROOT / "eval" / "lab_baseline.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lab_baseline"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _log(path: Path, calls: int, *, image_sent: bool = False, model: str = "qwen2.5-coder:7b") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    detail = [{"index": index + 1, "kind": "coder", "at": "2026-09-29T00:00:00+0000",
               "image_sent": image_sent, "image_bytes": 0, "prompt_chars": 100, "ok": True,
               "error": None} for index in range(calls)]
    path.write_text(json.dumps({"schema": "drawingto3d.inference-log/1", "note": "", "calls": calls,
                                "inference_called": calls > 0, "image_sent": image_sent,
                                "kinds": ["coder"] if calls else [],
                                "models": {"coder": {"kind": "coder", "model": model}} if calls else {},
                                "calls_detail": detail}), encoding="utf-8")


def test_a_row_without_a_call_log_reports_no_evidence_rather_than_no_calls(tmp_path):
    """Kanıt dosyası yoksa alan `null`: "ölçülmedi" ile "çağrılmadı" aynı şey değil."""
    module = load_module()
    product = tmp_path / "product"
    product.mkdir(parents=True)

    fields = module._fields_from_disk(tmp_path, {"part_id": "p", "kind": "vector"},
                                      [{"command": ["propose"]}], [], None, None, None, tmp_path)

    assert fields["command_started"] is True
    assert fields["inference_called"] is None and fields["image_sent"] is None
    assert fields["inference_log"] is None
    assert fields["step_built"] is False and fields["evaluated"] is False


def test_a_zero_call_log_measures_that_no_model_was_asked(tmp_path):
    """Sıfır çağrılı kayıt `false` yazar: "model çağrılmadı" artık bir ölçüm."""
    module = load_module()
    (tmp_path / "product").mkdir(parents=True)
    _log(tmp_path / "product" / "inference-log.json", 0)

    fields = module._fields_from_disk(tmp_path, {"part_id": "p", "kind": "vector"}, [{}], [], None, None,
                                      None, tmp_path)

    assert fields["inference_called"] is False and fields["image_sent"] is False
    assert fields["inference_log"].endswith("product/inference-log.json")


def test_a_call_log_carries_the_model_and_whether_an_image_went(tmp_path):
    module = load_module()
    (tmp_path / "product").mkdir(parents=True)
    _log(tmp_path / "product" / "inference-log.json", 3, image_sent=False)

    fields = module._fields_from_disk(tmp_path, {"part_id": "p", "kind": "raster"}, [{}], [], None, None,
                                      None, tmp_path)

    assert fields["inference_called"] is True
    assert fields["image_sent"] is False, "görüntü gitmediyse gitmiş gibi yazılmamalı"
    assert fields["arms"]["product"]["models"]["coder"]["model"] == "qwen2.5-coder:7b"
    assert "serbest kod" in fields["arms"]["product"]["pipeline"], \
        "raster kolu yapılandırılmış ürün yolu gibi adlandırılmamalı"


def test_the_summary_keeps_attempts_and_distinct_parts_apart():
    """Beş satırın dördü ayrı parça: paydalar ayrı yazılmalı, kol başına da ayrı."""
    module = load_module()
    rows = [
        {"part_id": "a", "error_class": "kısıt/kalibrasyon", "evaluator": None, "product_step": None,
         "product_refusals": ["x"], "command_started": True, "inference_called": False,
         "image_sent": False, "plan_produced": False, "step_built": False, "evaluated": False,
         "arms": {"model": {"ran": False}}},
        {"part_id": "a", "error_class": "CAD işlemi", "evaluator": None, "product_step": None,
         "product_refusals": [], "command_started": True, "inference_called": True, "image_sent": False,
         "plan_produced": True, "step_built": False, "evaluated": False,
         "arms": {"model": {"ran": True, "inference_called": True, "plan_produced": False}}},
        {"part_id": "b", "error_class": "kısıt/kalibrasyon", "evaluator": None, "product_step": None,
         "product_refusals": [], "command_started": True, "inference_called": None, "image_sent": None,
         "plan_produced": False, "step_built": False, "evaluated": False, "arms": {}},
    ]
    summary = module._summary(rows)

    assert summary["attempt_count"] == 3 and summary["unique_part_count"] == 2
    assert summary["arms"]["product"]["inference_called"] == 1
    assert summary["arms"]["product"]["inference_log_missing"] == 1, \
        "kayıtsız satır ölçülmemiş sayılmalı, model kullanmamış gibi değil"
    assert summary["arms"]["model"]["ran"] == 1
