"""Build a whole Sunday-service deck from a service.yaml + the church's weekly template .pptx.

    python3 build_service.py service.yaml out.pptx [--profile oxblood-library]

Reading slides (读) are parchment; songs, covers and blanks (唱 / 封面) use the chosen dark profile.
All paths inside service.yaml are relative to the yaml file. See references/service-spec.md.
"""
import argparse, copy, json, os, re, sys
from functools import lru_cache
import yaml
from lxml import etree
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import songs
from songs import STYLES, import_slides, jianpu_slides, styled_lyric_slides, song_from_handoff

VERSION = "0.4.2"

ap = argparse.ArgumentParser()
ap.add_argument("service"); ap.add_argument("out")
ap.add_argument("--profile", help="override the profile named in service.yaml")
args = ap.parse_args()
BASE = os.path.dirname(os.path.abspath(args.service))
SPEC = yaml.safe_load(open(args.service, encoding="utf-8"))
path = lambda p: p if os.path.isabs(p) else os.path.join(BASE, p)

PROFILE_NAME = args.profile or SPEC.get("profile") or STYLES.get("default_profile", "oxblood-library")
P = STYLES["profiles"][PROFILE_NAME]
if P.get("service") is False:
    sys.exit(f"profile {PROFILE_NAME} is a light lyric-only profile; pick a dark profile for a whole service")
hexv = lambda h: h.lstrip("#").upper()
rgb = lambda h: RGBColor.from_string(hexv(h))

def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))

R = STYLES["reading"]
PARCH, INK, GREY = rgb(R["bg"]), rgb(R["ink"]), rgb(R["num"])
CREAM, DEEP, GOLD, SOFT = rgb(P["zh"]), rgb(P["verse_bg"]), rgb(P["accent"]), rgb(P["en"])
MID = rgb(P.get("cover_top") or mix(P["verse_bg"], P["chorus_bg"], 0.65))
FONTS = STYLES["fonts"]["pptx"]
EA, LAT = FONTS["zh"], FONTS["en"]

if SPEC.get("template"):
    prs = Presentation(path(SPEC["template"]))
else:                                            # song-only decks need no church template (small files)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
T = list(prs.slides)

def t(n):
    if not T:
        sys.exit("this step reuses a template slide, but service.yaml has no template")
    return T[n - 1]
LAYOUT = t(SPEC["layout_slide"]).slide_layout if SPEC.get("layout_slide") else next(
    (l for l in prs.slide_layouts if re.search(r"blank|空白", l.name, re.I)), prs.slide_layouts[-1])
used = set()

# ---------------------------------------------------------------- slide plumbing
def dup(src):
    new = prs.slides.add_slide(src.slide_layout)
    rmap = {}
    for rId, rel in src.part.rels.items():
        if "notesSlide" in rel.reltype or "slideLayout" in rel.reltype:
            continue
        rmap[rId] = (new.part.relate_to(rel.target_ref, rel.reltype, is_external=True) if rel.is_external
                     else new.part.relate_to(rel.target_part, rel.reltype))
    xml = etree.tostring(src._element).decode()
    xml = re.sub(r'(r:(?:embed|id|link|pict)=")(rId\d+)(")',
                 lambda m: m.group(1) + rmap.get(m.group(2), m.group(2)) + m.group(3), xml)
    el = etree.fromstring(xml)
    for c in list(new._element): new._element.remove(c)
    for c in el: new._element.append(c)
    for k in ("shapes", "placeholders", "background"): new.__dict__.pop(k, None)
    return new

def take(n):
    """template slide n; a second use gets a copy"""
    if n in used:
        return dup(t(n))
    used.add(n)
    return t(n)

def blank_new():
    s = prs.slides.add_slide(LAYOUT)
    for sh in list(s.shapes): sh._element.getparent().remove(sh._element)
    return s

def clear_shapes(s):
    for sh in list(s.shapes): sh._element.getparent().remove(sh._element)

