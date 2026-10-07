"""G4 deterministic callout parser (`PLAN.md` §7–§9): grammar v1, no-guess, taxonomy.

The parser is pure, so everything here calls the real function on real text — no fixture reading a
record, no store, no model. The positive matrix is the plan's own list; the negative matrix pins the
error taxonomy, including the cases where a *correct parse is not a successful one* (`Ø8 DEEP`,
`4x 25`). Store integration (parse freshness after a transcription edit, ignore, undo) lives in
`test_guided_callout_parse.py`.
"""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from drawingto3d import callout_parse
from drawingto3d.callout_models import CALLOUT_PARSER_VERSION, SemanticParse
from drawingto3d.callout_parse import CalloutReading, parse_callout, semantic_parse

# --- pozitif matris (PLAN §8) ---------------------------------------------------

POSITIVE = [
    ("25", {"form": "linear", "size": 25.0}),
    ("25.0", {"form": "linear", "size": 25.0}),
    ("25 mm", {"form": "linear", "size": 25.0, "unit": "mm"}),
    ("Ø8", {"form": "diameter", "size": 8.0}),
    ("⌀8", {"form": "diameter", "size": 8.0}),
    ("DIA 8", {"form": "diameter", "size": 8.0}),
    ("8 DIA", {"form": "diameter", "size": 8.0}),
    ("R5", {"form": "radius", "size": 5.0}),
    ("4x Ø8", {"form": "diameter", "size": 8.0, "count": 4}),
    ("4 X Ø8", {"form": "diameter", "size": 8.0, "count": 4}),
    ("4 × Ø8 THRU", {"form": "diameter", "size": 8.0, "count": 4, "termination": "thru"}),
    # `THRU ALL` standart atölye dilidir (paftada: `4 x Ø6,80 THRU ALL`); ALL sonlandırmayı niteler,
    # ölçüyü değil. Yalnız THRU'dan hemen sonra tanınır — tek başına ALL sözcüğü hâlâ bilinmezdir.
    ("4 x Ø6,80 THRU ALL", {"form": "diameter", "size": 6.8, "count": 4, "termination": "thru"}),
    ("Ø8 THROUGH ALL", {"form": "diameter", "size": 8.0, "termination": "thru"}),
    ("Ø10 6 DEEP", {"form": "diameter", "size": 10.0, "termination": "blind", "depth": 6.0}),
    ("Ø10 DEPTH 6", {"form": "diameter", "size": 10.0, "termination": "blind", "depth": 6.0}),
    (".375 DIA", {"form": "diameter", "size": 0.375}),
]


@pytest.mark.parametrize("text,expected", POSITIVE)
def test_the_positive_matrix_parses_to_exactly_these_fields(text, expected):
    reading = parse_callout(text)
    assert reading.status == "parsed"
    assert {key: getattr(reading, key) for key in expected} == expected


@pytest.mark.parametrize("text", [text for text, _ in POSITIVE])
def test_the_parser_version_is_the_one_the_contract_expects(text):
    assert callout_parse.CALLOUT_PARSER_VERSION == CALLOUT_PARSER_VERSION == "callout-parser/2"
    assert parse_callout(text).status == "parsed"


# --- no-guess -------------------------------------------------------------------

def test_a_diameter_is_a_diameter_and_nothing_more():
    """`Ø8` says diameter 8 — not a hole, not through, not one place count (PLAN §8)."""
    reading = parse_callout("Ø8")
    assert (reading.form, reading.size) == ("diameter", 8.0)
    assert reading.termination is None and reading.count is None and reading.depth is None


def test_a_radius_is_a_radius_and_not_a_fillet():
    reading = parse_callout("R5")
    assert (reading.form, reading.size) == ("radius", 5.0)
    assert reading.count is None and reading.termination is None


def test_a_missing_unit_stays_missing():
    """Ne sayfa ne pafta birimi bir ölçünün birimini doldurur; eksik olan eksik söylenir."""
    assert parse_callout("Ø8").unit is None
    assert parse_callout("Ø8").warnings == ["unit_unresolved"]
    assert parse_callout("Ø8", sheet_unit="mm").unit is None, "pafta birimi ölçüye yazılmaz"
    assert "unit_unresolved" in parse_callout("Ø8", sheet_unit="mm").warnings


def test_a_printed_unit_that_disagrees_with_the_sheet_is_said_out_loud():
    assert parse_callout("25 mm", sheet_unit="mm").warnings == []
    assert parse_callout("25 mm", sheet_unit="in").warnings == ["unit_differs_from_sheet"]
    assert parse_callout("25 in", sheet_unit=None).warnings == []


