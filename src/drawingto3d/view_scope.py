"""Which drawing view owns which geometry, and which view may feed the solid (PLAN-25 §46–§54).

The candidates are the segmenter's own boxes (`views.segment_views`), persisted once with the
session: a reopen never re-runs the segmenter, only a reader/geometry migration re-reads (§46).

Ownership is decided here by containment alone — a geometry that fits inside exactly one candidate
is that candidate's, and anything straddling a border or sitting outside every box stays `None`
(§48). There is no nearest-view guess: an ambiguous contour is the user's to resolve, never the
closest box's.

An *unowned* contour is not a conflict of its own: it is a geometry whose view relation was never
established, while §52 refuses geometry that belongs to a *different* view than the confirmed
source. So the build gate fires on ownership that disagrees with the user's own decisions — a
contour owned by a reference/ignored view, by a picture, or by a view other than the confirmed
primary — and leaves an unowned contour to build exactly as it did before this layer existed.

The roles (`primary`, `plan`, `side`, `section`, `isometric_ignore`, `unused`) are the user's own
decision (§47/§51). The solid's source in this version is the *primary* view — and with no
confirmation yet, a candidate the segmenter called a picture (isometric) is not a source either
(§52/§53): nothing here infers a build from a drawn picture.
"""

from __future__ import annotations

CATEGORY = "view_scope_conflict"
"""The readiness category the build's own waiting state reports under (PLAN-25 §52)."""

COVERAGE = 0.95
"""How much of a geometry's own box must fall inside one candidate to count as 'strongly inside'."""

ROLES = ("primary", "plan", "side", "section", "isometric_ignore", "unused")
SOLID_ROLE = "primary"
"""V1 builds the extrude from the primary view only (§52); the other roles are reference."""

ROLE_LABELS = {"primary": "Ana görünüş", "plan": "Üst görünüş", "side": "Yan görünüş",
               "section": "Kesit", "isometric_ignore": "İzometrik (üretim kaynağı değil)",
               "unused": "Kullanılmıyor"}


def category() -> str:
    return CATEGORY


def candidate_labels(candidates: list[dict]) -> dict[str, str]:
    """One label per candidate — a *candidate* name, never a claim about the drawing (§51).

    Orthographic/unknown candidates are numbered in the segmenter's own order (`Görünüş 1`,
    `Görünüş 2`, …); a hatched candidate is `Kesit adayı` and a picture is `İzometrik adayı`.
    """
    labels: dict[str, str] = {}
    ortho = 0
    for row in candidates:
        kind = str(row.get("kind") or "unknown")
        if kind == "section":
            labels[row["id"]] = "Kesit adayı"
        elif kind == "isometric":
            labels[row["id"]] = "İzometrik adayı"
        else:
            ortho += 1
            labels[row["id"]] = f"Görünüş {ortho}"
    return labels


def geometry_bbox(row: dict) -> tuple[float, float, float, float] | None:
    """The geometry's own box, from whatever shape the reader gave it (points / edges / circle)."""
    xs: list[float] = []
    ys: list[float] = []

    def keep(x, y):
        xs.append(float(x))
        ys.append(float(y))

    for point in row.get("points") or []:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            keep(point[0], point[1])
    for edge in row.get("edges") or []:
        for key in ("start", "end"):
            point = edge.get(key)
            if isinstance(point, (list, tuple)) and len(point) >= 2:
                keep(point[0], point[1])
        center, radius = edge.get("center"), edge.get("radius")
        if isinstance(center, (list, tuple)) and len(center) >= 2 and radius:
            keep(float(center[0]) - float(radius), float(center[1]) - float(radius))
            keep(float(center[0]) + float(radius), float(center[1]) + float(radius))
    circle = row.get("circle") or (row if "center" in row and "radius" in row else None)
    if isinstance(circle, dict):
        center, radius = circle.get("center"), circle.get("radius")
        if isinstance(center, (list, tuple)) and len(center) >= 2 and radius:
            keep(float(center[0]) - float(radius), float(center[1]) - float(radius))
            keep(float(center[0]) + float(radius), float(center[1]) + float(radius))
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _candidate_box(row: dict) -> tuple[float, float, float, float]:
    box = row.get("bbox") or {}
    x, y = float(box.get("x", 0.0)), float(box.get("y", 0.0))
    return x, y, x + float(box.get("w", 0.0)), y + float(box.get("h", 0.0))


def _coverage(inner: tuple[float, float, float, float], outer: tuple[float, float, float, float]) -> float:
    ix0, iy0 = max(inner[0], outer[0]), max(inner[1], outer[1])
    ix1, iy1 = min(inner[2], outer[2]), min(inner[3], outer[3])
    intersection = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    area = max(1e-9, (inner[2] - inner[0]) * (inner[3] - inner[1]))
    return intersection / area


