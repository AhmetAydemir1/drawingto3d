"""Every third-party module the repo imports must exist in this interpreter's environment.

Written after `uv run` inside the project directory re-synced `.venv` and dropped packages that the
lockfile does not carry; this is the deterministic way to see what is still missing instead of
waiting for a test to trip over it.
"""
import ast
import importlib.util
import pathlib
import sys

ROOTS = [pathlib.Path("src"), pathlib.Path("tests"), pathlib.Path("eval"), pathlib.Path(".")]
LOCAL = {"drawingto3d", "tests", "conftest", "eval"}

found: set[str] = set()
for root in ROOTS:
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "site-packages" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])

missing = []
for name in sorted(found):
    if name in LOCAL or name in sys.stdlib_module_names:
        continue
    try:
        if importlib.util.find_spec(name) is None:
            missing.append(name)
    except (ImportError, ValueError) as error:
        missing.append(f"{name} ({error})")

print("checked:", len(found), "top-level imports")
print("missing:", missing or "none")
