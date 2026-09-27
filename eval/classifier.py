"""Can a small classifier separate a printed number from the drawing's own ink? Measured by part group.

    PYTHONPATH=src .venv/bin/python eval/candidates.py            # the labelled set, from the text layers
    PYTHONPATH=src .venv/bin/python eval/classifier.py            # leave-one-part-group-out

The candidate set is exactly labelled: on a vector sheet the PDF's text layer says which boxes carry a printed
number, and the reader's candidates are judged against it. The section 7 measurement says three quarters of
those candidates are not numbers (150 candidates, 37 numbers, precision 0.25), which is what stops a scanned
sheet from ever fitting a scale.

This fits a logistic regression on the features `eval/candidates.py` measures from the crop and the stroke,
with the split **by part group**, never by crop: crops of one sheet are not independent samples, so a random
split would report a number that means nothing. It trains on two groups and tests on the third, three times,
and prints what that would do end to end — how many printed numbers survive and how much of the noise goes.

No dependency is added: the fit is forty lines of numpy, and the file is deliberately small so that the number
it reports can be reproduced by hand.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

FEATURES = ["glyphs", "fill_mean", "fill_min", "ink_density", "border_per_side", "holes", "hole_share",
            "aspect", "size_vs_sheet", "across_px", "along_px"]

# The same question asked without pixels. Two of these sheets print at 7.83 px/mm and one at 3.92, so a box
# measured in pixels means a different thing on each; dividing by the sheet's own text scale is what makes a
# model trained on two sheets applicable to a third.
SCALE_FREE = ["glyphs", "fill_mean", "fill_min", "ink_density", "border_per_side", "holes", "hole_share",
              "aspect", "size_vs_sheet", "w_vs_sheet", "h_vs_sheet", "across_vs_sheet", "along_vs_sheet"]


def load(path: Path, names: list[str]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for row in rows:
        # The sheet's own text scale, recovered from the one column that already carries it, so nothing has to
        # be re-measured for a feature set that is simply expressed in different units.
        biggest = max(float(row["w"]), float(row["h"]))
        median = biggest / row["size_vs_sheet"] if row.get("size_vs_sheet") else biggest
        row["w_vs_sheet"] = round(float(row["w"]) / median, 3)
        row["h_vs_sheet"] = round(float(row["h"]) / median, 3)
        row["across_vs_sheet"] = round(float(row["across_px"]) / median, 3)
        row["along_vs_sheet"] = round(float(row["along_px"]) / median, 3)
    matrix = np.array([[float(row[name]) for name in names] for row in rows])
    labels = np.array([row["label"] for row in rows], dtype=float)
    groups = [row["part_group"] for row in rows]
    return matrix, labels, groups


def fit(matrix: np.ndarray, labels: np.ndarray, iterations: int = 3000, rate: float = 0.5,
        penalty: float = 1e-3) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Logistic regression by full-batch gradient descent, on standardised features.

    Standardisation is fitted on the training rows only — scaled on the whole set it would leak the test
    group's own spread into the model that is being judged on it, which is the classic way a small experiment
    reports a number it cannot hold. The scaling it used comes back with the model so the test rows can be
    measured in the same units.
    """
    mean = matrix.mean(axis=0)
    spread = matrix.std(axis=0).copy()
    spread[spread == 0] = 1.0
    scaled = (matrix - mean) / spread
    weights = np.zeros(scaled.shape[1])
    bias = 0.0
    for _ in range(iterations):
        scores = scaled @ weights + bias
        probabilities = 1.0 / (1.0 + np.exp(-scores))
        error = probabilities - labels
        weights -= rate * (scaled.T @ error / len(labels) + penalty * weights)
        bias -= rate * error.mean()
    return np.concatenate([weights, [bias]]), mean, spread


def predict(model: np.ndarray, matrix: np.ndarray, mean: np.ndarray, spread: np.ndarray) -> np.ndarray:
    scaled = (matrix - mean) / spread
    scores = scaled @ model[:-1] + model[-1]
    return 1.0 / (1.0 + np.exp(-scores))


