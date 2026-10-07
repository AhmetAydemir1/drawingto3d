"""G12.0 süreç sınırı: üretici referansı göremez — süzgeç, denetim, kaynak taraması (PLAN-24 §8).

Üç soru sorulur ve üçü de mekanik olarak yanıtlanır:

1. Manifest girdisinden üretici görünümü yalnız beyaz listeyi taşır mı (10 vaka)?
2. Manifestteki hiçbir referans kimliği üretici girdisinin JSON'unda geçer mi?
3. `assert_reference_free` env/argv/yük içine sızan bir referansı gerçekten yakalar mı — ve temiz
   yükte susar mı?

Ek olarak ürün kaynağı (`src/drawingto3d`) vaka adı, manifest referans alanı ya da kaynak-kimliği
sabitini *kod* olarak taşımaz (docstring tarihçesi serbest — PLAN-24 §95; kod yolu serbest değil).
"""
import ast
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNNER = ROOT / "eval/g12_runner"
MANIFEST = ROOT / "eval/guided_10_manifest.json"


def _load(name: str, path: pathlib.Path):
    import sys
    sys.path.insert(0, str(RUNNER))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRODUCER_INPUT = _load("g12_producer_input", RUNNER / "producer_input.py")
PRODUCE_CASE = _load("g12_produce_case", RUNNER / "produce_case.py")


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_producer_view_is_a_whitelist_for_every_manifest_case():
    manifest = _manifest()
    for entry in manifest["cases"]:
        view = PRODUCER_INPUT.producer_view(entry)
        assert set(view) == set(PRODUCER_INPUT.PRODUCER_FIELDS), entry["case_id"]
        assert view["case_id"] == entry["case_id"]
        assert view["source_path"] == entry["source_path"]
        # Değerlendirme sınıflandırması ve referans alanları üreticiye taşınmaz.
        for banned in ("tags", "note", "prior_exposure", "reference_available",
                       "reference_identifier_evaluator_only"):
            assert banned not in view, (entry["case_id"], banned)


def test_all_manifest_reference_values_stay_out_of_producer_input():
    manifest = _manifest()
    references = PRODUCER_INPUT.reference_values(manifest)
    assert references, "manifestte en az bir referans olmalı (aksi hâlde denetim boşa koşar)"
    for entry in manifest["cases"]:
        blob = json.dumps(PRODUCER_INPUT.producer_view(entry), ensure_ascii=False).lower()
        for token in references + [token.rsplit("/", 1)[-1] for token in references]:
            assert token.lower() not in blob, (entry["case_id"], token)
        for banned in PRODUCER_INPUT.FORBIDDEN_FIELDS:
            assert banned not in blob, (entry["case_id"], banned)


def test_guard_fires_on_reference_in_env_argv_or_payload():
    references = PRODUCER_INPUT.reference_values(_manifest())
    needle = references[0]
    cases = {
        "env": {"env": {"G12_LEAK": needle}},
        "argv": {"argv": ["python", "driver.py", "--reference", needle]},
        "payload": {"producer_input": {"note": f"compare with {needle}"}},
        "field": {"producer_input": {"reference_identifier_evaluator_only": "x"}},
        "nested_field": {"a": [{"deep": {"reference_path": "y"}}]},
    }
    for label, payload in cases.items():
        try:
            PRODUCER_INPUT.assert_reference_free(payload, reference_values=references, where=label)
        except PRODUCER_INPUT.ReferenceLeakage:
            continue
        raise AssertionError(f"sızma yakalanmadı: {label}")


def test_guard_is_silent_on_a_clean_payload():
    references = PRODUCER_INPUT.reference_values(_manifest())
    clean = {"producer_input": PRODUCER_INPUT.producer_view(_manifest()["cases"][0]),
             "env": {"G12_CASE_ID": "plate-pocket-vector"}, "argv": ["python", "driver.py", "r.json"]}
    PRODUCER_INPUT.assert_reference_free(clean, reference_values=references, where="test-clean")


def test_produce_case_prepare_only_writes_reference_free_input(tmp_path):
    references = PRODUCER_INPUT.reference_values(_manifest())
    code = PRODUCE_CASE.main(["--case", "plate-pocket-vector", "--round", str(tmp_path),
                              "--prepare-only"])
    assert code == 0
    target = tmp_path / "cases" / "plate-pocket-vector" / "producer-input.json"
    assert target.exists()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert set(payload) == set(PRODUCER_INPUT.PRODUCER_FIELDS)
    blob = json.dumps(payload, ensure_ascii=False).lower()
    for token in references + [t.rsplit("/", 1)[-1] for t in references]:
        assert token.lower() not in blob
    record = json.loads((target.parent / "produce-run.json").read_text(encoding="utf-8"))
    assert record["reference_checked"] is True and record["driver_ran"] is False
    assert record["producer_input_sha256"] == __import__("hashlib").sha256(
        target.read_bytes()).hexdigest()