def test_an_unknown_sheet_unit_is_a_programming_error_not_a_guess():
    with pytest.raises(ValueError):
        parse_callout("25", sheet_unit="ft")


# --- hata taksonomisi -----------------------------------------------------------

NEGATIVE = [
    ("", "empty_text"),
    ("   ", "empty_text"),
    ("\u00a0", "empty_text"),
    ("M8x1.25", "unsupported_syntax"),
    ("M6 DEEP 10", "unsupported_syntax"),
    ("6 DEEP", "unsupported_syntax"),
    ("1,234", "ambiguous_number"),
    ("Ø8 10", "ambiguous_number"),
    ("25 30", "ambiguous_number"),
    ("4x Ø8 5x Ø10", "ambiguous_number"),
    ("Ø", "missing_value_after_symbol"),
    ("R", "missing_value_after_symbol"),
    ("Ø8 DEEP", "missing_depth_value"),
    ("Ø8 Ø10", "conflicting_symbols"),
    ("Ø8 R5", "conflicting_symbols"),
    ("25 mm in", "conflicting_units"),
    ("4x", "count_without_feature"),
    ("4x 25", "count_without_feature"),
    ("Ø8 HELLO", "unknown_tokens"),
    ("ALL", "unknown_tokens"),
    ("Ø8 ALL", "unknown_tokens"),      # THRU olmadan ALL bir şey söylemez: uydurulmaz
    ("ALL THRU", "unknown_tokens"),    # akış yönü THRU → ALL'dir; tersi standart değil
    ("???", "unknown_tokens"),
    ("Ø8 THRU DEEP 6", "thru_with_depth"),
    ("Ø0", "invalid_value"),
    ("0x Ø8", "invalid_value"),
    ("4.5x Ø8", "invalid_value"),
]


@pytest.mark.parametrize("text,code", NEGATIVE)
def test_every_named_error_case_carries_its_own_code(text, code):
    reading = parse_callout(text)
    assert code in reading.warnings, reading.warnings
    assert reading.status != "parsed", "desteklenmeyen bir okuma başarılı sayılmaz"


def test_an_ambiguous_number_is_ambiguous_not_unsupported():
    """`Ø8 10`: hangi sayının ölçü olduğu belirsiz — yine de bir Ø okundu, o bilgi atılmaz."""
    reading = parse_callout("Ø8 10")
    assert reading.status == "ambiguous"
    assert reading.form == "diameter"
    assert reading.warnings == ["ambiguous_number", "unit_unresolved"]


def test_an_error_and_a_note_can_stand_together():
    """Kod sırası sabittir: hata kodları notlardan önce, her ikisi de tanımlı sırayla."""
    reading = parse_callout("Ø8 HELLO")
    assert reading.warnings == ["unknown_tokens", "unit_unresolved"]
    assert reading.status == "unsupported"
    assert reading.form == "diameter" and reading.size == 8.0, "okunan alanlar atılmaz"


def test_every_code_the_module_can_emit_is_declared():
    codes = set(callout_parse.ERROR_CODES) | set(callout_parse.NOTE_CODES)
    emitted = set()
    for text, _ in NEGATIVE:
        emitted |= set(parse_callout(text).warnings)
    for text, _ in POSITIVE:
        emitted |= set(parse_callout(text).warnings)
    emitted |= set(parse_callout("25 mm", sheet_unit="in").warnings)
    assert emitted <= codes, f"tanımsız kod: {sorted(emitted - codes)}"
    assert {"unit_unresolved", "unit_differs_from_sheet"} <= codes


# --- unicode ve boşluk özellikleri ----------------------------------------------

@pytest.mark.parametrize("text", ["Ø8", "ø8", "⌀8", "∅8", "DIA 8", "dia 8", "Diam 8"])
def test_diameter_glyphs_and_words_are_one_thing(text):
    """Dört glif ve iki sözcük aynı okumayı verir; hiçbiri 'bilinmeyen parça' değildir."""
    assert parse_callout(text).model_dump(exclude_none=True) == \
        parse_callout("Ø8").model_dump(exclude_none=True)


@pytest.mark.parametrize("separator", [" ", "  ", "\t", "\n", "\u00a0", "\u2009", "\u2003"])
def test_every_unicode_space_separates_the_same_way(separator):
    """Sayfa metni kopyalanırken gelen boşluk türleri okumayı değiştirmez."""
    reading = parse_callout(f"Ø8{separator}THRU")
    assert (reading.form, reading.size, reading.termination) == ("diameter", 8.0, "thru")