def set_text(shape, text, size):
    """replace the text of a template text box, keeping its first run's formatting"""
    tf = shape.text_frame
    p0 = tf.paragraphs[0]; r0 = p0.runs[0]._r
    proto = copy.deepcopy(p0._p)
    for p in list(tf.paragraphs): p._p.getparent().remove(p._p)
    for line in text.split("\n"):
        p = copy.deepcopy(proto)
        for r in p.findall(qn("a:r")) + p.findall(qn("a:br")) + p.findall(qn("a:fld")): p.remove(r)
        r = copy.deepcopy(r0); r.find(qn("a:t")).text = line
        if size: r.find(qn("a:rPr")).set("sz", str(int(size * 100)))
        end = p.find(qn("a:endParaRPr"))
        (end.addprevious(r) if end is not None else p.append(r))
        tf._txBody.append(p)

def alpha(fill_el, val):
    etree.SubElement(fill_el.find(".//" + qn("a:srgbClr")), qn("a:alpha")).set("val", str(val))

def rect(s, x, y, w, h, color, a=100000):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    r.fill.solid(); r.fill.fore_color.rgb = color; alpha(r._element.spPr, a)
    r.line.fill.background(); r.shadow.inherit = False
    return r

def font(run, size, color, bold=False, sup=False):
    f = run.font; f.size = Pt(size); f.bold = bold; f.color.rgb = color
    rpr = run._r.get_or_add_rPr(); rpr.set("lang", "zh-CN")
    if sup: rpr.set("baseline", "30000")
    for tag, face in (("a:latin", LAT), ("a:ea", EA), ("a:cs", LAT)):
        e = rpr.find(qn(tag))
        if e is None: e = etree.SubElement(rpr, qn(tag))
        e.set("typeface", face)

# ---------------------------------------------------------------- reading slides (读)
LINE = 1.25                                      # line pitch = 1.25 x font size (fixed, so estimates match)
TOP = Inches(0.8)
BOX_TOP, BOX_H = Inches(0.95), Inches(6.3)
EXTRA = Inches(0.5)                              # header grows to two lines when needed

def header_tall(section, source):
    w = lambda s, size: sum(size * (0.55 if ord(ch) < 0x2E80 else 1.0) for ch in s)
    return w(section, 40) + w("　｜　" + (source or "").strip(), 30) > (prs.slide_width - Inches(2.7)) / 12700

def header_band(s, section, source, page, tall=False):
    W = prs.slide_width; h = TOP + (EXTRA if tall else 0)
    rect(s, 0, 0, W, h, DEEP)
    tb = s.shapes.add_textbox(Inches(0.5), 0, W - Inches(2.6), h)
    tb.text_frame.word_wrap = True; tb.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tb.text_frame.paragraphs[0]
    r = p.add_run(); r.text = section; font(r, 40, GOLD, bold=True)
    if source and source.strip():
        r = p.add_run(); r.text = "　｜　" + source; font(r, 30, CREAM)
    pg = s.shapes.add_textbox(W - Inches(2.3), 0, Inches(1.8), h)
    pg.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    pp = pg.text_frame.paragraphs[0]; pp.alignment = PP_ALIGN.RIGHT
    r = pp.add_run(); r.text = page; font(r, 22, CREAM)

def reading(header, footer, page, paras, size=44, align=PP_ALIGN.LEFT, gap=0.35, tall=False):
    s = blank_new()
    W = prs.slide_width
    s.background.fill.solid(); s.background.fill.fore_color.rgb = PARCH
    ex = EXTRA if tall else 0
    tb = s.shapes.add_textbox(Inches(0.55), BOX_TOP + ex, W - Inches(1.1), BOX_H - ex)
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    bp = tf._txBody.find(qn("a:bodyPr"))
    for c in list(bp): bp.remove(c)
    etree.SubElement(bp, qn("a:noAutofit"))
    for i, segs in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = Pt(size * LINE); p.space_after = Pt(size * gap)
        if i and segs and segs[0][1] == "tag":
            p.space_before = Pt(size * 0.45)         # breathing room where the speaker changes
        for text, kind in segs:
            r = p.add_run(); r.text = text
            if kind == "n": font(r, size * 0.6, GREY, sup=True)
            elif kind == "q": font(r, size, INK, bold=True)
            else: font(r, size, INK)                 # body and 【role】 tags: one colour, one weight
    header_band(s, header, footer, page, tall)
    s._kind = "read"
    return s

def em_width(segs, size):
    return sum((0.6 if kind == "n" else 1.0) * (0.55 if ord(ch) < 0x2E80 else 1.0)
               for text, kind in segs for ch in text)

