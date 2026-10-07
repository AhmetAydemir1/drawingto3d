"""G11R-04/G11R-05 regresyonu: kanıt dosyaları ve tarayıcı/değerlendirici hata ayrımı.

Bağımsız inceleme (20261007): (a) STEP üretilemeyen vakalarda session/review/readiness kanıtı hiç
yazılmıyordu; (b) her console/network hatası `EVALUATOR` etiketi alıyordu — flange'in tek sorunu
favicon 404'tü, ex17/ex13'ünki build HTTP 400'dü. Bu dosya `g11_evidence`'ın sözleşmesini çiviler ve
`g11_runner.py`'nin bu yolları gerçekten kullandığını kaynak düzeyinde doğrular (runner cdp-venv
bağımlılıkları taşır; burada modül import edilemez, wiring kaynaktan okunur).
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
G11 = ROOT / "eval/audits/20261007-guided-g11"


def _load():
    spec = importlib.util.spec_from_file_location("g11_evidence_under_test", G11 / "g11_evidence.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_favicon_404_is_ui_telemetry_not_a_failure_code():
    """G11R-05: flange/my-part'ın tek 'hatası' favicon'du; bu bir UI telemetrisi satırıdır."""
    evidence = _load()
    signals = evidence.classify_signals(
        console_errors=[{"level": "error", "source": "network",
                         "text": "Failed to load resource: the server responded with a status of 404",
                         "url": "http://127.0.0.1:8765/favicon.ico"}],
        rejected_requests=[{"status": 404, "url": "http://127.0.0.1:8765/favicon.ico", "request": {}}])
    assert len(signals["assets"]) == 1                    # iki kaynak da tek satıra iner
    assert signals["assets"][0]["status"] == 404          # durumlu kayıt kazanır
    assert signals["api_failures"] == [] and signals["page_errors"] == []


def test_a_build_400_is_an_api_failure_and_a_js_error_is_a_page_error():
    """G11R-05: /api build reddi ayrı kovada; gerçek JS hatası sayfa hatası olarak saklanır."""
    evidence = _load()
    signals = evidence.classify_signals(
        console_errors=[{"level": "error", "source": "javascript", "url": "",
                         "text": "Uncaught TypeError: row is undefined"}],
        rejected_requests=[{"status": 400, "url": "http://127.0.0.1:8765/api/guided/build",
                            "request": {"postData": "{}"}}])
    assert [row["status"] for row in signals["api_failures"]] == [400]
    assert signals["api_failures"][0]["url"].endswith("/api/guided/build")
    assert signals["page_errors"] and "Uncaught TypeError" in signals["page_errors"][0]["text"]
    assert signals["assets"] == []
    # Hiçbir kova EVALUATOR anlamı taşımaz; etiket yalnız değerlendirici sürecinden gelir.
    assert "EVALUATOR" not in json.dumps(signals, ensure_ascii=False)


def test_aborted_requests_go_to_cancelled_not_to_api_failures():
    evidence = _load()
    signals = evidence.classify_signals([], [{"status": 0, "url": "", "request": {}}])
    assert len(signals["cancelled"]) == 1 and signals["api_failures"] == []


def test_build_errors_are_classified_by_the_servers_own_text():
    """G11R-05: build hatası kök nedenine göre ayrılır — asla EVALUATOR olmaz."""
    evidence = _load()
    assert evidence.classify_build_error(
        "üretim için eksik/uyumsuz girdiler var: ölçek girilmedi")[0] == "CONSTRAINT_UNSUPPORTED"
    assert evidence.classify_build_error(
        "callout kararları çelişiyor: aynı bölge iki kez")[0] == "CONSTRAINT_CONFLICT"
    assert evidence.classify_build_error(
        "temel geometri kaynaktan yenilenemedi")[0] == "CAD_UNSUPPORTED"
    assert evidence.classify_build_error("kesit çözülemedi: profil kapalı değil")[0] == "CAD_UNSUPPORTED"
    assert evidence.classify_build_error(None)[0] == "CAD_UNSUPPORTED"
    for text in (None, "", "üretim için eksik/uyumsuz girdiler var: hedef onaylanmadı",
                 "callout kararları çelişiyor", "rastgele"):
        assert evidence.classify_build_error(text)[0] != "EVALUATOR", text


def test_case_evidence_is_written_regardless_of_build_outcome(tmp_path):
    """G11R-04: üç dosya build durumundan bağımsız yazılır; STEP/plan indirmesi kapının arkasında."""
    evidence = _load()
    out = tmp_path / "case"
    written = evidence.write_case_evidence(
        out, session_public={"token": "tok", "step": None},
        review_bundle={"decisions": [], "actions": []},
        readiness={"ready": False, "questions": [{"text": "Ölçek eksik"}]})
    assert sorted(written) == ["readiness.json", "review-bundle.json", "session-public.json"]
    for name in written:
        assert (out / name).is_file()
    assert json.loads((out / "readiness.json").read_text())["questions"][0]["text"] == "Ölçek eksik"
    assert evidence.EVIDENCE_ALWAYS == ("session-public.json", "review-bundle.json", "readiness.json")
    assert "part.step" in evidence.EVIDENCE_BUILD_GATED


def test_recovered_evidence_is_labeled_with_time_and_source():
    """G11R-04: sonradan kurtarılan kanıt koşu-anı kanıtı gibi sunulmaz."""
    evidence = _load()
    note = evidence.recovered_note("out/guided/abc/session.json", recovered_at="2026-10-07T21:00:00+03:00")
    assert note["label"] == "recovered-after-run"
    assert note["not_run_time_evidence"] is True
    assert note["recovered_from"].endswith("session.json")
    assert note["recovered_at"] == "2026-10-07T21:00:00+03:00"
    assert "sonradan" in note["note"]


def test_the_runner_wires_the_new_evidence_and_classification_paths():
    """G11R-04/05 wiring: kayıt alanları, kanıt yazımı, build yanıtı ve telemetri çağrıları."""
    source = (G11 / "g11_runner.py").read_text(encoding="utf-8")
    for needle in ('"session_token": None', 'record["session_token"] = token',
                   'EVIDENCE.write_case_evidence(', 'if final.get("step"):  # STEP/plan downloads stay '
                   'gated on a real build', 'record["browser_signals"] = EVIDENCE.classify_signals(',
                   'record["build_error_response"] = build_response_probe(page)',
                   'EVIDENCE.classify_build_error(', 'record["readiness"] = {',
                   '"recipe_sha256"', '"recipe_notes"', '"input_verification"'):
        assert needle in source, needle
    # Eski hatalı sınıflama gitti: console/network → EVALUATOR üretilemez.
    assert 'fail("EVALUATOR", {"console_errors"' not in source
    assert '"console_errors": errors, "rejected_requests": page.failures' not in source


def test_round_runs_write_records_to_their_own_directory_and_capture_late_tokens():
    """Tur kayıtları tur dizinine yazılır; yavaş ingest'te token kapı sonrası yakalanır.

    rerun-round2 koşusunda kayıt yolu resmî `cases/` dizinine sabitti (kayıtlar yanlış yere yazıldı,
    tur sonrası taşındı) ve 120 sn'lik token yoklaması ağır rasterlerde kaçırdı (kayıtlar token'sız
    kaldı, artefakttan tamamlandı) — ikisinin de düzeltmesi burada çivilenir.
    """
    source = (G11 / "g11_runner.py").read_text(encoding="utf-8")
    assert 'path = base / "cases" / f"{case_id}.json"' in source
    assert 'path = G11_DIR / "cases" / f"{case_id}.json"' not in source
    assert "oturum token (kapı sonrası yakalandı)" in source
    assert 'token = page.ev("return new URLSearchParams(location.search).get(\'session\');")' in source
