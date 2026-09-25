"""Read one printed number from one small crop.

Measured on the A4 practice sheet: tesseract turns `37` into `3`, `80` into `4`, `35` into `7` and `57`
into `5!` - it drops a digit and answers a number that was never printed, with no sign of doubt. The
vision model reads those same crops correctly, but it once answered `30` for a `D` in the frame band.
So the model reads and tesseract cross-checks: what the two disagree about is what the user is asked
about, instead of one silent answer standing for both.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from drawingto3d.ingest import parse_dimension_unit

NUMBER_PROMPT = (
    "One dimension is printed in this crop of an engineering drawing. "
    "Write the number exactly as printed, with a leading diameter, R or C mark if one is printed. "
    "Answer with the number only."
)


class NumberReader(Protocol):
    def read(self, crop: np.ndarray) -> str | None: ...


class TesseractReader:
    """Local OCR: fast, offline, and blind to its own mistakes."""

    def __init__(self, scale: float = 5.0) -> None:
        self.scale = scale

    def read(self, crop: np.ndarray) -> str | None:
        if shutil.which("tesseract") is None:
            return None
        big = _upscale(crop, self.scale)
        for delta in (0, -90, 90, 180):
            text = _tesseract(_rotate(big, delta), digits_only=False)
            if text:
                return text
        return None


class VisionReader:
    """The local vision model, asked one closed question about one small crop."""

    def __init__(self, scale: float = 3.0, vision=None) -> None:
        self.scale = scale
        self._vision = vision

    @property
    def vision(self):
        if self._vision is None:
            from drawingto3d.llama import OllamaVision

            self._vision = OllamaVision()
        return self._vision

    def read(self, crop: np.ndarray) -> str | None:
        big = _upscale(crop, self.scale)
        png = cv2.imencode(".png", cv2.cvtColor(big, cv2.COLOR_GRAY2BGR))[1].tobytes()
        answer = self.vision.ask(png, NUMBER_PROMPT, predict=12).strip()
        return answer or None


class AgreeingReader:
    """The model reads; tesseract's answer is kept beside it so a wrong read can be seen, not guessed at."""

    def __init__(self, primary: NumberReader | None = None, second: NumberReader | None = None) -> None:
        self.primary = primary if primary is not None else VisionReader()
        self.second = second if second is not None else TesseractReader()
        self.pairs: list[tuple[str | None, str | None]] = []

    def read(self, crop: np.ndarray) -> str | None:
        model = self.primary.read(crop)
        other = self.second.read(crop)
        self.pairs.append((model, other))
        return model or other

    def agreement(self) -> tuple[int, int]:
        """How many reads the two readers agreed on (same printed value), and how many they did not."""
        agreed = disagreed = 0
        for model, other in self.pairs:
            if model is None or other is None:
                disagreed += 1
                continue
            same = parse_dimension_unit(model)[1] == parse_dimension_unit(other)[1]
            agreed += 1 if same else 0
            disagreed += 0 if same else 1
        return agreed, disagreed

    def disagreements(self) -> list[tuple[str | None, str | None]]:
        out = []
        for model, other in self.pairs:
            if model is None or other is None:
                out.append((model, other))
                continue
            if parse_dimension_unit(model)[1] != parse_dimension_unit(other)[1]:
                out.append((model, other))
        return out


def read_dimension(
    reader: NumberReader,
    crop: np.ndarray,
    vertical: bool,
    expected_mm: float | None = None,
) -> str | None:
    """Read one number upright, and decide the rotation by the sheet's own scale when it is known.

    Text along a vertical dimension line is printed a quarter turn round. Asked about such a crop the
    vision model answers things like `R100` for a printed `80` - a number that parses, so nothing
    downstream can tell it is wrong. When the sheet has been calibrated, the rotation whose answer
    matches the length of the line the number sits on is the one to believe; without a calibration the
    first rotation that yields a number is used, and the sheet's calibration is the next thing to build.
    """
    attempts = [_turn(crop, 1), _turn(crop, -1)] if vertical else [crop]
    best: tuple[float, str] | None = None
    for attempt in attempts:
        text = reader.read(attempt)
        if not text:
            continue
        value = parse_dimension_unit(text)[1]
        if value is None:
            continue
        if expected_mm is None or expected_mm <= 0:
            return text
        error = abs(value - expected_mm) / expected_mm
        if best is None or error < best[0]:
            best = (error, text)
    return best[1] if best else None


def _turn(crop: np.ndarray, quarters: int) -> np.ndarray:
    if quarters > 0:
        return cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
    return cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)


def _rotate(image: np.ndarray, angle: float) -> np.ndarray:
    if angle % 360 == 0:
        return image
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderValue=255)


def _upscale(crop: np.ndarray, scale: float) -> np.ndarray:
    """Small print needs pixels: one digit is 20-45 px tall on a 200 dpi sheet."""
    height, width = crop.shape[:2]
    factor = max(1.0, scale)
    return cv2.resize(crop, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)


def _tesseract(image: np.ndarray, digits_only: bool) -> str | None:
    config = "--psm 7"
    if digits_only:
        config += " -c tessedit_char_whitelist=0123456789.,ØöOoRC/"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "crop.png"
        cv2.imwrite(str(path), image)
        try:
            done = subprocess.run(
                ["tesseract", str(path), "stdout", *config.split()],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.SubprocessError, OSError):
            return None
    text = " ".join(done.stdout.split()).strip()
    if not text:
        return None
    kind, value, _unit = parse_dimension_unit(text)
    return text if kind.value != "text" or value is not None else None