def est_height(paras, size, gap, per_line):
    lines = sum(max(1, -(-em_width(p, size) // per_line)) for p in paras)
    return lines * size * LINE + (len(paras) - 1) * size * gap

def refs(items):
    """whole-passage reference for the header: 诗 95:7b-11；林前 10:3-6"""
    groups = []
    for it in items:
        r = it.get("_ref")
        if not r:
            if it.get("src") and (not groups or groups[-1][0] != it["src"]):
                groups.append((it["src"], None))
            continue
        book, ch, v = r
        if groups and groups[-1][0] == (book, ch): groups[-1][1].append(v)
        else: groups.append(((book, ch), [v]))
    out = []
    for key, vs in groups:
        if vs is None: out.append(key); continue
        (book, ch), lo, hi = key, vs[0], vs[-1]
        out.append(f"{book} {ch}:{lo}" + ("" if lo == hi else f"-{hi}"))
    return "；".join(out)

ROLE = {"主席": "主席", "会众": "会众", "齐": "齐", "齐声": "齐"}

def to_paras(items):
    paras, prev = [], object()
    for it in items:
        role = ROLE.get(it["role"], str(it["role"]).strip()) if it.get("role") else None   # unknown roles shown as given
        segs = []
        if role and role != prev:
            segs.append(("【" + role + "】", "tag"))
        prev = role
        if it.get("num"): segs.append((it["num"] + " ", "n"))
        segs.append((it["text"], "q" if it.get("bold") else "b"))
        paras.append(segs)
    return paras

def norm_items(raw):
    out = []
    for it in raw:
        it = dict(it)
        if it.get("ref"):
            m = re.match(r"^\s*(\S+?)\s*(\d+)\s*[:：]\s*(\d+[a-z]?)\s*$", str(it["ref"]))
            if not m: sys.exit(f"bad ref {it['ref']!r} (use e.g. '诗 95:7b')")
            it["_ref"] = (m.group(1), int(m.group(2)), m.group(3))
            it.setdefault("num", re.match(r"\d+", m.group(3)).group(0))
        if it.get("num") is not None: it["num"] = str(it["num"])
        out.append(it)
    return out

def pack(st):
    items = norm_items(st["items"])
    size = st.get("size", 44); gap = st.get("gap", 0.35)
    align = {"center": PP_ALIGN.CENTER, "left": PP_ALIGN.LEFT}[st.get("align", "left")]
    footer = st.get("source")
    if footer is None: footer = refs(items) + st.get("suffix", "")
    tall = header_tall(st["header"], footer)
    per_line = (prs.slide_width - Inches(1.1) - Emu(182880)) / Pt(size) - 0.8
    avail = (BOX_H - (EXTRA if tall else 0)) / 12700 - 14
    H = lambda a, b: est_height(to_paras(items[a:b]), size, gap, per_line)
    pages, cur = [], 0                           # greedy page count ...
    for i in range(1, len(items) + 1):
        if i - cur > 1 and H(cur, i) > avail:
            pages.append((cur, i - 1)); cur = i - 1
    pages.append((cur, len(items)))
    k, n = len(pages), len(items)

    @lru_cache(None)
    def best(i, kk):                             # ... then even out the pages (no orphan slides)
        if kk == 1:
            h = H(i, n); return (h * h if h <= avail else 1e18, (n,))
        res = (1e18, ())
        for j in range(i + 1, n - kk + 2):
            h = H(i, j)
            if h > avail: break
            sub = best(j, kk - 1)
            res = min(res, (h * h + sub[0], (j,) + sub[1]))
        return res
    if k > 1:
        m, cuts = best(0, k)
        if m < 1e18:
            pages, a = [], 0
            for c in cuts: pages.append((a, c)); a = c
    return [reading(st["header"], footer, f"{i}/{len(pages)}", to_paras(items[a:b]), size, align, gap, tall)
            for i, (a, b) in enumerate(pages, 1)]

# ---------------------------------------------------------------- dark slides (唱 / 封面)
def gradient(s):
    f = s.background.fill; f.gradient(); f.gradient_angle = 90
    st = f.gradient_stops
    st[0].color.rgb = MID; st[0].position = 0.0
    st[1].color.rgb = DEEP; st[1].position = 1.0

def darken(s):
    """template slide -> profile: gradient ground, drop full-bleed photos, strip glow/outline,
    recolour text (template yellow = English -> profile 'en', all else -> cream). Text untouched."""
    W, H = prs.slide_width, prs.slide_height
    for sh in list(s.shapes):
        if sh.shape_type == 13 and sh.width >= W * 0.9 and sh.height >= H * 0.9:
            sh._element.getparent().remove(sh._element)
    gradient(s)
    for el in list(s._element.iter(qn("a:rPr"), qn("a:endParaRPr"), qn("a:defRPr"))):
        for child in list(el):
            if child.tag in (qn("a:effectLst"), qn("a:effectDag"), qn("a:ln")):
                el.remove(child)
    cover_runs = []
    for r in list(s._element.iter(qn("a:rPr"))):
        if int(r.get("sz", "0")) >= 9600:
            r.set("b", "0")                      # KaiTi has no bold: faux bold smears at cover size
            cover_runs.append(r)
    for sh in s.shapes:
        tfs = [sh.text_frame] if sh.has_text_frame else []
        if getattr(sh, "has_table", False) and sh.has_table:
            tfs += [c.text_frame for row in sh.table.rows for c in row.cells]
        for tf in tfs:
            for p in tf.paragraphs:
                for r in p.runs:
                    try: cur = r.font.color.rgb if r.font.color and r.font.color.type is not None else None
                    except Exception: cur = None
                    r.font.color.rgb = SOFT if cur is not None and str(cur).upper() == "FFFF00" else CREAM
                    rpr = r._r.get_or_add_rPr()
                    for tag, face in (("a:latin", LAT), ("a:ea", EA), ("a:cs", LAT)):
                        e = rpr.find(qn(tag))
                        if e is None: e = etree.SubElement(rpr, qn(tag))
                        e.set("typeface", face)
                        for k in ("panose", "pitchFamily", "charset"): e.attrib.pop(k, None)
    for r in cover_runs:
        cover_shadow(r)
    return s

def cover_shadow(r):
    """faint drop shadow that lifts a big cover title off the gradient (no glow, no outline)"""
    eff = etree.Element(qn("a:effectLst"))
    sh = etree.SubElement(eff, qn("a:outerShdw"), blurRad="38100", dist="25400", dir="2700000",
                          algn="tl", rotWithShape="0")
    shadow = mix(P["verse_bg"], "#000000", 0.5).lstrip("#")
    etree.SubElement(etree.SubElement(sh, qn("a:srgbClr"), val=shadow), qn("a:alpha"), val="50000")
    anchor = next((r.find(qn(tg)) for tg in ("a:highlight", "a:uLnTx", "a:uLn", "a:uFillTx", "a:uFill", "a:latin",
                   "a:ea", "a:cs", "a:sym", "a:hlinkClick", "a:hlinkMouseOver", "a:rtl", "a:extLst")
                   if r.find(qn(tg)) is not None), None)
    (anchor.addprevious(eff) if anchor is not None else r.append(eff))

def dark_blank(s):
    s.background.fill.solid(); s.background.fill.fore_color.rgb = DEEP
    return s

def textbox(s, y, h, text, size, color, bold=False, align=PP_ALIGN.CENTER, x=None, w=None):
    W = prs.slide_width
    b = s.shapes.add_textbox(x if x is not None else Inches(0.5), y, w or (W - Inches(1.0)), h)
    b.text_frame.word_wrap = True
    p = b.text_frame.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = text; font(r, size, color, bold=bold)

def hymn_title(first, st):
    """title page for an imported hymn: title, 赞美诗 number, credit (read from its first slide unless given)"""
    texts = {sh.name: sh.text_frame.text.strip() for sh in first.shapes if sh.has_text_frame}
    title = st.get("title") or texts.get("Rectangle 2", "")
    number = st.get("number") or next((v for v in texts.values() if v.startswith("赞美诗")), "")
    credit = st.get("credit") or " ".join(next((v for v in texts.values() if v.startswith("Written")), "").split())
    s = blank_new(); gradient(s)
    W, H = prs.slide_width, prs.slide_height
    textbox(s, Inches(2.2), Inches(1.2), title, 72, CREAM, bold=True)
    rect(s, (W - Inches(1.0)) // 2, Inches(3.6), Inches(1.0), Emu(12700), GOLD)
    if number: textbox(s, Inches(3.8), Inches(0.8), number, 36, SOFT)
    if credit: textbox(s, H - Inches(0.55), Inches(0.42), credit, 16, SOFT, align=PP_ALIGN.LEFT, x=Inches(0.5), w=Inches(11.5))
    s._kind = "song"
    return s

def slide_nums(v):
    if isinstance(v, int): return [v]
    out = []
    for part in str(v).split(","):
        a, _, b = part.strip().partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out

# ---------------------------------------------------------------- steps
KEEP_TRANSITION, IMAGE_PAGES = set(), set()
PROVENANCE = []                                  # songs built from a handoff: what they were built from

def step(st):
    ty = st["type"]
    if ty == "template":
        out = []
        for n in slide_nums(st["slide"]):
            style = st.get("style", "dark")
            if st.get("text"):                   # reuse a cover, swap its title
                s = dup(t(n))
                box = next(sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip())
                set_text(box, st["text"], st.get("size"))
            else:
                s = take(n)
            if style == "dark": darken(s)
            elif style == "blank": dark_blank(s)
            elif style == "keep": IMAGE_PAGES.add(id(s._element))
            for a, b in (st.get("resize") or {}).items():
                for r in s._element.iter(qn("a:rPr"), qn("a:endParaRPr")):
                    if r.get("sz") == str(int(a) * 100): r.set("sz", str(int(b) * 100))
            if st.get("keep_transition"): KEEP_TRANSITION.add(id(s._element))
            out.append(s)
        return out
    if ty == "reading":
        return pack(st)
    if ty == "hymn":
        hs = import_slides(prs, path(st["file"]), LAYOUT)
        for s in hs:
            darken(s); s._kind = "hymn"
        return ([hymn_title(hs[0], st)] if st.get("title_page", True) else []) + hs
    if ty == "jianpu" and st.get("handoff"):    # approved score from the lyric translator
        h = json.load(open(path(st["handoff"]), encoding="utf-8"))
        status = h.get("lyric_status")
        if status not in ("text-approved", "performed") and not st.get("allow_draft"):
            sys.exit(f"{st['handoff']}: lyric-status is {status!r}; approve it in the translator first "
                     "(or set allow_draft: true for a rehearsal deck)")
        if st.get("score"):
            import hashlib
            now = hashlib.sha256(open(path(st["score"]), "rb").read()).hexdigest()
            if now != h.get("source_sha256"):
                sys.exit(f"{st['handoff']} was exported from an older {st['score']}; rerun handoff.py events")
        song = song_from_handoff(h)
        out = jianpu_slides(prs, LAYOUT, song, PROFILE_NAME)
        for s in out: s._kind = "song"
        PROVENANCE.append({"title": h["title"], "handoff": st["handoff"], "score": st.get("score"),
                           "score_sha256": h.get("source_sha256"), "lyric_version": h.get("lyric_version"),
                           "lyric_status": status, "_slides": out})
        return out
    if ty in ("jianpu", "lyrics"):
        song = json.load(open(path(st["song"]), encoding="utf-8"))
        if "title_page" in st:                    # e.g. the second song of a medley: no title page of its own
            song["title_page"] = bool(st["title_page"])
        fn = jianpu_slides if ty == "jianpu" else styled_lyric_slides
        out = fn(prs, LAYOUT, song, PROFILE_NAME)
        for s in out: s._kind = "song"
        return out
    if ty == "cover":                            # 环节 cover generated in the profile style (no template slide needed)
        s = blank_new(); gradient(s)
        W, H = prs.slide_width, prs.slide_height
        title, sub = str(st["text"]), st.get("subtitle")
        em = sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in title)
        size = st.get("size") or max(72, min(138, int(860 / max(em, 1))))   # template covers are 138pt
        th, sh_ = Pt(size * 1.3), (Pt(40 * 1.4) + Inches(0.3) if sub else 0)
        y = int((H - th - sh_) / 2)
        b = s.shapes.add_textbox(Inches(0.5), y, W - Inches(1.0), th)
        b.text_frame.word_wrap = True; b.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = b.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = title; font(r, size, CREAM)
        cover_shadow(r._r.get_or_add_rPr())
        if sub:
            textbox(s, y + th + Inches(0.3), Pt(40 * 1.4), str(sub), 40, SOFT)
        return [s]
    if ty == "image":
        s = blank_new()
        s.shapes.add_picture(path(st["file"]), 0, 0, prs.slide_width, prs.slide_height)
        IMAGE_PAGES.add(id(s._element)); s._kind = "image"
        return [s]
    if ty == "blank":
        return [dark_blank(blank_new())]
    sys.exit(f"unknown step type {ty!r}")

order = []
for st in SPEC["service"]:
    made = step(st)
    if st.get("transition"):                     # per-step override: cut | fade
        if st["transition"] not in ("cut", "fade"): sys.exit(f"transition must be cut or fade, not {st['transition']!r}")
        for s in made: s._transition = st["transition"]
    order += made

# ---------------------------------------------------------------- transitions
# songs, hymns, readings and song title pages: straight cut (text is there the moment the operator clicks);
# covers / blanks / image pages: 0.75 s fade marks a change of 环节; flagged slides keep the template's own.
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent"
for sl in order:
    el = sl._element
    if id(el) in KEEP_TRANSITION: continue
    for old in el.findall(qn("p:transition")): el.remove(old)
    for old in el.findall(MC):
        if old.find(".//" + qn("p:transition")) is not None: el.remove(old)
    cut = getattr(sl, "_kind", None) in ("song", "read", "hymn")
    cut = {"cut": True, "fade": False}.get(getattr(sl, "_transition", None), cut)
    if not cut:
        tr = etree.Element(qn("p:transition"), spd="med"); etree.SubElement(tr, qn("p:fade"))
        anchor = el.find(qn("p:clrMapOvr"))
        (anchor if anchor is not None else el.find(qn("p:cSld"))).addnext(tr)

# ---------------------------------------------------------------- theme colours + fonts
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
THEME = [("dk1", R["ink"]), ("lt1", P["zh"]), ("dk2", P["verse_bg"]), ("lt2", R["bg"]),
         ("accent1", P["chorus_bg"]), ("accent2", P.get("bridge_bg", P["chorus_bg"])), ("accent3", P["accent"]),
         ("accent4", R["num"]), ("accent5", "#" + hexv(MID.__str__())), ("accent6", P["en"]),
         ("hlink", P["accent"]), ("folHlink", P["en"])]
SLOT = {"dk1": "tx1", "lt1": "bg1", "dk2": "tx2", "lt2": "bg2"}
TO_SCHEME = {}
for slot, h in THEME:
    if slot in ("hlink", "folHlink"): continue
    TO_SCHEME.setdefault(hexv(h), SLOT.get(slot, slot))

def theme_xml(blob):
    root = etree.fromstring(blob)
    cs = root.find(f".//{{{A}}}clrScheme")
    if cs is not None:
        cs.set("name", "崇拜 " + P.get("label", PROFILE_NAME))
        for c in list(cs): cs.remove(c)
        for slot, h in THEME:
            etree.SubElement(etree.SubElement(cs, f"{{{A}}}{slot}"), f"{{{A}}}srgbClr", val=hexv(h))
    fs = root.find(f".//{{{A}}}fontScheme")
    if fs is not None:
        fs.set("name", f"崇拜 {EA}+{LAT}")
        for c in list(fs): fs.remove(c)
        for kind in ("majorFont", "minorFont"):
            f = etree.SubElement(fs, f"{{{A}}}{kind}")
            etree.SubElement(f, f"{{{A}}}latin", typeface=LAT)
            etree.SubElement(f, f"{{{A}}}ea", typeface=EA)
            etree.SubElement(f, f"{{{A}}}cs", typeface=LAT)
            for sc in ("Hans", "Hant"):
                etree.SubElement(f, f"{{{A}}}font", script=sc, typeface=EA)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

def freeze_scheme_colours(sl):
    """'keep' pages must look exactly as the template did: pin their theme-colour references to the
    template theme's values before the theme is re-skinned."""
    master = sl.slide_layout.slide_master
    theme = next(r.target_part for r in master.part.rels.values() if r.reltype.endswith("/theme"))
    root = etree.fromstring(theme.blob)
    cs = root.find(f".//{{{A}}}clrScheme")
    val = {}
    for c in cs:
        v = c[0].get("val") if c[0].tag.endswith("srgbClr") else c[0].get("lastClr")
        val[etree.QName(c).localname] = v
    cmap = master._element.find(qn("p:clrMap")).attrib
    for e in list(sl._element.iter(f"{{{A}}}schemeClr")):
        name = cmap.get(e.get("val"), e.get("val"))
        if name in val and val[name]:
            n = etree.Element(f"{{{A}}}srgbClr", val=val[name])
            for ch in e: n.append(ch)
            e.addprevious(n); e.getparent().remove(e)

for sl in order:
    if id(sl._element) in IMAGE_PAGES and getattr(sl, "_kind", None) != "image":
        freeze_scheme_colours(sl)

for part in prs.part.package.iter_parts():
    if "/ppt/theme/theme" in str(part.partname):
        part._blob = theme_xml(part.blob)

for sl in order:                                  # colours -> theme slots, fonts -> theme fonts (easy to re-skin)
    if id(sl._element) in IMAGE_PAGES: continue
    for c in list(sl._element.iter(f"{{{A}}}srgbClr")):
        slot = TO_SCHEME.get(c.get("val", "").upper())
        if slot:
            n = etree.Element(f"{{{A}}}schemeClr", val=slot)
            for ch in c: n.append(ch)
            c.addprevious(n); c.getparent().remove(c)
    for tag, ref in (("latin", "+mn-lt"), ("ea", "+mn-ea"), ("cs", "+mn-cs")):
        for e in sl._element.iter(f"{{{A}}}{tag}"):
            if e.getparent().tag in (f"{{{A}}}rPr", f"{{{A}}}endParaRPr", f"{{{A}}}defRPr"):
                e.set("typeface", ref)
                for k in ("panose", "pitchFamily", "charset"): e.attrib.pop(k, None)

# ---------------------------------------------------------------- final slide order
lst = prs.slides._sldIdLst
by_part = {prs.part.related_part(x.rId): x for x in list(lst)}
keep = [by_part[s.part] for s in order]
assert len(set(map(id, keep))) == len(keep), "a slide appears twice in the service"
for x in list(lst):
    lst.remove(x)
    if x not in keep: prs.part.drop_rel(x.rId)
for x in keep: lst.append(x)
# provenance travels inside the deck as a custom document property (File > Properties > Custom),
# so a library check can find songs whose approved score changed after the deck was built
def set_custom_property(prs, name, value):
    from xml.sax.saxutils import escape
    from pptx.opc.package import Part
    from pptx.opc.packuri import PackURI
    RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
    CP = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
    VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
    pkg = prs.part.package
    old = next((r for r in pkg._rels.values() if r.reltype == RT), None)
    if old is not None:
        root = etree.fromstring(old.target_part.blob)
    else:
        root = etree.Element(f"{{{CP}}}Properties", nsmap={None: CP, "vt": VT})
    for p in root.findall(f"{{{CP}}}property"):
        if p.get("name") == name:
            root.remove(p)
    pid = max([int(p.get("pid", "1")) for p in root.findall(f"{{{CP}}}property")] + [1]) + 1
    prop = etree.SubElement(root, f"{{{CP}}}property", fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}",
                            pid=str(pid), name=name)
    etree.SubElement(prop, f"{{{VT}}}lpwstr").text = value
    blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    if old is not None:
        old.target_part._blob = blob
    else:
        part = Part(PackURI("/docProps/custom.xml"),
                    "application/vnd.openxmlformats-officedocument.custom-properties+xml", pkg, blob)
        pkg.relate_to(part, RT)

out_dir = os.path.dirname(os.path.abspath(args.out))
def rel(p):
    if not p: return None
    try: return os.path.relpath(path(p), out_dir).replace(os.sep, "/")
    except ValueError: return os.path.abspath(path(p))
pos = {id(s._element): i for i, s in enumerate(order, 1)}
prov = [{**{k: v for k, v in e.items() if k != "_slides"}, "handoff": rel(e["handoff"]), "score": rel(e["score"]),
         "slides": [pos[id(e["_slides"][0]._element)], pos[id(e["_slides"][-1]._element)]]} for e in PROVENANCE]
set_custom_property(prs, "worship-slides", json.dumps({"tool": "worship-slides", "version": VERSION,
                                                       "profile": PROFILE_NAME, "songs": prov}, ensure_ascii=False))
prs.save(args.out)
print(f"slides: {len(keep)}  profile: {PROFILE_NAME}  ->  {args.out}")
