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
                       ("callout-hint-yes", "button"), ("callout-hint-edit", "button"), ("callout-hint-ignore", "button"),
                       ("callout-show-ignored", "input")):
        assert collector.by_id.get(name) == kind, (name, collector.by_id.get(name))
        assert collector.counts[name] == 1, (name, collector.counts[name])


def test_callout_text_is_never_rendered_as_markup():
    """U16: drawing text is shown through textContent / textarea.value, never as HTML."""
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "innerHTML" not in script
    assert "textContent" in script
    assert "$('callout-text').value" in script


def test_the_production_panel_says_the_saved_text_reaches_the_build_and_gates_it():
    """PLAN §13/§14: since G7/G8 the saved text is compiled and the build waits — the panel may say
    neither that the text is unused (the old admission, now false) nor that a build may start with a
    callout still unresolved."""
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    assert "Kaydedilen ölçü/not metinleri artık üretime girer" in html
    assert "eksik kalanlar tamamlanmadan üretim başlamaz" in html
    assert "Onaylanmış hedefler (delik/ölçü) üretime derlenir" in html
    assert "Kaydedilen callout metinleri bu taslak üretiminde henüz kullanılmıyor" not in html


def test_the_empty_callout_list_gives_the_detectors_own_reason():
    """G3R-04: an empty list is not automatically "a text-less drawing" — the stored detection decides.

    The panel distinguishes the detector's normal empty result (`no_text_observations`) from a run
    that could not produce candidates, says honestly when an old record carries no detection
    information at all, and warns while still listing the candidates it did find.
    """
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "state.callout_detection" in script                     # public alan gerçekten tüketiliyor
    assert "'no_text_observations'" in script
    assert "source_digest_mismatch" in script and "invalid_frame" in script
    assert "eski kayıtta tespit bilgisi yok" in script             # uydurma açıklama yok
    assert "Aday üretilemedi" in script and "Uyarı: bazı gözlemler adaya çevrilemedi" in script
    collector = parse()
    assert collector.by_id.get("callout-detection") == "div"
    assert collector.counts["callout-detection"] == 1


def test_the_target_confirm_button_writes_the_proposal_the_panel_shows():
    """R03: vurgulanan öneri ile [Onayla]'nın yazdığı hedef aynı state'ten gelmeli.

    Eski hâl: etikete tıklamak `proposalHighlight`'ı kurarken genel [Onayla] her zaman
    `proposals[0]`'ı yazıyordu — panel başka bir hedefi işaret ederken onay sessizce ilkini
    kaydediyordu. Gerçek tarayıcı regresyonu denetim turunda (ui_fix_regression.py); burada
    servis edilen betiğin sözleşmesi çivilenir: tek bir aktif öneri state'i var ve Onayla onu
    (yoksa ilk öneriyi — düğme bunu açıkça söyler) kullanıyor.
    """
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "function activeProposal()" in script, "aktif öneri tek state'ten okunmalı"
    assert "$('target-confirm').onclick=()=>{const item=activeProposal();" in script, \
        "Onayla, o anda aktif olan öneriyi yazmalı"
    assert "`Doğru · ${" in script, "düğme hangi öneriyi yazacağını açıkça belirtmeli"


def test_the_review_panel_carries_the_ux01_burden_reduction_controls():
    """UX-01 §6–§8: "Sonraki eksik" çubuğu + makine ipucunun üçlü akışı birer kez servis edilir."""
    collector = parse()
    for name, kind in (("callout-prev", "button"), ("callout-remaining", "span"), ("callout-next", "button"),
                       ("callout-hint-yes", "button"), ("callout-hint-edit", "button"),
                       ("callout-hint-ignore", "button")):
        assert collector.by_id.get(name) == kind, (name, collector.by_id.get(name))
        assert collector.counts[name] == 1, (name, collector.counts[name])
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    assert "Sonraki eksik" in html and "Önceki" in html, "çözülmemiş akışı panelin en üstünde"
    assert "Evet, doğru" in html and "Bu bir ölçü/not değil" in html, "ipucu tek tıkla karar olabilmeli"
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "function unresolvedRows(" in script and "$('callout-next').onclick=" in script
    assert "accept_hint" in script and "$('callout-hint-yes').onclick=" in script


