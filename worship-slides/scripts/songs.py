"""Song slides: bilingual lyric slides, jianpu (numbered-notation) slides, imported hymn decks,
section badges, and the phrase splitter that turns extracted score rows into slide specs."""
import copy
from pptx.oxml.ns import qn
import json, os
from lxml import etree
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

STYLES_PATH = os.environ.get("WORSHIP_STYLES") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "styles.json")
STYLES = json.load(open(STYLES_PATH, encoding="utf-8"))

def _rgb(h): return RGBColor.from_string(h.lstrip("#"))

def _box(s, x, y, w, h, text, size, color, zh_font, en_font, bold=False, italic=False,
         align=PP_ALIGN.CENTER, spc=0, lang="zh-CN", anchor=MSO_ANCHOR.TOP):
    tb = s.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, Emu(25400))
    bp = tf._txBody.find(qn("a:bodyPr"))
    for c in list(bp): bp.remove(c)
    etree.SubElement(bp, qn("a:noAutofit"))
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run(); r.text = text
    f = r.font; f.size = Pt(size); f.bold = bold; f.italic = italic; f.color.rgb = _rgb(color)
    rpr = r._r.get_or_add_rPr(); rpr.set("lang", lang)
    if spc: rpr.set("spc", str(spc))
    for tag, face in (("a:latin", en_font), ("a:ea", zh_font), ("a:cs", en_font)):
        e = etree.SubElement(rpr, qn(tag)); e.set("typeface", face)
    return tb

def section_kind(tag):
    t = (tag or "").upper()
    for k in ("CHORUS", "BRIDGE", "ENDING", "TAG", "VERSE"):
        if t.startswith(k):
            return k
    return "VERSE"

def section_bg(P, kind):
    if kind == "BRIDGE":
        return P.get("bridge_bg", P["verse_bg"])
    if kind in ("CHORUS", "ENDING", "TAG"):
        return P["chorus_bg"]
    return P["verse_bg"]

def badge_texts(tags):
    """simple English labels: Verse 1/2/3 numbered; Chorus plain; Bridge numbered only if there are several"""
    kinds = [section_kind(t) for t in tags]
    names = {"VERSE": "Verse", "CHORUS": "Chorus", "BRIDGE": "Bridge", "ENDING": "Ending", "TAG": "Tag"}
    distinct = {}
    for t, k in zip(tags, kinds):
        distinct.setdefault(k, [])
        if t not in distinct[k]: distinct[k].append(t)
    out, vcount = [], 0
    for t, k in zip(tags, kinds):
        if k == "VERSE":
            num = "".join(ch for ch in t if ch.isdigit())
            if not num:
                vcount += 1; num = str(vcount)
            out.append(f"Verse {num}")
        elif k == "BRIDGE" and len(distinct[k]) > 1:
            out.append(f"Bridge {distinct[k].index(t) + 1}")
        else:
            out.append(names[k])
    return out

def _badge(s, x, y, text, kind, P, zh_f, en_f):
    from pptx.enum.shapes import MSO_SHAPE
    style = STYLES["section_types"][kind]["badge"]
    w = Inches(0.42 * sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in text) + 0.5)
    b = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, Inches(0.6))
    b.adjustments[0] = 0.5; b.shadow.inherit = False
    acc, ink = P["accent"], P["verse_bg"]
    if style == "solid":
        b.fill.solid(); b.fill.fore_color.rgb = _rgb(acc); b.line.fill.background(); col = ink
    elif style == "soft":
        b.fill.solid(); b.fill.fore_color.rgb = _rgb(P["en"]); b.line.fill.background(); col = ink
    else:
        b.fill.background(); b.line.color.rgb = _rgb(acc); b.line.width = Pt(2.5); col = acc
    tf = b.text_frame; tf.margin_left = tf.margin_right = Emu(0); tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = text
    f = r.font; f.size = Pt(30); f.bold = True; f.color.rgb = _rgb(col)
    rpr = r._r.get_or_add_rPr()
    for tag, face in (("a:latin", en_f), ("a:ea", zh_f), ("a:cs", en_f)):
        e = etree.SubElement(rpr, qn(tag)); e.set("typeface", face)
    return b

