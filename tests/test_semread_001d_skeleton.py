"""SEMREAD-001D — experiment skeleton (PLAN-17 §4 / devam zinciri): plan izleme + bütçe deklarasyonu.

Kapsam:

* `docs/PLAN-17.md` bayt kopya olarak izleniyor ve sha256'sı burada pinli (PLAN-17 §4: yeni
  history entry — "`001d/1` producer identity sonrası: dev-report → 001D dev input kurulumu →
  static preflight → Round 1 semantic proof"). Taslak kendi slotunu PLAN-16 diye beyan ediyordu,
  ama o slot b2e1218'de doldu; §4'ün "yeni history entry + eskiyi rewrite etme + SHA/pin zinciri
  korunur" kuralı gereği sıradaki serbest numara verildi: PLAN-16 **rewrite edilmedi** ve son
  izlenen revizyonuyla (`73f81009…`) geçmişte donar — değişmemesi burada denetlenir; PLAN-15
  (`909e46cb…`; daha önce PLAN-14 `39cf9b84…`, `a027cb4a…`, `f2d249b7…`) de geçmişte durur;
* pilot bütçe tavanları 001D'nin deklare bütçesine sabit (dev 12 / final 20 / toplam 32 —
  PLAN-17 başlığında `0/12`, `0/20`, `0/32` olarak deklare);
* 001D handoff açık ve 001C'nin READ-ONLY kapandığını kaydediyor;
* kök `report.md` aktif-plan pointer'ı PLAN-17'ye çevrildi.

Bu testler çağrı yapmaz; yalnız skeleton kayıtlarını denetler.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "PLAN-17.md"
# Plan izleme (§4 işinin dayanağı): "`001d/1` producer identity sonrası: dev-report → 001D dev
# input kurulumu → static preflight → Round 1 semantic proof" planı — bayt kopya. PLAN-16 rewrite
# edilmedi; izlenen revizyon zinciri git history'de pinli (73f81009…, 909e46cb…, 39cf9b84…,
# a027cb4a…, f2d249b7…); sha bilinçli olarak elle pinlenir (revizyon sessizce geçmesin).
PLAN_SHA256 = "1bdd49873d5375196da6dd3e072e59299534e2676cefc44177ee7358ea0b9546"
PLAN_16_SHA256 = "73f81009dfad29eed1eca73090e3c94a2ade6e10635677a738e3a64f7b9ea437"
PLAN_15_SHA256 = "909e46cb67aac205b0e270861a364ad79e69eaa2a1b74aa8cf2a4d572109144e"
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
    assert PLAN.exists(), "docs/PLAN-16.md izlenmeli (bayt kopya)"
    digest = hashlib.sha256(PLAN.read_bytes()).hexdigest()
    assert digest == PLAN_SHA256


def test_plan16_history_is_preserved():
    """PLAN-17 §4: PLAN-16 rewrite edilmez — dosya son izlenen revizyonuyla donar."""
    history = ROOT / "docs" / "PLAN-16.md"
    assert history.exists(), "PLAN-16 geçmiş olarak korunmalı (§4)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_16_SHA256, \
        "PLAN-16 son izlenen revizyonu olarak donmalı"


def test_plan15_history_is_preserved():
    """PLAN-17 §4 zinciri: PLAN-15 rewrite edilmez — dosya son izlenen revizyonuyla donar."""
    history = ROOT / "docs" / "PLAN-15.md"
    assert history.exists(), "PLAN-15 geçmiş olarak korunmalı (§4)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_15_SHA256, \
        "PLAN-15 son izlenen revizyonu olarak donmalı"


def test_plan14_history_is_preserved():
    """PLAN-17 §4 zinciri: PLAN-14 geçmiş olarak korunur — dosya silinmez, byte'ı değişmez."""
    history = ROOT / "docs" / "PLAN-14.md"
    assert history.exists(), "PLAN-14 geçmiş olarak korunmalı (§4)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_14_SHA256, \
        "PLAN-14 son izlenen revizyonu olarak donmalı"


def test_declared_budget_is_dev_12_final_20_total_32():
    assert pilot.LIVE_CALL_LIMIT_DEV == 12
    assert pilot.LIVE_CALL_LIMIT_FINAL == 20
    assert pilot.LIVE_CALL_LIMIT_TOTAL == 32
    assert pilot.PHASE_LIMITS == {"dev": 12, "final": 20}


def test_handoff_opened_and_records_the_001c_closure():
    text = HANDOFF.read_text(encoding="utf-8")
    assert "PLAN-17" in text
    assert "SEMREAD-001D" in text
    assert "READ-ONLY" in text
    assert PLAN_SHA256[:12] in text
    # PLAN-17 §4: PLAN-16 (+ PLAN-15, PLAN-14) geçmiş kaydı handoff'ta görünür kalır.
    assert "PLAN-16" in text
    assert "73f81009" in text
    assert "PLAN-15" in text
    assert "909e46cb" in text
    assert "PLAN-14" in text


def test_report_points_to_the_active_plan():
    text = (ROOT / "report.md").read_text(encoding="utf-8")
    assert "docs/PLAN-17.md" in text
    assert PLAN_SHA256[:8] in text
