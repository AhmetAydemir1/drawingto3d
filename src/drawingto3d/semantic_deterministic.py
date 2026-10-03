"""SEMREAD-001B — **D kolu**: mevcut deterministic okuyucuyu aday sözleşmesine çeviren küçük adapter.

Bu modül **hiçbir VLM çağrısı yapmaz** (llama import edilmez; testle bağlıdır). Yaptığı iş tek:
`observe` → `bind` → `meaning` çıktısını `semantic_candidates` sözleşmesine eşlemek. Yeni bir akıllı
okuyucu eklenmez, hedefe özel düzeltme yapılmaz; üretemediği alan `unknown`/`not_stated` kalır ve
**abstention doğru bir sonuçtur**, yanlış kesin iddia değildir.

Kasıtlı sınırlar:
  * `resolution="confirmed"` **yeni bir ürün statüsüne dönüşmez**; yalnız provenance/uncertainty
    notunda taşınır. Sözleşmede `supported`/`confirmed` alanı yoktur.
  * `physical.kind` deterministic yolda **unknown** kalır: bu okuyucu fiziksel yorum (delik/cephe)
    üretmez; `form=radius|diameter` yalnız **temsili** söyler.
  * Hangi yolun kullanıldığı kayda geçer: PDF metin katmanı mı, rasterda OCR mı (`source_type`).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from drawingto3d.bind import bind_page
from drawingto3d.meaning import meaning_page
from drawingto3d.observe import Observations, observe
from drawingto3d.semantic_candidates import (CANDIDATE_READER_VERSION, CalloutText, Candidate,
                                              CandidateResponse, CountField, DepthField, FormField,
                                              Num, PhysicalField, ProvenanceField, Region,
                                              RepresentationField, SourceField, TargetField,
                                              TerminationField, UncertaintyField, UNITS)

D_ARM = "D"
D_METHOD = "observe+bind+meaning"
READER_VERSION = CANDIDATE_READER_VERSION

THRU_PATTERN = re.compile(r"\b(thru|through)\b", re.IGNORECASE)
# Derinlik işareti **önce** işaretten **sonraki** sayı olarak okunur: "Ø8 ↧6" çağında 8 çap, 6 derinliktir.
DEPTH_AFTER = re.compile(r"[\u21a7\u2335]\s*([0-9]+(?:[.,][0-9]+)?)")
DEPTH_WORD = re.compile(r"\b(?:depth|derinlik|dep)\.?\s*([0-9]+(?:[.,][0-9]+)?)", re.IGNORECASE)
DEPTH_BEFORE = re.compile(r"([0-9]+(?:[.,][0-9]+)?)\s*[\u21a7\u2335]")
NUMBER_PATTERN = re.compile(r"([0-9]+(?:[.,][0-9]+)?)")
UNIT_PATTERN = re.compile(r"\b(mm|cm|m|in|inch|inches|\")\b", re.IGNORECASE)
UNIT_MAP = {"mm": "mm", "in": "in", "inch": "in", "inches": "in", '"': "in"}


def _round(value: float) -> float:
    return float(round(value, 6))


def _region_from_points(points: list[list[float]], frame) -> Region | None:
    if not points:
        return None
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    width = float(frame.width) or 1.0
    height = float(frame.height) or 1.0
    x0, x1 = max(0.0, min(xs) / width), min(1.0, max(xs) / width)
    y0, y1 = max(0.0, min(ys) / height), min(1.0, max(ys) / height)
    if x1 - x0 < 1e-4:
        x0, x1 = max(0.0, x0 - 0.002), min(1.0, x1 + 0.002)
    if y1 - y0 < 1e-4:
        y0, y1 = max(0.0, y0 - 0.002), min(1.0, y1 + 0.002)
    try:
        return Region(x0=x0, y0=y0, x1=x1, y1=y1)
    except ValueError:
        return None


def _region_from_bbox(bbox, frame) -> Region | None:
    """`bbox` BBox nesnesi ya da `[x, y, w, h]` listesi olabilir (bind kaydı liste tutar)."""
    if bbox is None:
        return None
    if isinstance(bbox, (list, tuple)):
        if len(bbox) != 4:
            return None
        x, y, w, h = (float(value) for value in bbox)
    else:
        x, y, w, h = (float(value) for value in (bbox.x, bbox.y, bbox.w, bbox.h))
    width = float(frame.width) or 1.0
    height = float(frame.height) or 1.0
    return _region_from_points([[x, y], [x + w, y + h]], frame)


def _unit_from_text(text: str, fallback: str | None) -> tuple[Literal["mm", "in"] | None, bool]:
    """"Birim basılı mı?" Ayrımı kayda geçer: basılı değilse okuyucunun varsayılanı kullanılır."""
    match = UNIT_PATTERN.search(text or "")
    if match:
        token = match.group(1).lower()
        mapped = UNIT_MAP.get(token, "mm" if token == "mm" else None)
        if mapped in UNITS:
            return mapped, True
    return (fallback if fallback in UNITS else None), False


def _termination_and_depth(text: str) -> tuple[
        Literal["thru", "finite", "unknown"], bool, float | None,
        Literal["known", "not_stated"], list[str]]:
    """Callout metninden sonlanma/derinlik okuması. Yazılı değilse `unknown`/`not_stated` kalır."""
    notes: list[str] = []
    thru = bool(THRU_PATTERN.search(text or ""))
    depth_match = (DEPTH_AFTER.search(text or "") or DEPTH_WORD.search(text or "")
                   or DEPTH_BEFORE.search(text or ""))
    depth_value = None
    if depth_match:
        raw = depth_match.group(1)
        if raw:
            depth_value = float(raw.replace(",", "."))
    if thru and depth_value is not None:
        notes.append("metinde hem thru hem derinlik işareti var: thru öncelikli okundu")
        depth_value = None
    if thru:
        return "thru", True, None, "not_stated", notes
    if depth_value is not None:
        return "finite", True, depth_value, "known", notes
    return "unknown", False, None, "not_stated", notes


def _form_field(span) -> FormField:
    if span.form == "radius":
        return FormField(symbol="R")
    if span.form == "diameter":
        return FormField(symbol="diameter")
    if span.form in ("distance",):
        return FormField(symbol="none")
    text = (span.text or "").strip().upper()
    if text.startswith("R") and NUMBER_PATTERN.search(text):
        return FormField(symbol="R")
    if any(glyph in (span.text or "") for glyph in ("\u00d8", "\u2300", "\u03a6", "\u03c6")):
        return FormField(symbol="diameter")
    return FormField(symbol="unknown")


def _representation_from_claim(claim, observations: Observations) -> RepresentationField:
    if claim is None:
        return RepresentationField(kind="unknown")
    ids = set(claim.matched_geometry or []) | {point.geometry_id for point in claim.points}
    kinds = {primitive.kind for primitive in observations.primitives if primitive.id in ids}
    if "circle" in kinds:
        diameter = None
        for primitive in observations.primitives:
            if primitive.id in ids and primitive.radius is not None:
                diameter = _round(2 * float(primitive.radius))
                break
        return RepresentationField(kind="circle", diameter_px=diameter)
    if "arc" in kinds:
        return RepresentationField(kind="arc")
    if kinds:
        return RepresentationField(kind="other")
    return RepresentationField(kind="unknown")


def _region_from_claim(claim, observations: Observations) -> Region | None:
    """Hedef bölge: daire ise merkez±yarıçap kutusu, değilse nokta (tek nokta genişletilir)."""
    primitives = {primitive.id: primitive for primitive in observations.primitives}
    corners: list[list[float]] = []
    for point in claim.points:
        primitive = primitives.get(point.geometry_id) if point.geometry_id else None
        if (primitive is not None and primitive.kind == "circle" and primitive.centre
                and primitive.radius):
            cx, cy = float(primitive.centre[0]), float(primitive.centre[1])
            radius = float(primitive.radius)
            corners += [[cx - radius, cy - radius], [cx + radius, cy + radius]]
        else:
            corners.append([float(point.point[0]), float(point.point[1])])
    return _region_from_points(corners, observations.frame) if corners else None


def _observation_id_from_claim(claim) -> str | None:
    if claim is None:
        return None
    matched = [value for value in (claim.matched_geometry or []) if value]
    if matched:
        return sorted(matched)[0]
    ids = sorted({point.geometry_id for point in claim.points if point.geometry_id})
    return ids[0] if ids else None


def deterministic_candidates(path: str | Path, *, image_id: str,
                             observations: Observations | None = None,
                             bindings=None, meanings=None) -> dict:
    """Bir paftayı D kolunda adaylara çevir. VLM çağrısı yok; girdi yalnız dosyanın kendisidir.

    `observations`/`bindings`/`meanings` verilebilir: testler model çağırmadan aynı eşlemeyi
    sınayabilsin diye (üretim yolunda hepsi dosyadan hesaplanır).
    """
    source = Path(path)
    observations = observations if observations is not None else observe(source)
    bindings = bindings if bindings is not None else bind_page(source)
    meanings = meanings if meanings is not None else meaning_page(source)

    binding_by_id = {binding.span_id: binding for binding in bindings.spans}
    candidates: list[Candidate] = []
    resolutions: dict[str, int] = {}
    with_value = without_value = 0

    for index, span in enumerate(meanings.spans, start=1):
        binding = binding_by_id.get(span.span_id)
        resolutions[span.resolution] = resolutions.get(span.resolution, 0) + 1
        unit, unit_printed = _unit_from_text(span.text, span.unit)
        termination, stated, depth_value, depth_state, notes = _termination_and_depth(span.text)

        target_region = None
        if span.claim is not None:
            target_region = _region_from_claim(span.claim, observations)
        callout_region = _region_from_bbox(binding.text_bbox if binding else None, observations.frame)
        region = target_region or callout_region
        if region is None:
            # Ölçülemeyen aday yazılmaz: bölgesiz aday adres doğrulaması yapılamaz.
            continue

        if span.printed_value is not None:
            with_value += 1
            size = Num(value=_round(float(span.printed_value)), unit=unit, state="known")
        else:
            without_value += 1
            size = Num(state="unknown" if span.resolution == "no-value" else "not_stated")

        found_circles = span.covered if span.count is not None else None
        count = CountField(printed=span.count, found_circles=found_circles,
                           state="known" if span.count is not None else "not_stated")

        uncertainty_fields: dict[str, str] = {}
        if not unit_printed:
            uncertainty_fields["size"] = ("birim basılı olarak okunmadı; okuyucunun varsayılanı "
                                          f"{unit or 'yok'} kullanıldı")
        uncertainty_fields["physical"] = ("deterministic okuyucu fiziksel yorum üretmez: "
                                          "temsil bilinir, delik/cephe değil")
        if span.resolution == "no-scale" and span.printed_value is not None:
            uncertainty_fields["target"] = "pafta ölçeği çözülemedi: bağlama doğrulanamadı"
        if span.alternatives:
            earlier = uncertainty_fields.get("target")
            note = f"{len(span.alternatives)} alternatif aday çifti var"
            uncertainty_fields["target"] = f"{earlier}; {note}" if earlier else note

        notes_all = [*list(span.notes), *(notes or [])]
        candidate = Candidate(
            candidate_id=f"d-{index}",
            callout=CalloutText(text=span.text or "", state="known" if span.text else "unknown"),
            representation=_representation_from_claim(span.claim, observations),
            physical=PhysicalField(kind="unknown",
                                   reason="deterministic okuyucu fiziksel yorum üretmez"),
            form=_form_field(span),
            size=size,
            count=count,
            termination=TerminationField(kind=termination, stated=stated),
            depth=DepthField(value=depth_value, unit=unit if depth_state == "known" else None,
                             state=depth_state),
            target=TargetField(region=target_region,
                               observation_id=_observation_id_from_claim(span.claim),
                               state="bound" if span.resolution == "confirmed" else "unknown"),
            source=SourceField(image_id=image_id, region=region, callout_region=callout_region),
            provenance=ProvenanceField(
                kind="deterministic", method=D_METHOD,
                source_ref=f"{source.name}#s{observations.frame.width}x{observations.frame.height}",
                notes=[f"resolution={span.resolution}", f"form={span.form}",
                       f"anchor_mode={span.anchor_mode}", *notes_all]),
            uncertainty=UncertaintyField(fields=uncertainty_fields,
                                         reason="; ".join(sorted(set(notes_all))) or "-"),
        )
        candidates.append(candidate)

    evidence = {
        "arm": D_ARM,
        "reader_version": READER_VERSION,
        "path": str(source),
        "source_type": "pdf" if source.suffix.lower() == ".pdf" else "raster",
        "frame": [int(observations.frame.width), int(observations.frame.height)],
        "counts": {
            "spans": len(meanings.spans),
            "candidates": len(candidates),
            "with_value": with_value,
            "without_value": without_value,
            "primitives": len(observations.primitives),
            "texts": len(observations.texts),
            "circles": sum(1 for p in observations.primitives if p.kind == "circle"),
        },
        "resolutions": resolutions,
        "coverage_note": ("D yalnız okuyucunun kendi bulduğu çağrıları adaylaştırır; üretemediği "
                          "hedefler `not_produced` sayılır ve raporda çıkarım olarak görünür"),
        "no_inference": True,
    }
    return {"response": CandidateResponse(items=candidates), "evidence": evidence}


__all__ = ["D_ARM", "D_METHOD", "deterministic_candidates", "READER_VERSION",
           "_region_from_points", "_termination_and_depth", "_unit_from_text"]
