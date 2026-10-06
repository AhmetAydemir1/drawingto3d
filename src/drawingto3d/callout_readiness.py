"""G8 — build readiness + per-callout audit (kök `PLAN.md` §14).

The backend's `questions()` stays the authority: this does not replace it, it names *why* a build
waits, in the plan's own categories, per callout — and it carries the audit chain of every callout
(callout → raw text → parser version → semantic fields → target → geometry key → compiled decision,
and, once a build has run, the feature it produced).

Pure: it reads the session record and returns a picture. It never creates a confirmation, never
re-pins geometry and never drops a callout silently: a callout the user excluded (ignored or
declared unbindable) is reported as a declared exclusion, not as an issue.
"""
from __future__ import annotations

from drawingto3d import callout_bind, callout_compile

CATEGORIES = ("missing_transcription", "parse_error", "parse_ambiguous", "missing_unit", "missing_target",
              "ambiguous_target", "stale_target", "unsupported_semantic", "callout_conflict",
              "missing_profile", "missing_view", "missing_calibration", "geometry_conflict",
              "unsupported_cad_feature")

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
            "compiled": callout_compile.compiled_summary(compilation),
            "rows": callout_compile.compile_provenance(compilation, feature_ids),
            "geometry_key": compilation.get("geometry_key"),
            "geometry_version": compilation.get("geometry_version")}


def readiness_questions(readiness: dict) -> list[str]:
    """The same picture as the question texts a user reads (order preserved)."""
    return [row["text"] for row in readiness.get("questions") or []]


__all__ = ["CATEGORIES", "build_readiness", "readiness_questions"]