def test_the_bulk_scope_decision_is_one_atomic_request_from_the_users_own_selection():
    """Sessiz filtreleme yok (UX-01 §7): toplu karar tek atomik `bulk_set_ignored` isteğidir.

    Seçim yalnız kullanıcının kendi checkbox tıklamalarından doğar; gövde tek istekle gider.
    N ardışık `set_ignored` isteği ya da iki adımlı silah (bulkArmed) yoktur.
    """
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "bulk_set_ignored" in script and "$('callout-bulk-apply').onclick=" in script
    assert "selectedForBulk" in script, "seçim yalnız kullanıcının kendi checkbox tıklamalarından gelir"
    assert "bulkArmed" not in script, "iki adımlı silah kaldırıldı: tek açık eylem kaldı"
    assert "set_ignored_many" not in script, "arayüz artık yönlendirilmiş toplu istek üretmez"
    handler = script[script.index("$('callout-bulk-apply').onclick="):]
    handler = handler[:handler.index("};")]
    assert handler.count("command(") == 1, "toplu karar tek istekte gider"


def test_ux01_next_missing_flow_selects_from_unresolved_and_navigation_writes_nothing():
    """UX-01 §6: "Sonraki eksik" çözülmemiş listesinden seçer; oto-ilerleme yalnız başarılı karardan sonra.

    G11R-03 (bağımsız inceleme): oto-ilerleme karar ÖNCESİ görünür sırayı taşır — satır filtreyle
    düştüğünde seçim temizlense bile sıradaki açık alan kararın kendi konumundan sürdürülür.
    """
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "function rowResolved(" in script and "function unresolvedRows(" in script
    assert "function advanceAfterDecision(" in script
    assert "advance={id:previous,order:previousOrder}" in script, \
        "oto-ilerleme yalnız komut başarısında ve sırasıyla kurulur"
    assert "['transcribe','set_ignored','set_unbindable'].includes(action)" in script
    assert "state.callout_parses" in script, "parse durumu otoriter okuma satırından okunur"
    assert "if(!rowResolved(previousId))return;" in script, "oto-ilerleme yalnız çözülen satırdan sonra"
    assert "if(selectedCallout&&selectedCallout!==previousId)return;" in script, \
        "G11R-03: seçim filtreyle temizlendiyse ilerleme sürer, kullanıcı taşındıysa durur"
    assert "Tüm ölçü/not kontrolleri tamamlandı." in script
    next_handler = script[script.index("$('callout-next').onclick="):]
    next_handler = next_handler[:next_handler.index("};")]
    assert "command(" not in next_handler and "api(" not in next_handler, "navigasyon karar yazmaz"
    assert "if(action==='transcribe')drafts.delete(payload.callout_id)" in script, "taslak yalnız yazılan kararla temizlenir"


def test_ux01_hint_actions_are_single_click_and_drafts_stay_local():
    """UX-01 §8: üç düğme; "Düzelt" yalnız taslak kurar, "Evet, doğru" açık tıkla karar yazar."""
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    yes = script[script.index("$('callout-hint-yes').onclick="):]
    yes = yes[:yes.index("};")]
    assert "raw_text:row.machine_text_hint" in yes and "accept_hint:true" in yes
    edit = script[script.index("$('callout-hint-edit').onclick="):]
    edit = edit[:edit.index("};")]
    assert "drafts.set(" in edit and "command(" not in edit and "api(" not in edit
    ignore = script[script.index("$('callout-hint-ignore').onclick="):]
    ignore = ignore[:ignore.index("};")]
    assert "command('set_ignored'" in ignore
    assert "$('callout-hint-yes').hidden=!row.machine_text_hint;" in script, "ipucu yoksa elle yazma yolu: ipucu düğmeleri gizlenir"
    assert "$('callout-text').oninput=()=>{if(selectedCallout)drafts.set(selectedCallout,$('callout-text').value);renderCallouts();}" in script


