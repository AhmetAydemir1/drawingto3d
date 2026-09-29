"""The Ø glyph rule: a diameter prefix that is stroke art, not text.

A sheet can print `Ø` as a small circle drawn beside the digits while its text layer carries no Ø at
all. The rule that reads it is relative to the phrase (a circle no bigger than 60% of the phrase's
height, within 1.2 x its height of the box), so it needs no sheet scale.
"""

from drawingto3d.observe import BBox, Frame, Observations, Primitive, SourceRef, TextObservation, _diameter_prefix_glyph


def _observations(*primitives):
    return Observations(source=SourceRef(ref="probe", sha256="0" * 64),
                        frame=Frame(width=400, height=400, dpi=200),
                        text_placement="as-is", primitives=list(primitives), notes=["probe"])


def _glyph(geometry_id, centre, radius):
    return Primitive(id=geometry_id, path_id="p0", kind="circle", centre=list(centre), radius=radius)


def _phrase(text, kind="linear"):
    # The measured third sheet: the digits of `Ø20`, 27,4 px tall, with the glyph 21 px to their left.
    return TextObservation(id="t0", text=text, kind=kind, bbox=BBox(x=417.1, y=960.9, w=38.2, h=27.4))


def test_a_glyph_beside_the_digits_makes_the_phrase_a_diameter():
    assert _diameter_prefix_glyph(_phrase("20"), [_glyph("g214", (396.5, 973.7), 12.2)]) == "g214"


def test_the_rule_ignores_a_real_circle_and_a_distant_glyph():
    """A feature circle is too big to be a glyph, and another callout's glyph is too far away."""
    assert _diameter_prefix_glyph(_phrase("20"), [_glyph("g133", (536.9, 470.8), 39.4)]) is None
    assert _diameter_prefix_glyph(_phrase("20"), [_glyph("g999", (417.1, 823.0), 12.2)]) is None


def test_a_phrase_that_already_carries_its_prefix_is_left_alone():
    assert _diameter_prefix_glyph(_phrase("Ø20", kind="diameter"), [_glyph("g214", (396.5, 973.7), 12.2)]) is None


def test_only_circles_count_as_glyphs():
    arc = Primitive(id="g214", path_id="p0", kind="arc", centre=[396.5, 973.7], radius=12.2)
    assert _diameter_prefix_glyph(_phrase("20"), [arc]) is None
    assert _diameter_prefix_glyph(_phrase("20"), []) is None
