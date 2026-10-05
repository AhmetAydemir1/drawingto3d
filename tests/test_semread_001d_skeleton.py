"""SEMREAD-001D — experiment skeleton (PLAN-15 §31 / §48): plan izleme + bütçe deklarasyonu.

Kapsam:

* `docs/PLAN-15.md` bayt kopya olarak izleniyor ve sha256'sı burada pinli (PLAN-15 §48: yeni
  history entry); PLAN-14 dosyası son izlenen revizyonuyla (`39cf9b84…`; daha önce `a027cb4a…`,
  `f2d249b7…`) **geçmiş olarak** korunur ve değişmemesi burada da denetlenir;
* pilot bütçe tavanları 001D'nin deklare bütçesine sabit (dev 12 / final 20 / toplam 32 — §31);
* 001D handoff açık ve 001C'nin READ-ONLY kapandığını kaydediyor;
* kök `report.md` aktif-plan pointer'ı PLAN-15'e çevrildi.

Bu testler çağrı yapmaz; yalnız skeleton kayıtlarını denetler.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "PLAN-15.md"
# Plan izleme (§60/§61 işinin dayanağı): "`/3` prompt/schema sonrası: 001D producer identity →
# dev-report → static preflight → Round 1 semantic proof" planı — bayt kopya. Önceki takip edilen
# revizyonlar (39cf9b84…, a027cb4a…, f2d249b7…) docs/PLAN-14.md olarak git history'de; sha
# bilinçli olarak elle pinlenir (revizyon sessizce geçmesin).
PLAN_SHA256 = "909e46cb67aac205b0e270861a364ad79e69eaa2a1b74aa8cf2a4d572109144e"
PLAN_14_SHA256 = "39cf9b8483f5cbfa03e0683cebcea4dba7d47dc68a0867b8da76057e7aaf088d"
HANDOFF = ROOT / "docs" / "HERMES_SEMREAD_001D_HANDOFF.md"


def _load_pilot():
    module_path = ROOT / "eval" / "semread_001b_pilot.py"
    spec = importlib.util.spec_from_file_location("semread_001d_skeleton_pilot", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pilot = _load_pilot()


def test_plan_is_tracked_as_a_pinned_byte_copy():
    assert PLAN.exists(), "docs/PLAN-15.md izlenmeli (bayt kopya)"
    digest = hashlib.sha256(PLAN.read_bytes()).hexdigest()
    assert digest == PLAN_SHA256


def test_plan14_history_is_preserved():
    """PLAN-15 §48: PLAN-14 geçmiş olarak korunur — dosya silinmez, byte'ı değişmez."""
    history = ROOT / "docs" / "PLAN-14.md"
    assert history.exists(), "PLAN-14 geçmiş olarak korunmalı (§48)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_14_SHA256, \
        "PLAN-14 son izlenen revizyonu olarak donmalı"


def test_declared_budget_is_dev_12_final_20_total_32():
    assert pilot.LIVE_CALL_LIMIT_DEV == 12
    assert pilot.LIVE_CALL_LIMIT_FINAL == 20
    assert pilot.LIVE_CALL_LIMIT_TOTAL == 32
    assert pilot.PHASE_LIMITS == {"dev": 12, "final": 20}


def test_handoff_opened_and_records_the_001c_closure():
    text = HANDOFF.read_text(encoding="utf-8")
    assert "PLAN-15" in text
    assert "SEMREAD-001D" in text
    assert "READ-ONLY" in text
    assert PLAN_SHA256[:12] in text
    # PLAN-15 §48: PLAN-14 geçmiş kaydı handoff'ta görünür kalır.
    assert "PLAN-14" in text


def test_report_points_to_the_active_plan():
    text = (ROOT / "report.md").read_text(encoding="utf-8")
    assert "docs/PLAN-15.md" in text
    assert PLAN_SHA256[:8] in text