def score(truth: np.ndarray, guessed: np.ndarray) -> dict:
    true_positive = int(((guessed == 1) & (truth == 1)).sum())
    false_positive = int(((guessed == 1) & (truth == 0)).sum())
    false_negative = int(((guessed == 0) & (truth == 1)).sum())
    truth_positive = int((truth == 1).sum())
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, truth_positive)
    return {"tp": true_positive, "fp": false_positive, "fn": false_negative, "truth": truth_positive,
            "precision": round(precision, 3), "recall": round(recall, 3)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(ROOT / "out" / "candidates" / "candidates.jsonl"))
    parser.add_argument("--features", default="", help="virgülle ayrılmış özellik listesi; boşsa piksel özellikleri")
    parser.add_argument("--min-recall", type=float, default=0.9,
                        help="eğitim grubunda tutulması istenen basılı sayı oranı (eşik buradan seçilir)")
    arguments = parser.parse_args()
    names = [name for name in arguments.features.split(",") if name] or FEATURES
    matrix, labels, groups = load(Path(arguments.data), names)
    unique = sorted(set(groups))
    print(f"özellikler ({len(names)}): {', '.join(names)}")
    print(f"{len(labels)} aday, {int(labels.sum())} basılı sayı, {len(unique)} parça grubu: {unique}")
    print(f"kural yok (hepsini tut)      kesinlik {labels.mean():.3f}  geri çağırma 1.000\n")

    totals = {"tp": 0, "fp": 0, "fn": 0, "truth": 0}
    for held_out in unique:
        train = np.array([group != held_out for group in groups])
        test = ~train
        model, mean, spread = fit(matrix[train], labels[train])
        # The threshold is chosen on the training group, never on the one being judged: the smallest value
        # that still keeps the wanted share of the printed numbers there. Missing a printed number costs more
        # than passing a candidate the reader can then refuse, so the trade is stated, not guessed.
        training_probabilities = predict(model, matrix[train], mean, spread)
        threshold = 0.5
        candidates_for_threshold = sorted(set(np.round(training_probabilities, 2)))
        for value in candidates_for_threshold:
            kept = training_probabilities >= value
            recall = (kept & (labels[train] == 1)).sum() / max(1, (labels[train] == 1).sum())
            if recall >= arguments.min_recall:
                threshold = float(value)
            else:
                break
        train_recall = ((training_probabilities >= threshold) & (labels[train] == 1)).sum() / \
            max(1, (labels[train] == 1).sum())
        probabilities = predict(model, matrix[test], mean, spread)
        guessed = (probabilities >= threshold).astype(float)
        result = score(labels[test], guessed)
        for key in totals:
            totals[key] += result[key]
        print(f"eğitim {', '.join(group for group in unique if group != held_out):<28} "
              f"test {held_out:<18} aday {int(test.sum()):<4} "
              f"kesinlik {result['precision']:.3f}  geri çağırma {result['recall']:.3f}  "
              f"(tp {result['tp']} fp {result['fp']} fn {result['fn']})")
        weights = dict(zip(names, [round(float(value), 2) for value in model[:-1]]))
        strongest = sorted(weights.items(), key=lambda item: -abs(item[1]))[:5]
        print(f"    eşik {threshold:.2f} (eğitimde geri çağırma {train_recall:.2f})  en ağır beş ağırlık: {strongest}")

    precision = totals["tp"] / max(1, totals["tp"] + totals["fp"])
    recall = totals["tp"] / max(1, totals["truth"])
    print(f"\nbütün gruplar (her biri bir kez test): kesinlik {precision:.3f}  geri çağırma {recall:.3f}  "
          f"(tp {totals['tp']} fp {totals['fp']} fn {totals['fn']})")
    print(f"karşılaştırma: kural yok kesinlik {labels.mean():.3f} / geri çağırma 1.000")


if __name__ == "__main__":
    main()
