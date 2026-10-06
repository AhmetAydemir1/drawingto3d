"""G4 deterministic callout reading parser (kök `PLAN.md` §7–§9).

`TranscriptionDecision.raw_text → CalloutReading`, and nothing else: no filesystem, no network, no
model, no OCR, no reference STEP, no store. The authority is the *user's own transcription*; a
machine text hint never reaches this function by itself, and this module never invents a field the
user did not write (PLAN §4: "yazmayan bilgiyi uydurma").

What the grammar knows (v1): a plain number (integer, decimal, `.375`, `25,5`), an explicit `mm`/`in`,
the diameter glyphs `Ø ⌀ ∅` and the words `DIA`/`DIAM`, the radius prefix `R`, a count written
`4x`/`4 X`/`4 ×`, `THRU`/`THROUGH`, and `DEPTH n`/`n DEEP`. `parse_callout` is pure and deterministic:
the same text yields the same reading, whatever the locale or the input order.

No-guess is part of the contract, not a style: `Ø8` means *diameter 8 and nothing more* — not a hole,
not through, not one place count; `R5` means *radius 5* — not a fillet. A missing unit stays missing
(`unit_unresolved`), never the sheet's unit: the sheet's own unit is only ever allowed to *disagree*
out loud (`unit_differs_from_sheet`).

Machine codes (Turkish wording lives in the interface, `guided.js`):

* `empty_text` — boş metin; `unsupported_syntax` — tanınmayan yazım (diş `M8x1.25` dahil);
* `ambiguous_number` — hangi sayının hangi alana ait olduğu belirsiz (ayrıca virgüllü binlik);
* `missing_value_after_symbol` — `Ø`, `R` değersiz; `missing_depth_value` — `DEEP` değersiz;
* `conflicting_symbols` — aynı callout'ta iki özellik simgesi; `conflicting_units` — iki farklı birim;
* `count_without_feature` — adet var ama adedi taşıyacak özellik (Ø/R) yok; `unknown_tokens` — okunmayan
  parça; `thru_with_depth` — `THRU` ile `DEEP` aynı callout'ta; `invalid_value` — sıfır/negatif ya da
  sınır dışı sayı.
* Notlar (`unit_unresolved`, `unit_differs_from_sheet`) durumu değiştirmez; yalnız söyler.

The pure result is `CalloutReading`, not `SemanticParse`: the callout id and the transcription
revision are the *store's*, and a pure function that invented them would be guessing. `semantic_parse`
pins a reading into the persisted `SemanticParse` record under one explicit parser version.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from drawingto3d.callout_models import CALLOUT_PARSER_VERSION, SemanticParse

__all__ = ["CALLOUT_PARSER_VERSION", "CalloutReading", "ERROR_CODES", "NOTE_CODES", "parse_callout",
           "semantic_parse"]

ERROR_CODES = (
    "empty_text",
    "unsupported_syntax",
    "ambiguous_number",
    "missing_value_after_symbol",
    "missing_depth_value",
    "conflicting_symbols",
    "conflicting_units",
    "count_without_feature",
    "unknown_tokens",
    "thru_with_depth",
    "invalid_value",
)
"""Every code that makes a reading *not* a successful parse (PLAN §8 taxonomy)."""

NOTE_CODES = ("unit_unresolved", "unit_differs_from_sheet")
"""Codes that inform without changing the status: the reading is still what the user wrote."""

_WARNING_ORDER = {code: index for index, code in enumerate(ERROR_CODES + NOTE_CODES)}

_HARD_CODES = frozenset(ERROR_CODES) - {"ambiguous_number"}
"""`ambiguous_number` is the one error that means *ambiguous* rather than *unsupported*."""

_AMBIGUOUS_CODES = ("ambiguous_number",)

# Diş yazımı (M8x1.25, M6) bu dilbilgisinde yok: sayı sanıp adet uydurmak yerine açıkça desteklenmez.
_THREAD_RE = re.compile(r"(?<![A-Za-z0-9])M\s*\d")

# Tek geçişli tarayıcı: boşluk, özellik simgeleri, sayı, adet işareti, thru/derinlik, birim, sözcük, geri kalan.
_TOKEN_RE = re.compile(
    r"""
      (?P<space>\s+)
    | (?P<diameter>Ø|ø|⌀|∅|DIAM|DIA)
    | (?P<radius>R(?![A-Za-z]))
    | (?P<number>\d+(?:[.,]\d+)?|\.\d+)
    | (?P<times>[xX×])
    | (?P<thru>THROUGH|THRU)
    | (?P<depthword>DEPTH|DEEP)
    | (?P<mm>MM)
    | (?P<inch>INCHES|INCH|IN|")
    | (?P<word>[A-Za-z]+)
    | (?P<other>\S)
    """,
    re.IGNORECASE | re.VERBOSE,
)

_THOUSANDS_RE = re.compile(r"\d+,\d{3}")


class CalloutReading(BaseModel):
    """What the user's own text says — the semantic fields, with no store identity attached."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    status: Literal["parsed", "ambiguous", "unsupported"]
    form: Literal["diameter", "radius", "linear"] | None = None
    size: float | None = Field(default=None, gt=0, le=1e6)
    count: int | None = Field(default=None, ge=1)
    termination: Literal["thru", "blind"] | None = None
    depth: float | None = Field(default=None, gt=0, le=1e6)
    unit: Literal["mm", "in"] | None = None
    warnings: list[str] = Field(default_factory=list, max_length=50)


def _number_value(text: str) -> float | str:
    """`25` / `25.0` / `.375` / `25,5` → sayı; `1,234` → `ambiguous` (binlik mi, ondalık mı?)."""
    if "," in text:
        if _THOUSANDS_RE.fullmatch(text):
            return "ambiguous"
        return float(text.replace(",", "."))
    return float(text)


def _with_unit(current: Literal["mm", "in"] | None, value: Literal["mm", "in"],
               warnings: set[str]) -> Literal["mm", "in"] | None:
    """One unit per callout. A second unit token — the same one or a different one — is a conflict."""
    if current is not None:
        warnings.add("conflicting_units")
        return current
    return value


def _sorted_warnings(warnings: set[str]) -> list[str]:
    return sorted(warnings, key=lambda code: (_WARNING_ORDER.get(code, len(_WARNING_ORDER)), code))


def _tokens(text: str) -> list[tuple[str, str]]:
    return [(str(match.lastgroup), match.group()) for match in _TOKEN_RE.finditer(text)
            if match.lastgroup != "space"]


def _depth_pick(tokens: list[tuple[str, str]], words: list[int],
                free: list[tuple[int, float]]) -> tuple[float | None, list[tuple[int, float]], str | None]:
    """`DEPTH 6` and `6 DEEP` both name the number next to the word; the one after it wins.

    Returns the depth, the numbers that stay free, and the code to raise when the word has no number.
    """
    after = [item for item in free if item[0] in {word + 1 for word in words}]
    before = [item for item in free if item[0] in {word - 1 for word in words}]
    near = after or before
    if len(near) > 1:
        return None, free, "ambiguous_number"
    if not near:
        return None, free, "missing_depth_value"
    return near[0][1], [item for item in free if item != near[0]], None


def parse_callout(raw_text: str, *, sheet_unit: str | None = None) -> CalloutReading:
    """The user's transcription → the semantic fields it actually carries (pure, deterministic).

    `sheet_unit` is the unit the *user* stated for the sheet (the calibration's own unit). It never
    fills in a missing unit — a dimension with no printed unit stays unresolved — and is only used to
    say out loud that a printed unit disagrees with the sheet (`unit_differs_from_sheet`).
    """
    if sheet_unit not in (None, "mm", "in"):
        raise ValueError(f"sheet_unit 'mm', 'in' ya da None olmalı: {sheet_unit!r}")
    text = " ".join(str(raw_text or "").split())
    if not text:
        return CalloutReading(status="unsupported", warnings=["empty_text"])

    warnings: set[str] = set()
    if _THREAD_RE.search(text):
        warnings.add("unsupported_syntax")     # diş: bu dilbilgisinde yok, uydurulmuş adet yok

    tokens = _tokens(text)
    symbols: list[tuple[int, Literal["diameter", "radius"]]] = []
    numbers: list[tuple[int, float]] = []
    depth_words: list[int] = []
    claimed: set[int] = set()
    form: Literal["diameter", "radius", "linear"] | None = None
    count: int | None = None
    unit: Literal["mm", "in"] | None = None
    thru = False

    for index, (kind, raw) in enumerate(tokens):
        if kind == "diameter":
            symbols.append((index, "diameter"))
        elif kind == "radius":
            symbols.append((index, "radius"))
        elif kind == "number":
            value = _number_value(raw)
            if isinstance(value, str):
                warnings.add("ambiguous_number")        # binlik mi ondalık mı: `1,234`
                continue
            numbers.append((index, value))
        elif kind == "times":
            previous = tokens[index - 1] if index else None
            if previous is None or previous[0] != "number" or (index - 1) in claimed:
                warnings.add("unsupported_syntax")      # tek başına adet işareti
                continue
            claimed.add(index - 1)
            value = _number_value(previous[1])
            if isinstance(value, str) or value < 1 or value != int(value):
                warnings.add("ambiguous_number" if isinstance(value, str) else "invalid_value")
                continue
            if count is not None:
                warnings.add("ambiguous_number")        # iki adet işareti: hangisi?
                continue
            count = int(value)
        elif kind == "thru":
            thru = True
        elif kind == "depthword":
            depth_words.append(index)
        elif kind == "mm":
            unit = _with_unit(unit, "mm", warnings)
        elif kind == "inch":
            unit = _with_unit(unit, "in", warnings)
        else:                                            # sözcük ya da tanınmayan karakter
            warnings.add("unknown_tokens")

    kinds = {kind for _, kind in symbols}
    conflict = len(kinds) > 1 or len(symbols) > 1
    if conflict:
        warnings.add("conflicting_symbols")         # tek callout = tek özellik simgesi
    form = None if conflict or not symbols else symbols[0][1]

    free = [(index, value) for index, value in numbers if index not in claimed]
    size: float | None = None
    depth: float | None = None
    if symbols and free:
        # Özellik boyutu: simgeye en yakın serbest sayı (`Ø10 6 DEEP` → 10); eşitlikte sonraki kazanır.
        anchor = symbols[0][0]
        pick = min(free, key=lambda item: (abs(item[0] - anchor), item[0] < anchor))
        size = pick[1]
        free = [item for item in free if item != pick]
    if depth_words:
        depth, free, issue = _depth_pick(tokens, depth_words, free)
        if issue:
            warnings.add(issue)
    if free:
        if symbols:
            warnings.add("ambiguous_number")        # simgenin dışında artan sayı: hangi alan?
        elif len(free) == 1:
            form, size = "linear", free[0][1]
        else:
            warnings.add("ambiguous_number")        # hangi sayı ölçü, hangisi değil?

    if size is not None and not (0 < size <= 1e6):
        warnings.add("invalid_value")
        size = None
    if depth is not None and not (0 < depth <= 1e6):
        warnings.add("invalid_value")
        depth = None
    if size is None and not (warnings & _HARD_CODES) and "ambiguous_number" not in warnings:
        warnings.add("missing_value_after_symbol" if form is not None else "unsupported_syntax")
    if count is not None and form not in ("diameter", "radius"):
        warnings.add("count_without_feature")
    if thru and depth is not None:
        warnings.add("thru_with_depth")                 # geçişli ile kör aynı callout'ta olmaz

    termination = None
    if thru and depth is None:
        termination = "thru"
    elif depth is not None and not thru:
        termination = "blind"

    if form is not None and size is not None:
        if unit is None:
            warnings.add("unit_unresolved")             # birim yazılmadıysa uydurulmaz
        elif sheet_unit is not None and unit != sheet_unit:
            warnings.add("unit_differs_from_sheet")

    if warnings & _HARD_CODES:
        status = "unsupported"
    elif warnings & set(_AMBIGUOUS_CODES):
        status = "ambiguous"
    else:
        status = "parsed"

    return CalloutReading(status=status, form=form, size=size, count=count, termination=termination,
                          depth=depth, unit=unit, warnings=_sorted_warnings(warnings))


def semantic_parse(transcription: dict, *, sheet_unit: str | None = None,
                   parser_version: str = CALLOUT_PARSER_VERSION) -> SemanticParse:
    """A stored transcription row → the `SemanticParse` record that belongs to it.

    The store's own identity (`callout_id`, `revision`) is copied, never derived: the parse is bound to
    the exact transcription revision it was computed from, which is what makes an edited text stale
    its parse instead of silently re-reading the old one (PLAN §9).
    """
    reading = parse_callout(transcription.get("raw_text"), sheet_unit=sheet_unit)
    return SemanticParse(callout_id=transcription["callout_id"], parser_version=parser_version,
                         transcription_revision=transcription.get("revision") or 0,
                         **reading.model_dump())