def assign_view_ids(options: dict, candidates: list[dict]) -> dict[str, int]:
    """Annotate every profile/circle with the one candidate that owns it (§48). Returns counts.

    A profile owns its whole contour — its edges and primitives ride with it; a circle is its own
    row. `view_id` is always written (a candidate id or an explicit `None`), so "no owner" is a
    recorded fact rather than a missing key.
    """
    boxes = [(row["id"], _candidate_box(row)) for row in candidates]
    counts = {row["id"]: 0 for row in candidates}
    counts["unowned"] = 0
    for row in (options.get("profiles") or []) + (options.get("circles") or []):
        box = geometry_bbox(row)
        owner = None
        if box is not None:
            inside = [vid for vid, candidate in boxes if _coverage(box, candidate) >= COVERAGE]
            owner = inside[0] if len(inside) == 1 else None
        row["view_id"] = owner
        counts[owner if owner else "unowned"] += 1
    return counts


def _role_rows(record: dict) -> dict[str, str | None]:
    return {row.get("view_id"): row.get("role")
            for row in ((record.get("decisions") or {}).get("drawing_views") or [])
            if isinstance(row, dict) and row.get("view_id")}


def _stale_role(record: dict) -> dict | None:
    """A role decision stamped against another geometry version asks again (§47/§49).

    The stamp is the server's own; a reader/geometry migration moves the record on, and a role the
    user approved against the old read must not silently keep steering the build.
    """
    current = record.get("geometry_version")
    if current is None:
        return None
    for row in ((record.get("decisions") or {}).get("drawing_views") or []):
        if not isinstance(row, dict) or not row.get("view_id"):
            continue
        stamped = row.get("geometry_version")
        if stamped is not None and int(stamped) != int(current):
            return row
    return None


def conflict(record: dict) -> dict | None:
    """Why the selected contour cannot be this build's solid source — or `None` when it can.

    With no candidate list at all (a pre-segmenter session) there is no view layer to enforce and the
    record keeps building as before; with no contour chosen yet there is nothing to judge. Everything
    else is named: unowned/ambiguity, a picture's candidate, a role that is not the solid's source,
    and a contour that lies in a different view than the one the user confirmed as primary.
    """
    decisions = record.get("decisions") or {}
    candidates = record.get("view_candidates") or []
    if not candidates:
        return None
    profile_id = decisions.get("profile_id")
    if not profile_id:
        return None
    options = record.get("options") or {}
    profile = next((row for row in options.get("profiles") or [] if row.get("id") == profile_id), None)
    if profile is None:
        return None
    view_id = profile.get("view_id")
    by_id = {row["id"]: row for row in candidates}
    labels = candidate_labels(candidates)
    if view_id is None or view_id not in by_id:
        # No established relation: not cross-view, nothing for the user to resolve here. The
        # assignment (and the UI) still show the geometry as unowned.
        return None
    label = labels.get(view_id, view_id)
    stale = _stale_role(record)
    if stale is not None:
        return {"reason": "stale_view_decision", "view_id": stale.get("view_id"),
                "detail": f"«{labels.get(stale.get('view_id'), stale.get('view_id'))}» görünüş rolünün onayı "
                          f"güncel değil (okuma yeni bir geometri sürümüne geçti); rolleri yeniden onaylayın."}
    roles = _role_rows(record)
    role = roles.get(view_id)
    primary = next((vid for vid, value in roles.items() if value == SOLID_ROLE), None)
    if role is None:
        if not by_id[view_id].get("used_for_solid", True):
            return {"reason": "candidate_isometric", "view_id": view_id,
                    "detail": f"Seçilen kontur «{label}» ({view_id}) içinde; izometrik resim parçanın "
                              f"üretim kaynağı olamaz — ana görünüşün konturunu seçin."}
        if primary and primary != view_id:
            return {"reason": "cross_view", "view_id": view_id,
                    "detail": f"Seçilen kontur ana görünüşün («{labels.get(primary, primary)}», {primary}) "
                              f"dışında: «{label}» ({view_id}) içinde. Üretim yalnız onaylanan ana görünüşün "
                              f"geometrisiyle başlar; konturu ana görünüşten seçin ya da görünüş rollerini "
                              f"güncelleyin."}
        return None
    if role != SOLID_ROLE:
        return {"reason": "role_not_solid_source", "view_id": view_id, "role": role,
                "detail": f"Seçilen kontur «{label}» ({view_id}) içinde; bu görünüşün rolü "
                          f"«{ROLE_LABELS.get(role, role)}» — üretim kaynağı olamaz."}
    return None


def conflict_questions(record: dict) -> list[str]:
    """The same conflict in the user's words — the one sentence the build refuses with (§52)."""
    row = conflict(record)
    return [row["detail"]] if row else []


__all__ = ["CATEGORY", "COVERAGE", "ROLES", "ROLE_LABELS", "SOLID_ROLE", "assign_view_ids",
           "candidate_labels", "category", "conflict", "conflict_questions", "geometry_bbox"]
