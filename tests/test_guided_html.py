"""A0.1: the served page must parse as HTML and hold the four elements the JS binds to.

The audit's F01 counter-example was a `<button <div ...> ... id="bind-start"` shape: the parser saw no
`bind-start` element at all, so `guided.js` attached its handler to `None`. A JS syntax check cannot see
that; this reads the exact file the app serves (`app.ROOT / "guided.html"`) and parses it as HTML.
"""
import re
from html.parser import HTMLParser
from pathlib import Path

from drawingto3d.app import ROOT


class Collector(HTMLParser):
    VOID = {"br", "input", "img", "meta", "link", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.by_id = {}
        self.counts = {}
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.by_id[attrs["id"]] = tag
            self.counts[attrs["id"]] = self.counts.get(attrs["id"], 0) + 1
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack:
            self.errors.append(f"fazla kapanış </{tag}>")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
            return
        if tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.errors.append(f"kapanmamış <{self.stack.pop()}> (</{tag}> geldi)")
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append(f"eşleşmeyen </{tag}>")


def parse():
    collector = Collector()
    collector.feed((ROOT / "guided.html").read_text(encoding="utf-8"))
    return collector


def test_the_served_page_is_the_one_this_suite_reads():
    """Point at the file `app.py` hands to `/guided`, not at a copy."""
    assert (ROOT / "guided.html").is_file()
    assert ROOT == Path(__file__).resolve().parents[1] / "src" / "drawingto3d" / "static"


def test_the_bind_controls_exist_once_with_the_right_element_kinds():
    """A0.1: axis/direction are selects; the two buttons are buttons — exactly one each, in valid markup."""
    collector = parse()
    assert not collector.errors, collector.errors
    assert not collector.stack, collector.stack
    for name, kind in (("bind-axis", "select"), ("bind-direction", "select"),
                       ("bind-start", "button"), ("bind-cancel", "button")):
        assert collector.by_id.get(name) == kind, (name, collector.by_id.get(name))
        assert collector.counts[name] == 1, (name, collector.counts[name])


def test_no_button_is_broken_by_a_nested_tag():
    """The exact F01 shape: `<button <div ...` leaves the parser no button with that id."""
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    assert "<button <" not in html
    assert re.search(r"<select\s[^>]*id=\"bind-axis\"", html)
    assert re.search(r"<button\s[^>]*id=\"bind-start\"", html)
    # the axis/direction row is a sibling of the buttons, not inside one
    start = html.index("<button ")
    button = html[html.index('id="bind-start"') - 60:html.index('id="bind-start"')]
    assert "<div" not in button, button


def test_every_element_the_script_binds_to_exists_exactly_once():
    """G3.3: the F01 class of bug caught in general — an id `guided.js` binds to must be served once.

    The callout panel added a dozen new controls; a typo in one of them would leave its handler on
    `undefined` and only show up as a dead button in the browser.
    """
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    collector = parse()
    bound = set(re.findall(r"\$\('([A-Za-z0-9_-]+)'\)", script))
    bound |= set(re.findall(r"getElementById\('([A-Za-z0-9_-]+)'\)", script))
    assert bound
    assert not [name for name in sorted(bound) if collector.by_id.get(name) is None]
    assert not [name for name in sorted(bound) if collector.counts.get(name, 0) > 1]


def test_the_callout_panel_has_the_review_controls_the_contract_requires():
    """PLAN-21 §7.1: canvas tools, crop, text field and the three review actions, one each."""
    collector = parse()
    for name, kind in (("pick-callout", "button"), ("draw-callout", "button"), ("callout-crop", "canvas"),
                       ("callout-text", "textarea"), ("callout-save", "button"), ("callout-ignore", "button"),
                       ("callout-restore", "button"), ("callout-edit", "button"), ("callout-new", "button"),
                       ("callout-use-hint", "button"), ("callout-show-ignored", "input")):
        assert collector.by_id.get(name) == kind, (name, collector.by_id.get(name))
        assert collector.counts[name] == 1, (name, collector.counts[name])


def test_callout_text_is_never_rendered_as_markup():
    """U16: drawing text is shown through textContent / textarea.value, never as HTML."""
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert "textContent" in script
    assert "$('callout-text').value" in script


def test_the_production_panel_admits_callout_text_is_not_used_yet():
    """PLAN-21 §5/§7.1: the UI must not imply the saved text reached the STEP."""
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    assert "Kaydedilen callout metinleri bu taslak üretiminde henüz kullanılmıyor." in html
