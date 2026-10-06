"""SEMREAD-001D — experiment skeleton (PLAN-19 §38 / devam zinciri): plan izleme + bütçe deklarasyonu.

Kapsam:

* `docs/PLAN-19.md` bayt kopya olarak izleniyor ve sha256'sı burada pinli (PLAN-19 başlığı:
  "Static preflight yeşil sonrası: Round 1 → offline semantic evaluation → tek karar noktası";
  §38: bu plan repo authority yapılacaksa `docs/PLAN-19.md` olarak **yeni history entry** tercih
  edilir ve **PLAN-18 overwrite edilmez**). Taslak kendi slotunu zaten PLAN-19 diye beyan ediyordu
  ve o slot boştu; §38'in "yeni history entry + eskiyi rewrite etme + SHA/pin zinciri korunur"
  kuralı gereği numara verildi: PLAN-18 **rewrite edilmedi** ve son izlenen revizyonuyla
  (`ec49e985…`) geçmişte donar — değişmemesi burada denetlenir; PLAN-17 (`1bdd4987…`), PLAN-16
  (`73f81009…`), PLAN-15 (`909e46cb…`), PLAN-14 (`39cf9b84…`; daha önce `a027cb4a…`,
  `f2d249b7…`) de geçmişte durur;
* pilot bütçe tavanları 001D'nin deklare bütçesine sabit (dev 12 / final 20 / toplam 32 —
  PLAN-19 §7'de `0/12`, `0/20` olarak deklare);
* 001D handoff açık ve 001C'nin READ-ONLY kapandığını kaydediyor;
* kök `report.md` aktif-plan pointer'ı PLAN-19'a çevrildi.

Bu testler çağrı yapmaz; yalnız skeleton kayıtlarını denetler.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "PLAN-19.md"
# Plan izleme (§38 işinin dayanağı): "Static preflight yeşil sonrası: Round 1 → offline semantic
# evaluation → tek karar noktası" planı — bayt kopya. PLAN-18 rewrite edilmedi; izlenen revizyon
# zinciri git history'de pinli (ec49e985…, 1bdd4987…, 73f81009…, 909e46cb…, 39cf9b84…, a027cb4a…,
# f2d249b7…); sha bilinçli olarak elle pinlenir (revizyon sessizce geçmesin).
PLAN_SHA256 = "d2148cb94955e5ed5d7651fc70dbe3be4dad6ea894bcfaaa4319efe023142381"
PLAN_18_SHA256 = "ec49e985671b59e0b8450d1f9b004971717df8f34fef5b0d044b3031f04c0477"
PLAN_17_SHA256 = "1bdd49873d5375196da6dd3e072e59299534e2676cefc44177ee7358ea0b9546"
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
    assert PLAN.exists(), "docs/PLAN-19.md izlenmeli (bayt kopya)"
    digest = hashlib.sha256(PLAN.read_bytes()).hexdigest()
    assert digest == PLAN_SHA256


def test_plan18_history_is_preserved():
    """PLAN-19 §38: PLAN-18 rewrite edilmez — dosya son izlenen revizyonuyla donar."""
    history = ROOT / "docs" / "PLAN-18.md"
    assert history.exists(), "PLAN-18 geçmiş olarak korunmalı (§38)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_18_SHA256, \
        "PLAN-18 son izlenen revizyonu olarak donmalı"


def test_plan17_history_is_preserved():
    """PLAN-19 §38 zinciri: PLAN-17 rewrite edilmez — dosya son izlenen revizyonuyla donar."""
    history = ROOT / "docs" / "PLAN-17.md"
    assert history.exists(), "PLAN-17 geçmiş olarak korunmalı (§38)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_17_SHA256, \
        "PLAN-17 son izlenen revizyonu olarak donmalı"


def test_plan16_history_is_preserved():
    """PLAN-19 §38 zinciri: PLAN-16 rewrite edilmez — dosya son izlenen revizyonuyla donar."""
    history = ROOT / "docs" / "PLAN-16.md"
    assert history.exists(), "PLAN-16 geçmiş olarak korunmalı (§38)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_16_SHA256, \
        "PLAN-16 son izlenen revizyonu olarak donmalı"


def test_plan15_history_is_preserved():
    """PLAN-19 §38 zinciri: PLAN-15 rewrite edilmez — dosya son izlenen revizyonuyla donar."""
    history = ROOT / "docs" / "PLAN-15.md"
    assert history.exists(), "PLAN-15 geçmiş olarak korunmalı (§38)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_15_SHA256, \
        "PLAN-15 son izlenen revizyonu olarak donmalı"


def test_plan14_history_is_preserved():
    """PLAN-19 §38 zinciri: PLAN-14 geçmiş olarak korunur — dosya silinmez, byte'ı değişmez."""
    history = ROOT / "docs" / "PLAN-14.md"
    assert history.exists(), "PLAN-14 geçmiş olarak korunmalı (§38)"
    assert hashlib.sha256(history.read_bytes()).hexdigest() == PLAN_14_SHA256, \
        "PLAN-14 son izlenen revizyonu olarak donmalı"


def test_declared_budget_is_dev_12_final_20_total_32():
    assert pilot.LIVE_CALL_LIMIT_DEV == 12
    assert pilot.LIVE_CALL_LIMIT_FINAL == 20
    assert pilot.LIVE_CALL_LIMIT_TOTAL == 32
    assert pilot.PHASE_LIMITS == {"dev": 12, "final": 20}


def test_handoff_opened_and_records_the_001c_closure():
    text = HANDOFF.read_text(encoding="utf-8")
    assert "PLAN-19" in text
    assert "SEMREAD-001D" in text
    assert "READ-ONLY" in text
    assert PLAN_SHA256[:12] in text
    # PLAN-19 §38: PLAN-18 (+ PLAN-17, PLAN-16, PLAN-15, PLAN-14) geçmiş kaydı handoff'ta görünür
    # kalır.
    assert "PLAN-18" in text
    assert "ec49e985" in text
    assert "PLAN-17" in text
    assert "1bdd4987" in text
    assert "PLAN-16" in text
    assert "73f81009" in text
    assert "PLAN-15" in text
    assert "909e46cb" in text
    assert "PLAN-14" in text


def test_report_points_to_the_active_plan():
    text = (ROOT / "report.md").read_text(encoding="utf-8")
    assert "docs/PLAN-19.md" in text
    assert PLAN_SHA256[:8] in text
