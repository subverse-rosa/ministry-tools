"""Turn a vector-PDF jianpu score (staff + jianpu + CN + EN layout, section labels like 'VERSE 1 · 主歌一')
into a song.json for build_service.py ('type: jianpu').

    python3 make_song.py score.pdf --title 我们所爱的神 --en-title "The God We Love" \
        --key "1 = B♭   4/4   ♩ = 82–84" --credit "Words & Music: … · CCLI 1234567" -o song.json
    python3 make_song.py score.pdf --dump          # print what was extracted, for checking

Scores whose jianpu is an overlay layer, or that need repeats unfolded, need a small per-song script
instead: see references/jianpu.md.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jianpu_extract as JE
from songs import song_from_score

ap = argparse.ArgumentParser()
ap.add_argument("pdf"); ap.add_argument("--title"); ap.add_argument("--en-title", default="")
ap.add_argument("--key", default=""); ap.add_argument("--credit", default="")
ap.add_argument("--max-width", type=float, default=12.6, help="inches of music per line")
ap.add_argument("-o", "--out"); ap.add_argument("--dump", action="store_true")
a = ap.parse_args()
rows = JE.extract(a.pdf)
if a.dump or not a.out:
    JE.show(rows); sys.exit()
song = song_from_score(rows, a.title, a.en_title, a.key, a.credit, max_width_in=a.max_width)
json.dump(song, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
for s in song["slides"]:
    print(s["badge"].ljust(9), " / ".join("".join(c["cn"] for c in sy["cells"] if c.get("cn") not in (None, "~"))
                                         for sy in s["systems"]))
print(len(song["slides"]), "slides ->", a.out)