@pytest.mark.parametrize("text", ["4x Ø8", "4X Ø8", "4× Ø8", "4 x Ø8", "4 × ø8", "4X⌀8"])
def test_the_count_marker_is_one_thing_whatever_it_is_written_with(text):
    reading = parse_callout(text)
    assert (reading.form, reading.size, reading.count) == ("diameter", 8.0, 4)


@pytest.mark.parametrize("text", ["4XØ8 THRU", "4 ×Ø8 THRU", "4X Ø8 thru", "4 x Ø8 Through"])
def test_a_callout_written_without_spaces_is_the_same_callout(text):
    reading = parse_callout(text)
    assert (reading.form, reading.size, reading.count, reading.termination) == \
        ("diameter", 8.0, 4, "thru")


def test_a_comma_decimal_is_a_number_but_a_thousands_separator_is_ambiguous():
    assert parse_callout("25,5").size == 25.5
    assert parse_callout("1,234").status == "ambiguous" and parse_callout("1,234").size is None


# --- saflık, determinizm, ham metin --------------------------------------------

def test_the_same_text_yields_the_same_reading_every_time():
    first = parse_callout("  4 × Ø8 THRU  ")
    for _ in range(5):
        assert parse_callout("  4 × Ø8 THRU  ") == first


def test_the_parser_does_not_keep_or_reformulate_the_raw_text():
    """Ham metin hâlâ kullanıcının: okuma baytları tutmaz, yalnız alanları taşır."""
    raw = "  4 × Ø8 THRU  "
    reading = parse_callout(raw)
    assert raw == "  4 × Ø8 THRU  "
    assert set(reading.model_dump()) == {"status", "form", "size", "count", "termination", "depth",
                                         "unit", "warnings"}


def test_the_parser_module_stays_pure():
    """Dosya sistemi, ağ, model, OCR ve referans yok (PLAN §7)."""
    source = Path(callout_parse.__file__).read_text(encoding="utf-8")
    for forbidden in ("import open", "import requests", "import urllib", "import socket",
                      "from pathlib", "Path(", "import os", "subprocess", "import llama",
                      "import observe", "import guided", "import ingest"):
        assert forbidden not in source, f"parser saflığı bozuldu: {forbidden}"


def test_the_reading_is_a_validated_record_not_a_dict():
    with pytest.raises(ValidationError):
        CalloutReading.model_validate({"status": "parsed", "form": "diameter", "size": -1})
    with pytest.raises(ValidationError):
        CalloutReading.model_validate({"status": "parsed", "form": "hole"})   # sözlükte olmayan biçim


# --- SemanticParse bağlama (store sınırı) --------------------------------------

def test_semantic_parse_copies_the_store_identity_and_never_invents_it():
    row = {"callout_id": "k1", "raw_text": "4x Ø8 THRU", "revision": 7}
    parse = semantic_parse(row, sheet_unit="mm")
    assert isinstance(parse, SemanticParse)
    assert (parse.callout_id, parse.transcription_revision) == ("k1", 7)
    assert parse.parser_version == CALLOUT_PARSER_VERSION
    assert (parse.status, parse.form, parse.size, parse.count, parse.termination) == \
        ("parsed", "diameter", 8.0, 4, "thru")
    assert parse.unit is None, "yazılmayan birim transcription'dan türetilmez"
    assert parse.warnings == ["unit_unresolved"]


def test_semantic_parse_round_trips_through_json_like_the_stored_records():
    row = {"callout_id": "k1", "raw_text": "Ø10 6 DEEP", "revision": 3}
    parse = semantic_parse(row)
    again = SemanticParse.model_validate(json.loads(json.dumps(parse.model_dump(mode="json"))))
    assert again == parse


def test_an_unsupported_text_still_produces_a_record_with_a_reason():
    """Desteklenmeyen okuma da kayıtlıdır: 'başarısız' sessizce kaybolmaz.

    `M8x1.25` bir diş: tarayıcı içinden sayı okuyabilir (adet 8, 1.25) ama durum `unsupported`dur —
    okuyan katman bu satırı kullanmak zorunda değil, kullanamaz (PLAN §4: desteklenmeyen ≠ başarı).
    """
    parse = semantic_parse({"callout_id": "k2", "raw_text": "M8x1.25", "revision": 1})
    assert parse.status == "unsupported" and "unsupported_syntax" in parse.warnings
    assert parse.form != "diameter", "diş çaplı bir delik sayılmaz"
