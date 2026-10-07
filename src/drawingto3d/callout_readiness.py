"""G8 — build readiness + per-callout audit (kök `PLAN.md` §14); G12.1 — disposition coverage.

The backend's `questions()` stays the authority: this does not replace it, it names *why* a build
waits, in the plan's own categories, per callout — and it carries the audit chain of every callout
(callout → raw text → parser version → semantic fields → target → geometry key → compiled decision,
and, once a build has run, the feature it produced).

G12.1 (PLAN-24 §10–§16) adds the *coverage* question the G11 run measured the absence of: a callout
whose candidate was blanket-ignored by the old bulk path must not quietly count as decided. Every
effective callout lands in exactly one bucket (`callout_coverage`), and three buckets block the
build on their own even though the compiler excludes those rows:

* `legacy_unclassified` — a pre-G12.1 `ignored`/`unbindable` row: never auto-promoted to a claim;
* `build_relevant_unsupported` — a real fact this version cannot apply; the honest stop;
* `invalid_duplicate` — a `redundant` claim whose citation is missing or stale.

Pure: it reads the session record and returns a picture. It never creates a confirmation, never
re-pins geometry and never drops a callout silently: a callout the user excluded (with an explicit
disposition) is reported as a declared exclusion, not as an issue.
"""
from __future__ import annotations

from drawingto3d import callout_bind, callout_compile, callout_models

CATEGORIES = ("missing_transcription", "parse_error", "parse_ambiguous", "missing_unit", "missing_target",
              "ambiguous_target", "stale_target", "unsupported_semantic", "callout_conflict",
              "missing_profile", "missing_view", "missing_calibration", "geometry_conflict",
              "unsupported_cad_feature",
              # G12.1 coverage categories (PLAN-24 §15/§16)
              "legacy_unclassified", "unsupported_build_relevant", "stale_duplicate_reference")

# --- G12.1 disposition coverage --------------------------------------------------------------

COVERAGE_BUCKETS = ("not_model_input", "redundant", "build_applied", "build_relevant_unsupported",
                    "unclassified", "legacy_unclassified", "stale", "compile_blocked", "invalid_duplicate")
"""Every effective callout lands in exactly one bucket (PLAN-24 §15).

`build_applied` = current transcription + current parse + current target + compiled decision, or a
decision the user already holds (`manual_decision_matches`). `unclassified`/`stale`/`compile_blocked`
are the machine-side waiting states the compiler already names; the other three are the new
disposition verdicts and are the ones that gate the build by themselves.
"""

COVERAGE_BLOCKING = ("unclassified", "legacy_unclassified", "stale", "compile_blocked",
                     "invalid_duplicate", "build_relevant_unsupported")
"""Buckets that keep `coverage_complete` false — each is either undecided or unapplied (never a claim)."""

# The decision vocab a `redundant` citation may name (`decision:<name>`): the fact already lives in
# one of the user's *own* decisions — this is what "represented by another explicit decision" means
# mechanically (PLAN-24 §15). Values are plain presence checks on the raw decisions dict.
DECISION_REFS = {
    "calibration": lambda decisions: decisions.get("calibration") is not None,
    "profile": lambda decisions: bool(decisions.get("profile_id")),
    "thickness": lambda decisions: decisions.get("thickness") is not None,
    "holes": lambda decisions: bool(decisions.get("holes")),
    "bindings": lambda decisions: bool(decisions.get("bindings")),
    "contour": lambda decisions: bool((decisions.get("contour") or {}).get("drop")
                                      or (decisions.get("contour") or {}).get("approve_join")),
    "view": lambda decisions: decisions.get("view") is not None,
    "trace": lambda decisions: bool(decisions.get("trace_acknowledged")),
}

_COMPILE_BLOCKED = ("missing_unit", "parse_ambiguous", "parse_unsupported", "unsupported_semantic",
                    "unsupported_cad_feature", "conflict", "view_not_confirmed", "stale_parse",
                    "stale_target", "missing_parse")


