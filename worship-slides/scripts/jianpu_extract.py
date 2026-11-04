"""Extract jianpu (numbered notation) + CN/EN lyrics from a vector PDF score
(staff + jianpu + CN + EN layout, as produced for 'The God We Love V6.5').

Output: list of rows; each row = dict(label, cells=[...]) where a cell is
  {"bar": True}
  {"dash": True}
  {"pitch": "5", "up": 1, "down": 0, "dur": "8", "tie": False, "cn": "我", "en": "We"}
"""
import re, unicodedata, logging
import pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)
LABEL_RE = re.compile(r"^(VERSE|CHORUS|BRIDGE|TAG|ENDING|INTRO|OUTRO|REFRAIN|INTERLUDE|PRE-CHORUS)$")


def _norm(t):
    return unicodedata.normalize("NFKC", t)


def extract(path):
    rows = []
    label = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            chars = page.chars
            digits = [c for c in chars if c["text"] in "01234567−" and "Times" in c["fontname"]
                      and c["size"] > 9]
            # jianpu rows = digit chars sharing a 'top'
            tops = sorted({round(c["top"], 1) for c in digits})
            row_tops = []
            for t in tops:
                n = sum(1 for c in digits if abs(c["top"] - t) < 0.6)
                if n >= 3 and (not row_tops or t - row_tops[-1] > 20):
                    row_tops.append(t)
            words = page.extract_words(keep_blank_chars=False)
            curves = page.curves
            hlines = [l for l in page.lines if abs(l["top"] - l["bottom"]) < 0.3]
            vlines = [l for l in page.lines if abs(l["x0"] - l["x1"]) < 0.3]
            rects = page.rects
            prev_y = 0
            for y in row_tops:
                # section label between previous row and this one (glyphs may contain private-use chars)
                for t in sorted({round(w["top"]) for w in words if prev_y + 20 < w["top"] < y - 10}):
                    line = " ".join(w["text"] for w in sorted([w for w in words if abs(w["top"] - t) < 4], key=lambda w: w["x0"]))
                    line = _norm(re.sub(r"[\ue000-\uf8ff]", "", line)).replace("CH ORUS", "CHORUS")
                    m = re.search(r"(VERSE|CHORUS|BRIDGE|TAG|ENDING|INTRO)\s*(\d*)\s*·\s*(\S+)", line)
                    if m:
                        label = dict(en=(m.group(1) + " " + m.group(2)).strip(), zh=m.group(3).replace("∕", "／"))
                prev_y = y
                row = [c for c in digits if abs(c["top"] - y) < 0.6]
                bottom = max(c["bottom"] for c in row)
                cells = []
                for c in sorted(row, key=lambda c: c["x0"]):
                    cx = (c["x0"] + c["x1"]) / 2
                    if c["text"] == "−":
                        cells.append(dict(dash=True, x=cx)); continue
                    dots = [d for d in curves if d["x1"] - d["x0"] < 2.5 and d["bottom"] - d["top"] < 2.5]
                    up = sum(1 for d in dots if abs((d["x0"] + d["x1"]) / 2 - cx) < 2.5 and c["top"] - 9 < d["bottom"] <= c["top"] + 0.5)
                    down = sum(1 for d in dots if abs((d["x0"] + d["x1"]) / 2 - cx) < 2.5 and bottom + 1.5 <= d["top"] < bottom + 10)
                    aug = any(0 <= d["x0"] - c["x1"] < 4 and c["top"] + 2 < (d["top"] + d["bottom"]) / 2 < bottom - 2 for d in dots)
                    uls = {round(l["top"], 1) for l in hlines
                           if l["x0"] - 1 < cx < l["x1"] + 1 and bottom - 2 < l["top"] < bottom + 4}
                    u = len(uls)
                    dur = {0: "4", 1: "8", 2: "16"}[min(u, 2)] + ("." if aug else "")
                    cells.append(dict(pitch=c["text"], up=up, down=down, dur=dur, tie=False, x=cx, x0=c["x0"],
                                      cn=None, en=None))
                # barlines
                for l in vlines:
                    if l["top"] < y + 2 and l["bottom"] > bottom - 2 and l["bottom"] - l["top"] < 30:
                        cells.append(dict(bar=True, x=l["x0"]))
                cells.sort(key=lambda c: c["x"])
                # drop leading/duplicate barlines
                clean = []
                for c in cells:
                    if c.get("bar") and (not clean or clean[-1].get("bar")):
                        continue
                    clean.append(c)
                cells = clean
                notes = [c for c in cells if "pitch" in c]
                # ties / slurs: wide flat curves just above the row
                for t in curves:
                    if t["x1"] - t["x0"] > 5 and y - 12 < t["top"] < y - 2:
                        a = min(notes, key=lambda n: abs(n["x"] - t["x0"]))
                        a["tie"] = True
                # CN lyrics (rests never carry lyrics)
                sung = [n for n in notes if n["pitch"] != "0"]
                for ch in chars:
                    if y + 10 < ch["top"] < y + 26 and "Noto" in ch["fontname"]:
                        ccx = (ch["x0"] + ch["x1"]) / 2
                        n = min(sung, key=lambda n: abs(n["x"] - ccx))
                        if abs(n["x"] - ccx) < 8:
                            n["cn"] = (n["cn"] or "") + _norm(ch["text"]); n["cn_x0"] = ch["x0"]
                # EN lyrics: a word starts at the x0 of its CN syllable
                ens = sorted([w for w in words if y + 30 < w["top"] < y + 46], key=lambda w: w["x0"])
                hy = [r for r in rects if y + 40 < r["top"] < y + 50 and r["x1"] - r["x0"] < 4]
                for w in ens:
                    cands = [n for n in sung if n.get("cn_x0") is not None]
                    n = min(cands, key=lambda n: abs(n["cn_x0"] - w["x0"])) if cands else None
                    if n is None or abs(n["cn_x0"] - w["x0"]) > 4:
                        n = min(sung, key=lambda n: abs(n["x"] - (w["x0"] + 3)))
                    txt = w["text"]
                    if any(w["x1"] < h["x0"] < w["x1"] + 14 for h in hy):
                        txt += "-"
                    if any(w["x0"] - 14 < h["x1"] < w["x0"] for h in hy):
                        txt = "-" + txt
                    n["en"] = txt if not n["en"] else n["en"] + " " + txt
                # melisma: tied continuation notes with no lyric
                for i, b in enumerate(sung):
                    if b["cn"] is None and (i > 0 or rows):
                        b["cn"] = "~"
                # tie carried over from the previous row
                if rows and sung and sung[0]["cn"] is None:
                    pn = [c for c in rows[-1]["cells"] if c.get("pitch") not in (None, "0")]
                    if pn and pn[-1]["tie"]:
                        sung[0]["cn"] = "~"
                rows.append(dict(label=label, cells=cells, page=page.page_number))
    return rows


def show(rows):
    for r in rows:
        out = []
        for c in r["cells"]:
            if c.get("bar"): out.append("|")
            elif c.get("dash"): out.append("−")
            else:
                out.append(c["pitch"] + "'" * c["up"] + "," * c["down"] + "/" + c["dur"] + ("^" if c["tie"] else "")
                           + (f"[{c['cn']}]" if c["cn"] else "") + (f"<{c['en']}>" if c["en"] else ""))
        print(r["page"], (r["label"] or {}).get("en"), " ".join(out))


if __name__ == "__main__":
    import sys
    show(extract(sys.argv[1]))
