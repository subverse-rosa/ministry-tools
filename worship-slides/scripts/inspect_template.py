"""List the weekly template's slides so service.yaml can point at them by number.

    python3 inspect_template.py template.pptx

Prints: slide number, layout, whether it has a full-bleed picture (photo cover / announcement image),
transition, and the first text on the slide.
"""
import sys
from pptx import Presentation
from pptx.oxml.ns import qn
prs = Presentation(sys.argv[1])
W, H = prs.slide_width, prs.slide_height
for i, s in enumerate(prs.slides, 1):
    pics = [sh for sh in s.shapes if sh.shape_type == 13]
    full = any(p.width >= W * 0.9 and p.height >= H * 0.9 for p in pics)
    tr = s._element.find(qn("p:transition"))
    tr_s = "-" if tr is None else (tr[0].tag.split("}")[1] if len(tr) else "x") + (f" {tr.get('advTm')}ms" if tr.get("advTm") else "")
    if tr is None and s._element.find("{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent") is not None:
        tr_s = "p14"
    txt = " / ".join(sh.text_frame.text.strip().replace("\n", " ") for sh in s.shapes
                     if sh.has_text_frame and sh.text_frame.text.strip())
    print(f"{i:>3}  {s.slide_layout.name[:18]:<18} {'PHOTO' if full else ('pic' if pics else '   ')}  {tr_s:<12} {txt[:70]}")