def _header2(s, title, badge, kind, P, right, zh_f, en_f, M):
    """section badge on the left, song title centred, optional info (key) on the right"""
    W = s.part.package.presentation_part.presentation.slide_width
    if badge:
        _badge(s, M, Inches(0.14), badge, kind, P, zh_f, en_f)
    _box(s, Inches(3.2), Inches(0.08), W - Inches(6.4), Inches(0.72), title, 40, P["accent"], zh_f, en_f, bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if right:
        _box(s, W - M - Inches(4.0), Inches(0.12), Inches(4.0), Inches(0.66), right, 26, P["accent"], zh_f, en_f,
             align=PP_ALIGN.RIGHT, lang="en-US", anchor=MSO_ANCHOR.MIDDLE)

def _rule(s, cx, y, w, color):
    from pptx.enum.shapes import MSO_SHAPE
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, cx - w // 2, y, w, Emu(12700))
    r.fill.solid(); r.fill.fore_color.rgb = _rgb(color); r.line.fill.background(); r.shadow.inherit = False

def _fade(s, ms=600):
    tr = etree.SubElement(s._element, qn("p:transition")); tr.set("spd", "med")
    etree.SubElement(tr, qn("p:fade"))
    # transition must precede timing/extLst
    s._element.remove(tr); cs = s._element.find(qn("p:clrMapOvr"))
    (cs if cs is not None else s._element.find(qn("p:cSld"))).addnext(tr)

def styled_lyric_slides(prs, layout, song, profile, target="pptx"):
    P = STYLES["profiles"][profile]
    F = STYLES["fonts"][target]
    zh_f, en_f, en_it = F["zh"], F["en"], F["en_italic"]
    W, H = prs.slide_width, prs.slide_height
    M = Inches(0.6); BW = W - 2 * M
    secs = song["sections"]
    title_page = song.get("title_page", True)
    # a section can continue the one before it (e.g. a song's final line after the last chorus):
    # same background as that section, no badge of its own, lines centred
    cont = {c["section_index"]: c.get("continues_section", c["section_index"] - 1)
            for c in song.get("section_continuations", [])}
    for i, j in cont.items():
        if not (0 < i < len(secs) and 0 <= j < i):
            raise ValueError(f"section_continuations: section {i} cannot continue section {j}")
    n = len(secs) + (1 if title_page else 0)      # page numbers count this song only
    first = 2 if title_page else 1
    out = []

    def new(bg):
        s = prs.slides.add_slide(layout)
        for sh in list(s.shapes): sh._element.getparent().remove(sh._element)
        s.background.fill.solid(); s.background.fill.fore_color.rgb = _rgb(bg)
        _fade(s); return s

    def foot(s, i, chorus, credit=False):
        acc = P.get("accent_chorus", P["accent"]) if chorus else P["accent"]
        _box(s, W - Inches(2.1), H - Inches(0.5), Inches(1.6), Inches(0.42), f"{i}/{n}", 22, acc,
             zh_f, en_f, align=PP_ALIGN.RIGHT, lang="en-US")
        if credit:
            _box(s, M, H - Inches(0.5), Inches(10.8), Inches(0.42), song["credit"], 16, P["en"],
                 zh_f, en_f, align=PP_ALIGN.LEFT, lang="en-US")

    if title_page:
        s = new(P["verse_bg"])
        _box(s, M, Inches(2.35), BW, Inches(1.2), song["title"], 72, P["zh"], zh_f, en_f, bold=True, spc=432)
        _rule(s, W // 2, Inches(3.75), Inches(1.0), P["accent"])
        _box(s, M, Inches(3.95), BW, Inches(0.8), song.get("en_title", ""), 36, P["en"], zh_f, en_f,
             italic=en_it, spc=100, lang="en-US")
        foot(s, 1, False, credit=True); out.append(s)

    # stanza slides (badges counted over the sections that show one)
    shown = [t for i, t in enumerate(song["tags"]) if i not in cont]
    shown_badges = iter(badge_texts(shown))
    badges = [None if i in cont else next(shown_badges) for i in range(len(secs))]
    for k, ((_, pairs), tag, bdg) in enumerate(zip(secs, song["tags"], badges), first):
        i = k - first
        if i in cont:
            tag = song["tags"][cont[i]]
        kind = section_kind(tag)
        chorus = kind in ("CHORUS", "ENDING", "TAG")
        s = new(section_bg(P, kind))
        acc = P.get("accent_chorus", P["accent"]) if chorus else P["accent"]
        en_c = P.get("en_chorus", P["en"]) if chorus else P["en"]
        _header2(s, song["title"], bdg, kind, P, None, zh_f, en_f, M)
        _rule(s, W // 2, Inches(0.84), W - 2 * M, acc)
        top, pitch = Inches(1.0), Inches(1.43)
        if i in cont:                                   # centre a short continuation in the lyric area
            top = Inches(1.0) + (4 - len(pairs)) * pitch // 2
        for j, (cn, en) in enumerate(pairs):
            y = top + pitch * j
            _box(s, M, y, BW, Inches(0.92), cn, 60, P["zh"], zh_f, en_f, spc=167)
            if en:
                _box(s, M, y + Inches(0.86), BW, Inches(0.58), en, 32, en_c, zh_f, en_f,
                     italic=en_it, bold=True, spc=57, lang="en-US")
        foot(s, k, chorus, credit=(k == n or (not title_page and k == 1))); out.append(s)
    return out


def import_slides(prs, src_path, layout):
    """Insert every slide of another .pptx as-is (shapes, own background, images, transition)."""
    import io, re as _re
    from pptx import Presentation as _P
    src = _P(src_path)
    out = []
    for ss in src.slides:
        new = prs.slides.add_slide(layout)
        rmap = {}
        for rId, rel in ss.part.rels.items():
            if "notesSlide" in rel.reltype or "slideLayout" in rel.reltype:
                continue
            if rel.is_external:
                rmap[rId] = new.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
            elif rel.reltype.endswith("/image"):
                _, rmap[rId] = new.part.get_or_add_image_part(io.BytesIO(rel.target_part.blob))
            else:
                raise ValueError("unsupported rel " + rel.reltype)
        xml = etree.tostring(ss._element).decode()
        xml = _re.sub(r'(r:(?:embed|id|link|pict)=")(rId\d+)(")',
                      lambda m: m.group(1) + rmap.get(m.group(2), m.group(2)) + m.group(3), xml)
        el = etree.fromstring(xml)
        for c in list(new._element): new._element.remove(c)
        for c in el: new._element.append(c)
        for k in ("shapes", "placeholders", "background"): new.__dict__.pop(k, None)
        out.append(new)
    return out

# ---------------------------------------------------------------- jianpu (numbered notation) slides
# note token: <pitch><octave marks>/<dur>[^]   pitch 0-7, ' = 8va up (dot above), , = down (dot below)
# dur: 16, 8, 8. (dotted 8th), 4, 4., 2 ; ^ = tie/slur to next note ; | = barline
# lyrics: one syllable per sounding note that starts a syllable; tied continuation notes take '~'
_W = {"16": 0.62, "16.": 0.72, "8": 0.78, "8.": 0.95, "4": 1.0, "4.": 1.35, "2": 1.6}
_UL = {"16": 2, "16.": 2, "8": 1, "8.": 1, "4": 0, "4.": 0, "2": 0}

def _cell_widths(cells, u0=0.72, en_em=0.17 * 32 / 26, cn_w=0.92):
    """inches per cell: rhythmic width, widened where a CN or EN syllable needs room"""
    out = []
    for c in cells:
        if c.get("bar"):
            out.append(0.3); continue
        base = (0.8 if c.get("dash") else _W[c["dur"]]) * u0
        need = 0.0
        if c.get("cn") not in (None, "~"):
            need = cn_w
        if c.get("en"):
            need = max(need, len(c["en"]) * en_em + 0.14)
        out.append(max(base, need))
    return out

def _parse(system):
    if "cells" in system:
        out = []
        for c in system["cells"]:
            c = dict(c)
            c["w"] = 0.35 if c.get("bar") else (0.8 if c.get("dash") else _W[c["dur"]])
            out.append(c)
        return out
    cells = []
    for tok in system["notes"].split():
        if tok == "|":
            cells.append(dict(bar=True, w=0.35)); continue
        head, dur = tok.split("/")
        tie = dur.endswith("^"); dur = dur.rstrip("^")
        pitch = head[0]; up = head.count("'"); down = head.count(",")
        cells.append(dict(bar=False, pitch=pitch, up=up, down=down, dur=dur, tie=tie, w=_W[dur]))
    sound = [c for c in cells if not c["bar"] and c["pitch"] != "0"]
    cn, en = system["cn"].split(), system["en"].split()
    assert len(cn) == len(sound) == len(en), (len(cn), len(sound), len(en), system["cn"])
    for c, a, b in zip(sound, cn, en):
        c["cn"], c["en"] = a, b
    return cells

def jianpu_slides(prs, layout, song, profile="rosa-parchment", target="pptx"):
    from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
    P = STYLES["profiles"][profile]
    F = STYLES["fonts"][target]
    zh_f, en_f = F["zh"], F["en"]
    INK, SOFT, ACC = P["zh"], P["en"], P["accent"]
    W, H = prs.slide_width, prs.slide_height
    M = Inches(0.5)
    NUM, CN, EN = 40, 60, 32
    out = []

    def line(s, x1, y1, x2, y2, color, w=1.5):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
        c.line.color.rgb = _rgb(color); c.line.width = Pt(w)
        return c

    def dot(s, cx, cy, color):
        d = s.shapes.add_shape(MSO_SHAPE.OVAL, cx - Emu(45720), cy - Emu(45720), Emu(91440), Emu(91440))
        d.fill.solid(); d.fill.fore_color.rgb = _rgb(color); d.line.fill.background(); d.shadow.inherit = False

    def arc(s, x1, x2, y, color):
        import math
        h = Inches(0.13); pts = []
        for i in range(13):
            t = i / 12
            pts.append((int(x1 + (x2 - x1) * t), int(y + h - h * math.sin(math.pi * t))))
        fb = s.shapes.build_freeform(pts[0][0], pts[0][1], scale=1.0)
        fb.add_line_segments(pts[1:], close=False)
        a = fb.convert_to_shape()
        a.fill.background(); a.line.color.rgb = _rgb(color); a.line.width = Pt(2.0); a.shadow.inherit = False

    if song.get("title") and song.get("title_page", True):  # title slide
        s = prs.slides.add_slide(layout)
        for sh in list(s.shapes): sh._element.getparent().remove(sh._element)
        s.background.fill.solid(); s.background.fill.fore_color.rgb = _rgb(P["verse_bg"]); _fade(s)
        _box(s, M, Inches(2.2), W - 2 * M, Inches(1.2), song["title"], 72, INK, zh_f, en_f, bold=True, spc=400)
        _rule(s, W // 2, Inches(3.6), Inches(1.0), ACC)
        _box(s, M, Inches(3.8), W - 2 * M, Inches(0.8), song.get("en_title", ""), 36, SOFT, zh_f, en_f,
             italic=F["en_italic"], lang="en-US")
        _box(s, M, Inches(4.75), W - 2 * M, Inches(0.5), song["key"] + "　·　简谱", 22, ACC, zh_f, en_f, lang="en-US")
        _box(s, M, H - Inches(0.5), Inches(10.8), Inches(0.42), song["credit"], 16, SOFT, zh_f, en_f,
             align=PP_ALIGN.LEFT, lang="en-US")
        s._kind = "song"
        out.append(s)
    for k, slide in enumerate(song["slides"], 1):
        s = prs.slides.add_slide(layout)
        for sh in list(s.shapes): sh._element.getparent().remove(sh._element)
        kind = section_kind(slide.get("tag"))
        s.background.fill.solid(); s.background.fill.fore_color.rgb = _rgb(section_bg(P, kind))
        _fade(s)
        _header2(s, song["title"], slide["badge"], kind, P, song["key"], zh_f, en_f, M)
        line(s, M, Inches(0.84), W - M, Inches(0.84), ACC, 0.75)
        for n, system in enumerate(slide["systems"]):
            cells = _parse(system)
            wid = _cell_widths(cells)
            scale = min(1.35, (W - Inches(0.7)) / Inches(sum(wid)))
            wid = [int(Inches(w) * scale) for w in wid]
            x = int((W - sum(wid)) / 2)
            y0 = Inches(0.98) + n * Inches(3.08)
            dig_top, dig_h = y0 + Inches(0.18), Inches(0.72)
            ul1 = dig_top + dig_h - Inches(0.06)
            cn_top = y0 + Inches(1.1)
            en_top = cn_top + Inches(1.0)
            prev = None
            for c, cw in zip(cells, wid):
                if c.get("dash"):
                    _box(s, x - Inches(0.3), dig_top, cw + Inches(0.6), dig_h, "−", NUM, INK, zh_f, en_f, lang="en-US")
                    x += cw; continue
                if c.get("bar"):
                    line(s, x + cw // 2, dig_top + Inches(0.08), x + cw // 2, dig_top + dig_h - Inches(0.05), SOFT, 1.5)
                    x += cw; prev = None; continue
                txt = c["pitch"] + ("·" if c["dur"].endswith(".") else "")
                _box(s, x - Inches(0.3), dig_top, cw + Inches(0.6), dig_h, txt, NUM, INK, zh_f, en_f, lang="en-US")
                cx = x + cw // 2 - (Inches(0.06) if c["dur"].endswith(".") else 0)
                if c.get("alter"):                     # numbered accidental, small and raised before the digit
                    _box(s, cx - Inches(0.42), dig_top - Inches(0.06), Inches(0.3), Inches(0.4),
                         {1: "#", 2: "x", -1: "b", -2: "bb"}[c["alter"]], 24, INK, zh_f, en_f, lang="en-US")
                for i in range(c["up"]):
                    dot(s, cx, dig_top + Inches(0.02) - i * Inches(0.12), INK)
                for i in range(c["down"]):
                    dot(s, cx, ul1 + Inches(0.12) + _UL[c["dur"]] * Inches(0.08) + i * Inches(0.12), INK)
                for i in range(_UL[c["dur"]]):
                    yy = ul1 + i * Inches(0.08)
                    line(s, x + Inches(0.1), yy, x + cw - Inches(0.1), yy, INK, 2.0)
                if prev is not None and prev.get("tie"):
                    arc(s, prev["cx"], cx, dig_top - Inches(0.2), INK)
                c["cx"] = cx
                if c.get("cn") and c["cn"] != "~":
                    _box(s, x - Inches(0.3), cn_top, cw + Inches(0.6), Inches(1.0), c["cn"], CN, INK, zh_f, en_f)
                    _box(s, x - Inches(0.7), en_top, cw + Inches(1.4), Inches(0.6), (c.get("en") or "").replace("_", " "), EN, SOFT,
                         zh_f, en_f, italic=F["en_italic"], bold=True, lang="en-US")
                elif c.get("cn") == "~":       # melisma line under the held syllable
                    line(s, x - cw // 2, cn_top + Inches(0.9), x + cw - Inches(0.12), cn_top + Inches(0.9), SOFT, 1.5)
                    if c.get("en"):
                        _box(s, x - Inches(0.7), en_top, cw + Inches(1.4), Inches(0.6), c["en"], EN, SOFT,
                             zh_f, en_f, italic=F["en_italic"], bold=True, lang="en-US")
                prev = c
                x += cw
            if system.get("en_line"):          # whole English line (no per-syllable alignment available)
                _box(s, M, en_top, W - 2 * M, Inches(0.6), system["en_line"], EN, SOFT, zh_f, en_f,
                     italic=F["en_italic"], bold=True, lang="en-US")
        _box(s, W - Inches(2.1), H - Inches(0.5), Inches(1.6), Inches(0.42), f"{k}/{len(song['slides'])}", 22, ACC,
             zh_f, en_f, align=PP_ALIGN.RIGHT, lang="en-US")
        if k == 1 or k == len(song["slides"]):
            _box(s, M, H - Inches(0.5), Inches(10.8), Inches(0.42), song["credit"], 16, SOFT, zh_f, en_f,
                 align=PP_ALIGN.LEFT, lang="en-US")
        out.append(s)
    return out



def song_from_score(rows, title_zh, title_en, key, credit, max_width_in=12.6, min_gap_in=0.66, break_beats=1.0,
                    break_on_label=False):
    """Score rows -> slide specs. The whole song is read as one stream and cut into phrases at
    rests of >= `break_beats`; a phrase takes the section label of the row where it ends.
    Over-wide phrases split at the barline nearest the middle. 2 lines per slide, new slide per section."""
    BEATS = {"16": .25, "8": .5, "4": 1, "2": 2}
    beats = lambda c: BEATS[c["dur"].rstrip(".")] * (1.5 if c["dur"].endswith(".") else 1)
    stream = []
    for r in rows:
        for c in r["cells"]:
            c = dict(c); c["label"] = r["label"]; stream.append(c)
        if stream and not stream[-1].get("bar"):
            stream.append(dict(bar=True, label=r["label"]))
    sung = lambda c: c.get("pitch") not in (None, "0")
    phrases, cur, rest_run, cur_label = [], [], 0.0, None
    for c in stream:
        if c.get("pitch") == "0":
            rest_run += beats(c); cur.append(c); continue
        if sung(c) and any(sung(x) for x in cur) and (rest_run >= break_beats or (break_on_label and c["label"] != cur_label)):
            phrases.append(cur); cur = []   # rest of >= 1 beat, or (handoff: sections are exact) a new section
        if sung(c):
            rest_run = 0.0; cur_label = c["label"]
        cur.append(c)
    phrases.append(cur)
    def tidy(cells):     # drop leading/trailing rests & bars, collapse double bars
        while cells and (cells[0].get("bar") or cells[0].get("pitch") == "0"): cells = cells[1:]
        while cells and (cells[-1].get("bar") or cells[-1].get("pitch") == "0" or cells[-1].get("dash")
                         and not any(sung(x) for x in cells[-3:])): cells = cells[:-1]
        out = []
        for c in cells:
            if c.get("bar") and out and out[-1].get("bar"): continue
            out.append(c)
        return out
    W_ = lambda c: 0.35 if c.get("bar") else (0.8 if c.get("dash") else _W[c["dur"]])
    width = lambda cells: sum(W_(c) for c in cells)
    def fits(cells):
        return sum(_cell_widths(cells)) <= max_width_in

    def split(cells):
        """DP over cut points: every line must fit; minimise cut penalties + lines."""
        if fits(cells):
            return [cells]
        cands = {0: 0.0}
        for j, c in enumerate(cells):
            if j == 0 or c.get("cn") in (None, "~") or not any(sung(x) for x in cells[:j]):
                continue
            k, bar = j - 1, False
            while k >= 0 and cells[k].get("bar"):
                bar = True; k -= 1
            prev = cells[k]
            # held across a barline (tie into this measure) counts as a phrase-ending hold
            q, crossed = k - 1, False
            while q >= 0 and cells[q].get("bar"):
                crossed = True; q -= 1
            tied_over = prev.get("cn") == "~" and crossed and q >= 0 and cells[q].get("tie")
            cands[j] = 0.0 if prev.get("pitch") == "0" else (1.0 if (prev.get("cn") == "~" and (beats(prev) >= 1 or tied_over)) or prev.get("dash")
                                                              else (3.0 if bar else 20.0))
            # a short note leading into the next barline is a pickup: a natural phrase start
            if c.get("dur") in ("8", "16", "8.") and not c.get("tie"):
                acc, m = 0.0, j
                while m < len(cells) and not cells[m].get("bar"):
                    if "dur" in cells[m]: acc += beats(cells[m])
                    m += 1
                if m < len(cells) and acc <= 1.0:
                    cands[j] = min(cands[j], 2.5)
        pos = sorted(cands) + [len(cells)]
        best = {0: (0.0, [])}
        for i, p0 in enumerate(pos):
            if p0 not in best: continue
            for p1 in pos[i + 1:]:
                seg = tidy(cells[p0:p1])
                if not seg or not fits(seg):
                    if seg and not fits(seg): break
                    continue
                cost = best[p0][0] + 0.3 + (cands.get(p1, 0.0) if p1 < len(cells) else 0.0)
                if p1 not in best or cost < best[p1][0]:
                    best[p1] = (cost, best[p0][1] + [seg])
        return best[len(cells)][1] if len(cells) in best else [cells]

    lines = []
    for ph in phrases:
        ph = tidy(ph)
        if not any(c.get("cn") not in (None, "~") for c in ph): continue
        label = [c for c in ph if sung(c)][-1]["label"]
        for part in split(ph):
            if any(c.get("cn") not in (None, "~") for c in part):
                lines.append(dict(label=label, cells=part))
    slides = []
    for ln in lines:
        lab = ln["label"] or {"en": "", "zh": ""}
        name = f"{title_zh} — {lab['en']} · {lab['zh']}" if lab["en"] else title_zh
        if slides and slides[-1]["label"] == name and len(slides[-1]["systems"]) < 2:
            slides[-1]["systems"].append(dict(cells=ln["cells"]))
        else:
            slides.append(dict(label=name, tag=lab["en"], chorus=lab["en"].startswith("CHORUS"), systems=[dict(cells=ln["cells"])]))
    # section badges: occurrence / total per kind, counted per section (not per slide)
    order_tags, prev = [], None
    for sl in slides:
        if sl["label"] != prev:
            order_tags.append(sl["tag"]); prev = sl["label"]
    bl = badge_texts(order_tags)
    i, prev = -1, None
    for sl in slides:
        if sl["label"] != prev:
            i += 1; prev = sl["label"]
        sl["badge"] = bl[i]
    return dict(key=key, credit=credit, slides=slides, title=title_zh, en_title=title_en)


def song_from_handoff(h, max_width_in=12.6):
    """Projection handoff JSON (schema lyric-handoff/1, from the lyric translator's `handoff.py events`)
    -> slide spec. Music and lyrics are taken as given; only the line breaks are decided here."""
    if h.get("schema") != "lyric-handoff/1":
        raise ValueError("not a lyric-handoff/1 events file")
    rows = []
    for i, sec in enumerate(h["sections"]):
        label = {"en": sec["label"].upper(), "zh": f"#{i}"}       # pass index keeps repeated sections apart
        cells = []
        for k, m in enumerate(sec["measures"]):
            if k:
                cells.append({"bar": True})
            for e in m["events"]:
                if e["underlines"] > 2:
                    raise ValueError(f"{e['id']}: 32nd notes are not supported on slides")
                if e.get("tuplet"):
                    raise ValueError(f"{e['id']}: tuplets are not supported on slides yet")
                c = {"pitch": str(e["number"]), "up": max(e["octave"], 0), "down": max(-e["octave"], 0),
                     "alter": e["alter"], "dur": {0: "4", 1: "8", 2: "16"}[e["underlines"]] + ("." if e["dot"] else ""),
                     "tie": bool(e["tie_next"]), "cn": None, "en": None, "id": e["id"]}
                if not e["rest"]:
                    if e["zh"]:
                        c["cn"] = e["zh"]
                    elif e["continuation"] or e["melisma"]:
                        c["cn"] = "~"
                    if e.get("en"):
                        c["en"] = e["en"] + ("-" if e.get("en_con") == "d" else "")
                cells.append(c)
                cells += [{"dash": True} for _ in range(e["dashes"])]
        rows.append({"label": label, "cells": cells})
    key = h.get("key_label") or f"1 = {h.get('tonic', '')}"
    song = song_from_score(rows, h["title"], h.get("title_en", ""), key, h.get("credits", ""), max_width_in=max_width_in,
                           break_on_label=True)
    song["handoff"] = {k: h.get(k) for k in ("source_sha256", "lyric_version", "lyric_status")}
    return song
