"""R05: external confirmations must retain the context the reviewer actually saw.

Real store/parser/export/import/migration/undo, isolated synthetic sessions. Only
the new geometry producer and GEOMETRY_VERSION are patched for the migration case;
no PDF ingestion, model or CAD execution is claimed. Exit 1 means an invariant failed.
"""
import copy
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from drawingto3d import callout_models, guided
from review_probes import H, TOKEN, store_in


def bundle_for(store):
    bundle = store.review_export(TOKEN)
    bundle["actions"] = [{"action": "confirm_target", "callout_id": "k1",
                          "target_kind": "circle", "target_ids": ["c0"]}]
    return bundle


def attempt(store, bundle):
    record = store.load(TOKEN)
    before = H["_session_path"](store).read_bytes()
    error = None
    try:
        store.review_import(TOKEN, record["revision"], bundle)
    except ValueError as exc:
        error = str(exc)
    after = store.load(TOKEN)
    return {"error": error, "import_wrote": H["_session_path"](store).read_bytes() != before,
            "stored_targets": after["decisions"].get("callout_targets", []),
            "target_state": callout_models.callout_states(after)[0]["target"],
            "passed": bool(error) and H["_session_path"](store).read_bytes() == before}


def current_control(root):
    store = store_in(root, "current_control", "Ø8 THRU")
    bundle = bundle_for(store)
    before = copy.deepcopy(store.load(TOKEN))
    outcome = attempt(store, bundle)
    imported = store.load(TOKEN)
    store.save(TOKEN, imported["revision"], undo=True)
    undone = store.load(TOKEN)
    restored = undone["decisions"] == before["decisions"]
    revision_increased = undone["revision"] > imported["revision"] > before["revision"]
    outcome.update(case="current_bundle_and_undo_control", finding="control",
                   undo_restored_exact_decisions=restored,
                   revision_increased=revision_increased,
                   passed=outcome["error"] is None and outcome["import_wrote"]
                          and outcome["target_state"]["state"] == "current"
                          and restored and revision_increased)
    return outcome


def old_parser(root):
    store = store_in(root, "old_parser", "Ø8 THRU")
    bundle = bundle_for(store)
    bundle["parser_version"] = "callout-parser/obsolete"
    outcome = attempt(store, bundle)
    outcome.update(case="obsolete_parser_header", finding="R05",
                   reviewed_parser_version=bundle["parser_version"])
    return outcome


def migrated_geometry(root):
    store = store_in(root, "migrated_geometry", "Ø8 THRU")
    bundle = bundle_for(store)
    original = store.load(TOKEN)
    fresh = copy.deepcopy(original["options"])
    circle = next(row for row in fresh["circles"] if row["id"] == "c0")
    old_center = list(circle["center"])
    circle["center"] = [70, 45]
    with patch.object(guided, "GEOMETRY_VERSION", original["geometry_version"] + 1), \
            patch.object(guided, "observe", return_value=None), \
            patch.object(guided, "drawing_options", return_value=fresh):
        migrated = store.load(TOKEN)  # actual migration; same IDs, changed coordinates
        outcome = attempt(store, bundle)  # snapshot after migration, before import
        outcome.update(case="bundle_exported_before_geometry_migration", finding="R05",
                       reviewed_geometry_version=bundle["geometry_version"],
                       current_geometry_version=migrated["geometry_version"],
                       base_revision_equal=bundle["base_revision"] == migrated["revision"],
                       old_center=old_center, new_center=circle["center"],
                       old_geometry_key=callout_models.geometry_key(original),
                       new_geometry_key=callout_models.geometry_key(migrated))
    return outcome


def main():
    with tempfile.TemporaryDirectory(prefix="guided-import-review-") as temporary:
        root = Path(temporary)
        cases = [current_control(root), old_parser(root), migrated_geometry(root)]
    passed = all(case["passed"] for case in cases)
    print(json.dumps({"reviewed_baseline": "e51f555", "cases": cases, "passed": passed},
                     ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