def _code_strings(path: pathlib.Path) -> list[tuple[int, str]]:
    """Bir Python dosyasının *kod* string'leri — docstring'ler tarihçedir, sayılmaz (PLAN-24 §95)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    doc_constant_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                doc_constant_ids.add(id(body[0].value))
    found = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in doc_constant_ids):
            found.append((getattr(node, "lineno", 0), node.value))
    return found


def test_product_source_has_no_case_names_or_reference_tokens():
    """§83/§84: ürün kodu vaka adına, manifest referans alanına ya da kaynak kimliğine göre dallanamaz."""
    manifest = _manifest()
    banned = {"reference_identifier_evaluator_only", "guided_10_manifest"}
    for entry in manifest["cases"]:
        banned.add(entry["case_id"])
        banned.add(entry["source_sha256"])
        for key in ("source_path", "reference_identifier_evaluator_only"):
            value = entry.get(key)
            if value:
                banned.add(str(value).rsplit("/", 1)[-1])
    offenders = []
    for path in sorted((ROOT / "src/drawingto3d").rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        if relative.startswith("src/drawingto3d/legacy/tests/"):
            continue                      # emekli boru hattının kendi testleri; ürün yolu değil
        for lineno, text in _code_strings(path):
            for token in banned:
                if token in text:
                    offenders.append((relative, lineno, token))
    assert not offenders, f"ürün kodunda vaka/referans sabiti: {offenders}"


# --- G12R-04: varsayılan sürücü kaynak-only G12 sürücüsüdür; eski G11 yolu reddedilir -------------

def test_the_default_driver_is_the_source_only_g12_driver():
    """Belgelenen varsayılan komut kaynak-only sürücüyü çalıştırır — G11 koşucusu değil."""
    assert PRODUCE_CASE.DEFAULT_DRIVER == RUNNER / "g12_runner.py"
    assert "g11" not in str(PRODUCE_CASE.DEFAULT_DRIVER).lower()


def test_the_legacy_g11_driver_is_refused_on_the_g12_producer_path(tmp_path):
    """Tarihsel G11 koşucusu G12 üretici yolunda SESSİZCE çalışmaz: açık ret, sürücü hiç başlamaz."""
    legacy = ROOT / "eval/audits/20261007-guided-g11/g11_runner.py"
    assert legacy.exists(), "tarihsel koşucu yerinde duruyor (dokunulmadı)"
    code = PRODUCE_CASE.main(["--case", "plate-pocket-vector", "--round", str(tmp_path),
                              "--driver", str(legacy), "--prepare-only"])
    assert code == PRODUCE_CASE.EXIT_LEGACY_DRIVER
    # Ret, hiçbir dosya yazmadan döner: yanlışlıkla tarihsel bir dizin verilse bile oraya dokunulmaz.
    assert not list(tmp_path.rglob("*")), "ret koşusu hiçbir dosya yazmaz"
    assert PRODUCE_CASE.refuse_legacy_driver(legacy) == "legacy-g11-driver"
    assert PRODUCE_CASE.refuse_legacy_driver(pathlib.Path("g12_runner.py")) is None


def test_the_default_command_runs_the_source_only_driver_end_to_end(tmp_path):
    """Gerçek varsayılan komut: üretici girdisi → sürücü → istenen tur dizinine yazılan kayıtlar.

    Sahte uygulama (yalnız `/api/guided/*` uçları) koşar; sürücünün gördüğü tek bilgi üretici girdisi
    ve reçetedir. Tarihsel G11 dizini koşu boyunca değişmez — varsayılan yol artık oraya yazmaz.
    """
    import http.server
    import threading

    manifest = _manifest()
    entry = next(row for row in manifest["cases"] if row["case_id"] == "plate-pocket-vector")
    seen: list[tuple[str, dict]] = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):        # sessiz
            pass

        def _reply(self, payload: dict):
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):                    # noqa: N802 — stdlib adı
            size = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(size)
            try:
                payload = json.loads(raw.decode())
            except Exception:                 # noqa: BLE001 — /open gövdesi ham bayt olabilir
                payload = {"raw_bytes": len(raw)}
            seen.append((self.path, payload))
            if self.path == "/api/guided/open":
                self._reply({"token": "t" * 32, "revision": 1, "callout_candidates": [{"id": "k1"}],
                             "effective_callouts": [{"id": "k1"}], "coverage": {"coverage_complete": False}})
            elif self.path == "/api/guided/callout":
                self._reply({"token": "t" * 32, "revision": 2})
            elif self.path == "/api/guided/strategy":
                self._reply({"token": "t" * 32, "revision": 3})
            elif self.path == "/api/guided/readiness":
                self._reply({"ready": False, "questions": [], "coverage": {"coverage_complete": False}})
            else:
                self._reply({})

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    history = ROOT / "eval/audits/20261007-guided-g11/cases"
    before = sorted(path.name for path in history.iterdir()) if history.exists() else None
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text(json.dumps({
        "case_id": "plate-pocket-vector", "source_sha256": entry["source_sha256"],
        "operator_basis": "source_drawing_only",
        "callout_actions": [{"callout_id": "k1", "action": "not_model_input", "reason": "sentetik"}],
        "strategy_decision": {"kind": "extrude_profile"}, "notes": []}, ensure_ascii=False), encoding="utf-8")
    try:
        code = PRODUCE_CASE.main(["--case", "plate-pocket-vector", "--round", str(tmp_path),
                                  "--recipe", str(recipe_path)],
                                 _app_environment={"G12_APP": f"http://127.0.0.1:{server.server_port}"})
    finally:
        server.shutdown()
        server.server_close()
    assert code == 0, code
    case_dir = tmp_path / "cases" / "plate-pocket-vector"
    produce = json.loads((case_dir / "produce-run.json").read_text(encoding="utf-8"))
    run = json.loads((case_dir / "g12-run.json").read_text(encoding="utf-8"))
    assert produce["driver_ran"] is True and produce["exit"] == 0
    assert produce["reference_checked"] is True
    assert run["remaining_closed_automatically"] is False
    assert run["build_status"] == "skipped:not-ready" and run["readiness_ready"] is False
    assert [path for path, _ in seen] == ["/api/guided/open", "/api/guided/callout",
                                          "/api/guided/strategy", "/api/guided/readiness"]
    assert run["source_sha256_checked"] is True
    assert (sorted(path.name for path in history.iterdir()) if history.exists() else None) == before, \
        "varsayılan komut tarihsel G11 dizinine yazmamalı"