def test_ux01_readiness_is_the_missing_items_checklist_and_build_waits_for_backend():
    """UX-01 §9: başlık "Eksik kalanlar"; görev satırları + ✓ satırları; hazır kararı backend'den."""
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    assert "<h3>Eksik kalanlar</h3>" in html
    assert "3B Modeli Oluştur" in html
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    for task in ("Ölçü/not kontrolü", "Gösterdiği yeri seç", "Dış şekli seç", "Ölçeği tamamla",
                 "Görüş yönünü onayla", "Modele uygulanıp uygulanmayacağına karar ver",
                 "Çelişkiyi düzelt", "Çizim/geometri sorununu düzelt"):
        assert task in script, task
    assert "const READINESS_TASK={missing_transcription:'Ölçü/not kontrolü'" in script
    assert "Tüm gerekli bilgiler tamamlandı" in script
    assert "build.disabled=pending||!r.ready" in script, "hazır kararı backend'den gelir; frontend ready diyemez"
    assert "r.questions.length" in script, "sayılar backend readiness satırlarından gelir"


def test_ux01_technical_ids_are_collapsed_and_main_copy_is_human():
    """UX-01 §10/§12: teknik ayrıntı <details> altında; ana copy ham kimlik göstermez."""
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    assert '<details id="technical-details">' in html and "<summary>Teknik ayrıntılar" in html
    assert "<h2>Günlük · her adım</h2>" not in html, "günlük artık collapsed teknik bölümün altında yaşar"
    assert '<details id="callout-technical">' in html
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "function humanRef(" in script
    assert "Köşe ${" in script and "'Dış şekil'" in script
    assert "(row.target_ids||[]).map(humanRef)" in script, "hedef özeti insan okunur etiketlerle"
    assert "callout-raw" in script and "kimlik:" in script, "ham kimlikler teknik satıra iner"


def test_ux01_user_language_has_no_internal_jargon_in_the_main_flow():
    """UX-01 §5: ana ekranda Callout/Target/jargon yok — ölçü/not ve gösterdiği yer dili."""
    html = (ROOT / "guided.html").read_text(encoding="utf-8")
    for gone in ("Callout inceleme", "Bu callout değil", "Hedef</strong>", "target-circle ·", "Sıradaki kararsız"):
        assert gone not in html, gone
    for present in ("Ölçü / not inceleme", "Bu ölçü/not nereyi gösteriyor?", "Programın önerdiği yer:",
                    "Modele uygulanmayacak", "Eksik kalanlar"):
        assert present in html, present
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "Çizimde şu mu yazıyor?" in script, "ipucu bir soru olarak sorulur"
    for gone in ("Önce bir callout seçin.", "Bu callout'ta makine ipucu yok", "Hedef türü", "hedef onayı güncel"):
        assert gone not in script, gone


def test_the_readiness_list_is_an_actionable_checklist():
    """G9 UX turu: hazırlık bir eylem listesidir — her madde kendi `action`ıyla hedefe götürür."""
    collector = parse()
    assert collector.by_id.get("readiness-questions") == "ul"
    assert collector.counts["readiness-questions"] == 1
    script = (ROOT / "guided.js").read_text(encoding="utf-8")
    assert "function readinessGo(" in script
    for action in ("'transcribe'", "'confirm_target'", "'confirm_view'"):
        assert action in script, action
    assert "scrollIntoView" in script
    assert "dataset.action" not in script, "eylem doğrudan sunucu satırından okunmalı, DOM'dan geri değil"
