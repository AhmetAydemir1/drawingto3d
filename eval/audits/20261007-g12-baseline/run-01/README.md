# 20261007-g12-baseline / run-01 — G12.0 truth lock kanıtı

Başlangıç HEAD: `cc36f8de62548299761a5b9c8d9a1b97320635f1` (planla birebir aynı).
`PLAN.md` kök devri bu koşuda yapıldı (§5); plan metni byte-kopya olarak
`docs/PLAN-24-G12-CORRECTNESS.md` altında durur.

## Koşular

| adım | komut (özet) | sonuç | kanıt |
|---|---|---|---|
| G12.0.1 git facts | `git status/log/rev-parse` | HEAD beklenen | `git-facts.txt` |
| G12.0.2 sözleşme pinleri | `pytest -q tests/test_g12_baseline_contract.py` | 3 passed | testin kendisi + `frozen-evidence-sha256.txt` |
| G12.0.3 G9 guard (dondurulmuş evaluator) | `.venv-cad/bin/python eval/audits/20261007-guided-g9-plate/plate_regression.py part.step "examples/pdf with steps/5/plate with a pocket.STEP" ...` | **PASS (9/9 kontrol)** | `plate-regression-verdict.json` |
| G12.0.4 ilgili süit | `pytest -q <callout/guided/g11/general/geo dosyaları>` | **540 passed (189.20s)** | `pytest-relevant.log` |
| G12.0.5 süreç sınırı | `pytest -q tests/test_g12_runner_boundary.py` | 9 passed (sözleşme+test birlikte) | testin kendisi |
| §5 plan devri | `cp PLAN.md docs/PLAN_ROOT_BEFORE_G12_20261007.md; cp <attachment> PLAN.md docs/PLAN-24-G12-CORRECTNESS.md` | SHA256'lar eşit | `plan-handoff-sha256.txt` |

Plate guard ayrıntısı: bbox [120.011, 80.002, 15.0] (eksende [15, 80.002, 120.011] — G9/G11 kaydıyla
aynı), 1 katı/valid, 9 silindir, hacim farkı 0.000104 (tol 0.005), simetrik fark 30.32 mm³
(tol 0.005 × Vref), `existing_evaluator` verdict pass.

## Donmuş kanıt (değiştirilmedi — byte kaydı)

`frozen-evidence-sha256.txt`: `eval/guided_10_manifest.json`, `eval/guided_10_report.json`,
`eval/guided_10_report.md` ve G9/G11/G11-fixes/G9-G11-independent-review audit klasörlerinin
(`__pycache__` hariç) tam sha256 listesi (362 satır). Bu liste G12 boyunca karşılaştırma tabanıdır.

`eval/audits/20261007-guided-g11-fixes-independent-review/` — önceki pencerenin bağımsız inceleme
kanıtı; G12.0'da **değiştirilmeden** sürüm kontrolüne alındı (önceki durumda izlenmiyordu):
`independent-review-evidence-sha256.txt` bayt kimliğini sabitler.

## G12.0 kabul eşlemesi (§9)

- historical evidence unchanged → sha dosyaları + test yok (kanıt kaydı).
- manifest unchanged → `test_g12_baseline_contract.py` byte pinleri.
- G9 Plate PASS → `plate-regression-verdict.json`.
- G11 rate 1/9 pinned → `test_g12_baseline_contract.py` metrik pinleri.
- product tests green → 540 passed log.
- reference leakage process boundary hazır → `eval/g12_runner/{producer_input,produce_case,evaluate_case}.py`
  + `tests/test_g12_runner_boundary.py` (üretici görünümü beyaz liste; env/argv/girdi denetimi;
  ürün kaynağında vaka/referans sabiti taraması).