def decision_ref_present(decisions: dict, name: str) -> bool:
    """Is the decision a `decision:<name>` citation names actually present in this session?"""
    check = DECISION_REFS.get(str(name))
    return bool(check and check(decisions or {}))


def _state_stale(state: dict) -> bool:
    return any((state.get(layer) or {}).get("state") == "stale"
               for layer in ("transcription", "parse", "target"))


def callout_coverage(record: dict, *, compilation: dict | None = None) -> dict:
    """The per-callout decision-coverage picture of one session (pure — reads, writes nothing).

    Returns one list of callout ids per bucket plus `counts`, `coverage_complete` and the
    `unclassified`/`legacy_unclassified` bookkeeping the UI panel shows (PLAN-24 §15).
    """
    decisions = record.get("decisions") or {}
    effective = callout_models.effective_callouts(record)
    by_id = {row["id"]: row for row in effective}
    compilation = compilation if compilation is not None else callout_compile.compile_callouts(record)
    compile_rows = {row.get("callout_id"): row for row in compilation.get("rows") or []}
    states = {row["id"]: row for row in callout_models.callout_states(record)}

    buckets: dict[str, list[str]] = {name: [] for name in COVERAGE_BUCKETS}

    def state_for(callout_id: str) -> dict:
        return states.get(callout_id) or {}

    def covered_for_citation(callout_id: str, stack: frozenset) -> bool:
        """Can this callout be cited as 'the fact is already represented here'?"""
        if callout_id in stack:
            return False                                   # döngü: dayanak kendine kapanamaz
        row = by_id.get(callout_id)
        if row is None or _state_stale(state_for(callout_id)):
            return False
        disposition = row.get("disposition")
        if disposition == "not_model_input":
            return True
        if disposition == "redundant":
            return citation_ok(row, stack | {callout_id})
        if disposition == "build_relevant_unsupported":
            return False
        if row.get("ignored") or row.get("unbindable"):
            return False                                   # legacy: kanıtsız, dayanak olamaz
        return (compile_rows.get(callout_id) or {}).get("status") == "compiled"

    def citation_ok(row: dict, stack: frozenset) -> bool:
        reference = str(row.get("duplicate_of") or "")
        if reference.startswith(callout_models.DISPOSITION_DECISION_PREFIX):
            name = reference[len(callout_models.DISPOSITION_DECISION_PREFIX):]
            return decision_ref_present(decisions, name)
        return covered_for_citation(reference, stack | {row["id"]})

    for row in effective:
        callout_id = row["id"]
        disposition = row.get("disposition")
        if disposition == "build_relevant_unsupported":
            buckets["build_relevant_unsupported"].append(callout_id)
            continue
        if disposition == "not_model_input":
            buckets["not_model_input"].append(callout_id)
            continue
        if disposition == "redundant":
            (buckets["redundant"] if citation_ok(row, frozenset()) else buckets["invalid_duplicate"]
             ).append(callout_id)
            continue
        if row.get("ignored") or row.get("unbindable"):
            # Pre-G12.1 rows: the flag is real, the *claim* was never made.
            buckets["legacy_unclassified"].append(callout_id)
            continue
        if _state_stale(state_for(callout_id)):
            buckets["stale"].append(callout_id)
            continue
        status = (compile_rows.get(callout_id) or {}).get("status")
        if status == "compiled":
            buckets["build_applied"].append(callout_id)
        elif status in _COMPILE_BLOCKED:
            buckets["compile_blocked"].append(callout_id)
        else:
            buckets["unclassified"].append(callout_id)

    counts = {name: len(rows) for name, rows in buckets.items()}
    return {"total": len(effective), **buckets, "counts": counts,
            "coverage_complete": all(counts[name] == 0 for name in COVERAGE_BLOCKING)}


