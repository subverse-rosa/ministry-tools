"""Extract the melody jianpu row from a score whose jianpu was added as an overlay
(digits in 'AAAAAA+TimesNewRomanPSMT', graphics drawn with plain 0 colour) on top of a
re-stamped engraved page. Returns measures in order: list of dict(page, row, cells)."""
import logging, re
import pdfplumber
logging.getLogger("pdfminer").setLevel(logging.ERROR)

FONT = "AAAAAA+TimesNewRomanPSMT"


def _overlay(o):
    return o.get("stroking_color") == 0 or o.get("non_stroking_color") == 0


def extract(path):
    out = []
    with pdfplumber.open(path) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            digs = [c for c in page.chars if c["fontname"] == FONT and c["text"] in "01234567−-" and c["size"] > 9]
            labels = [c for c in page.chars if "SimSun" in c["fontname"]]
            lines = [l for l in page.lines if _overlay(l) and (
                (abs(l["top"] - l["bottom"]) < 0.3 and abs(l.get("linewidth", 0) - 0.42) < 0.05 and l["x1"] - l["x0"] < 12) or
                (abs(l["x0"] - l["x1"]) < 0.3 and abs(l.get("linewidth", 0) - 0.35) < 0.05))]
            curves = [c for c in page.curves if _overlay(c)]
            tops = sorted({round(c["top"], 1) for c in digs})
            rows = []
            for t in tops:
                if not rows or t - rows[-1] > 6:
                    rows.append(t)
            for y in rows:
                row = sorted([c for c in digs if abs(c["top"] - y) < 1.5], key=lambda c: c["x0"])
                # which label sits on this row?  简谱 / 简谱1 / 简谱2
                lab = "".join(c["text"] for c in sorted([c for c in labels if abs(c["top"] - y) < 6], key=lambda c: c["x0"]))
                bottom = max(c["bottom"] for c in row)
                cells = []
                for c in row:
                    cx = (c["x0"] + c["x1"]) / 2
                    if c["text"] in "−-":
                        cells.append(dict(dash=True, x=cx)); continue
                    dots = [d for d in curves if d["x1"] - d["x0"] < 2.5]
                    up = sum(1 for d in dots if abs((d["x0"] + d["x1"]) / 2 - cx) < 2.5 and c["top"] - 8 < d["bottom"] <= c["top"] + 0.6)
                    down = sum(1 for d in dots if abs((d["x0"] + d["x1"]) / 2 - cx) < 2.5 and bottom + 1 <= d["top"] < bottom + 9)
                    aug = any(0 <= d["x0"] - c["x1"] < 5 and c["top"] + 2 < (d["top"] + d["bottom"]) / 2 < bottom - 1 for d in dots)
                    uls = {round(l["top"], 1) for l in lines if abs(l["top"] - l["bottom"]) < 0.3
                           and l["x0"] - 1 < cx < l["x1"] + 1 and bottom - 2 < l["top"] < bottom + 5}
                    u = min(len(uls), 2)
                    cells.append(dict(pitch=c["text"], up=up, down=down, u=u, aug=aug, tie=False, x=cx, x0=c["x0"]))
                for l in lines:
                    if abs(l["x0"] - l["x1"]) < 0.3 and l["top"] < y + 1 and l["bottom"] > bottom - 1:
                        cells.append(dict(bar=True, x=l["x0"]))
                cells.sort(key=lambda c: c["x"])
                notes = [c for c in cells if "pitch" in c]
                for t in curves:
                    if (t["x1"] - t["x0"] > 5 and y - 12 < t["top"] < y + 1 and notes and t.get("stroke") and not t.get("fill")
                            and abs((t.get("linewidth") or 0) - 0.4) < 0.05 and t.get("stroking_color") == 0):
                        a = min(notes, key=lambda n: abs(n["x"] - t["x0"]))
                        b = min(notes, key=lambda n: abs(n["x"] - t["x1"]))
                        a["tie"] = True
                        a["arc_to"] = b["x"]
                rows_meas, cur = [], []
                for c in cells:
                    if c.get("bar"):
                        if cur: rows_meas.append(cur)
                        cur = []
                    else:
                        cur.append(c)
                if cur: rows_meas.append(cur)
                out.append(dict(page=pn, y=y, label=lab, measures=rows_meas))
    return out


def fmt(c):
    if c.get("dash"): return "−"
    return (c["pitch"] + "'" * c["up"] + "," * c["down"] + ("_" * c["u"]) + ("." if c["aug"] else "") + ("^" if c["tie"] else ""))


if __name__ == "__main__":
    import sys
    for r in extract(sys.argv[1]):
        print(r["page"], round(r["y"]), r["label"] or "-", " | ".join(" ".join(fmt(c) for c in m) for m in r["measures"]))