def coverage_issues(coverage: dict, record: dict) -> list[dict]:
    """The coverage buckets the compiler cannot see, as readiness issues (PLAN-24 §16)."""
    by_id = {row["id"]: row for row in callout_models.effective_callouts(record)}
    issues: list[dict] = []
    for callout_id in coverage.get("legacy_unclassified") or []:
        issues.append({"category": "legacy_unclassified", "callout_id": callout_id,
                       "action": "review_callout", "reason": "legacy_unclassified",
                       "detail": "Eski 'yok sayıldı/bağlanamaz' kaydı yeni sözleşmede kanıtsız."})
    for callout_id in coverage.get("build_relevant_unsupported") or []:
        reason = (by_id.get(callout_id) or {}).get("disposition_reason")
        issues.append({"category": "unsupported_build_relevant", "callout_id": callout_id,
                       "action": "review_callout", "reason": "build_relevant_unsupported",
                       "detail": reason or "gerçek ölçü/not bu sürümde uygulanamıyor"})
    for callout_id in coverage.get("invalid_duplicate") or []:
        reference = (by_id.get(callout_id) or {}).get("duplicate_of")
        issues.append({"category": "stale_duplicate_reference", "callout_id": callout_id,
                       "action": "review_callout", "reason": "invalid_duplicate",
                       "detail": str(reference or "")})
    return issues


# status (compiler row) → (category, action) — the interface's button, in machine form
_STATUS = {
    "missing_transcription": ("missing_transcription", "transcribe"),
    "missing_parse": ("parse_error", "edit_transcription"),
    "stale_parse": ("parse_error", "edit_transcription"),
    "parse_ambiguous": ("parse_ambiguous", "edit_transcription"),
    "parse_unsupported": ("parse_error", "edit_transcription"),
    "missing_unit": ("missing_unit", "edit_transcription"),
    "missing_target": ("missing_target", "confirm_target"),
    "stale_target": ("stale_target", "confirm_target"),
    "unsupported_semantic": ("unsupported_semantic", "review_callout"),
    "unsupported_cad_feature": ("unsupported_cad_feature", "review_callout"),
    "conflict": ("callout_conflict", "review_conflict"),
    # R01 (review): a linear tie with no vouchable view is an open *view* decision, not a broken
    # callout — the category is the sheet's, and the action names the step that answers it.
    "view_not_confirmed": ("missing_view", "confirm_view"),
}

_QUESTION = {
    "missing_transcription": "«{id}» için callout metnini yazın.",
    "parse_error": "«{id}» okuması güncel değil ({reason}): metni yeniden yazıp kaydedin.",
    "parse_ambiguous": "«{id}» metni birden fazla okumaya izin veriyor: netleştirin.",
    "missing_unit": "«{id}» ölçüsünde birim yok: metne mm (ya da inç) yazın veya kalibrasyonda sayfanın birimini seçin.",
    "missing_target": "«{id}» için hedef geometri onaylanmadı.",
    "ambiguous_target": "«{id}» için birden fazla eş olasılıklı hedef var: hangisi olduğunu seçin.",
    "stale_target": "«{id}» hedefi eskidi ({reason}): yeniden onaylayın.",
    "unsupported_semantic": "«{id}» bu sürümde karara derlenmiyor: {reason}.",
    "unsupported_cad_feature": "«{id}» için CAD özelliği bu sürümde yok: {reason}.",
    "callout_conflict": "«{id}» kararı çelişiyor: {reason}.",
    "missing_profile": "Ana görünüşte dış konturu seçin.",
    "missing_calibration": "Bilinen ölçünün iki noktasını ve uzunluğunu belirtin.",
    "missing_view": "{reason}",
    "geometry_conflict": "{reason}",
    # G12.1 kapsam kategorileri (PLAN-24 §13/§16; PLAN-25 §18 copy'si birebir).
    "legacy_unclassified": "«{id}» bu alan eski oturumda kapsam dışı bırakılmış; nedenini yeniden seçin "
                           "(modele ait değil / zaten başka bir ölçüyle temsil ediliyor / gerçek ölçü "
                           "ama bu sürüm uygulayamıyor).",
    "unsupported_build_relevant": "«{id}» bu gerçek ölçü/not mevcut modelleme yetenekleriyle "
                                  "uygulanamıyor ({reason}).",
    "stale_duplicate_reference": "«{id}» bu bilgi için seçilen dayanak («{reason}») artık güncel değil.",
}


def _detail_for(compilation: dict, callout_id: str, category: str, reason) -> str:
    for row in compilation.get("unsupported") or []:
        if row.get("callout_id") == callout_id and row.get("reason") == reason:
            return str(row.get("detail") or reason or "")
    for row in compilation.get("conflicts") or []:
        if row.get("callout_id") == callout_id:
            return str(row.get("detail") or reason or "")
    return str(reason or "")


def build_readiness(record: dict, *, sheet_issues: list[dict] | None = None,
                    feature_ids: dict[str, list[str]] | None = None) -> dict:
    """The G8 picture: per-callout issues in the plan's categories, plus the audit rows."""
    compilation = callout_compile.compile_callouts(record)
    issues: list[dict] = []
    for row in compilation.get("rows") or []:
        status = row.get("status")
        if status in (None, "compiled", "excluded"):
            continue
        category, action = _STATUS.get(status, ("parse_error", "edit_transcription"))
        callout_id = row.get("callout_id")
        detail = _detail_for(compilation, callout_id, category, row.get("reason"))
        if category == "missing_target":
            # Equal-strength proposals are not an answer: the user still has to choose (G5 → G6).
            proposals = callout_bind.propose_targets(record, callout_id)
            if len(proposals) > 1:
                category, action = "ambiguous_target", "confirm_target"
        issues.append({"category": category, "callout_id": callout_id, "action": action,
                       "reason": row.get("reason"), "detail": detail})
    for issue in sheet_issues or []:
        category = issue.get("category") if issue.get("category") in CATEGORIES else "geometry_conflict"
        issues.append({"category": category, "callout_id": issue.get("callout_id"),
                       "action": issue.get("action", "sheet_question"),
                       "reason": issue.get("reason"), "detail": issue.get("detail")})

    # G12.1 (PLAN-24 §16): the coverage audit is part of readiness — a legacy bulk ignore, a real
    # fact this version cannot apply, or a redundant claim whose dayanak is gone all block the
    # build here, even though the compiler excludes those rows from its own chain.
    coverage = callout_coverage(record, compilation=compilation)
    issues.extend(coverage_issues(coverage, record))

    excluded = [{"callout_id": row.get("callout_id"), "reason": row.get("reason")}
                for row in compilation.get("excluded") or []]
    questions = []
    for issue in issues:
        template = _QUESTION.get(issue["category"], "{reason}")
        questions.append({"category": issue["category"], "callout_id": issue.get("callout_id"),
                          "action": issue.get("action"), "reason": issue.get("reason"),
                          "text": template.format(id=issue.get("callout_id") or "",
                                                  reason=issue.get("detail") or issue.get("reason") or "")})
    counts: dict[str, int] = {}
    for issue in issues:
        counts[issue["category"]] = counts.get(issue["category"], 0) + 1
    return {"ready": not questions,
            "questions": questions,
            "issues": issues,
            "categories": counts,
            "excluded": excluded,
            "coverage": coverage,
            "compiled": callout_compile.compiled_summary(compilation),
            "rows": callout_compile.compile_provenance(compilation, feature_ids),
            "geometry_key": compilation.get("geometry_key"),
            "geometry_version": compilation.get("geometry_version")}


def readiness_questions(readiness: dict) -> list[str]:
    """The same picture as the question texts a user reads (order preserved)."""
    return [row["text"] for row in readiness.get("questions") or []]


__all__ = ["CATEGORIES", "COVERAGE_BUCKETS", "COVERAGE_BLOCKING", "DECISION_REFS",
           "build_readiness", "callout_coverage", "coverage_issues", "decision_ref_present",
           "readiness_questions"]
