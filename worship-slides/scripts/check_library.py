"""Check song decks in a folder against the approved scores they were built from.

    python3 check_library.py <folder> [--json]

For every .pptx (skipping _archive folders and PowerPoint lock files) that carries worship-slides
provenance, each song built from a lyric-translator handoff is reported as:
  current       score unchanged since the deck was built, and the deck's Chinese matches the handoff
  STALE         the score (score.mei) changed after the deck was built: rebuild the deck
  EXPORT-OLD    the events JSON is older than the score: rerun handoff.py events, then rebuild
  EDITED        the deck's Chinese lyrics differ from the handoff (someone edited the PPT)
  MISSING       the recorded score or events file is gone
Decks without provenance (template-only weeks, PDF-extracted songs) are listed as "no handoff".
Exit code 1 when anything needs attention. Read-only: nothing is changed.
"""
import argparse, hashlib, json, os, sys, zipfile
from xml.etree import ElementTree as ET

CP = "{http://schemas.openxmlformats.org/officeDocument/2006/custom-properties}"
CN_SIZE = "6000"          # Chinese lyric runs on jianpu slides are 60pt


def provenance(pptx):
    with zipfile.ZipFile(pptx) as z:
        if "docProps/custom.xml" not in z.namelist():
            return None
        root = ET.fromstring(z.read("docProps/custom.xml"))
    for p in root.iter(CP + "property"):
        if p.get("name") == "worship-slides":
            return json.loads("".join(p.itertext()))
    return None


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def deck_chinese(pptx, first, last):
    from pptx import Presentation
    from pptx.oxml.ns import qn
    slides = list(Presentation(pptx).slides)[first - 1:last]
    out = []
    for s in slides:
        for r in s._element.iter(qn("a:r")):
            rpr = r.find(qn("a:rPr"))
            if rpr is not None and rpr.get("sz") == CN_SIZE:
                out.append(r.findtext(qn("a:t")) or "")
    return "".join(out)


def handoff_chinese(h):
    return "".join(e["zh"] for s in h["sections"] for m in s["measures"] for e in m["events"] if e.get("zh"))


def check_song(deck_dir, pptx, song):
    res = {"deck": pptx, "title": song.get("title"), "lyric_version": song.get("lyric_version")}
    score = os.path.join(deck_dir, song["score"]) if song.get("score") else None
    handoff = os.path.join(deck_dir, song["handoff"]) if song.get("handoff") else None
    if score is None:
        res["status"], res["detail"] = "MISSING", "no score path was recorded; build with `score:` next time"
        return res
    if not os.path.exists(score):
        res["status"], res["detail"] = "MISSING", f"score not found: {song['score']}"
        return res
    if sha(score) != song.get("score_sha256"):
        res["status"], res["detail"] = "STALE", "score changed after this deck was built"
        if handoff and os.path.exists(handoff):
            h = json.load(open(handoff, encoding="utf-8"))
            if h.get("source_sha256") != sha(score):
                res["status"], res["detail"] = "EXPORT-OLD", "events JSON is older than the score: rerun handoff.py events, then rebuild"
            else:
                res["detail"] += f" (now lyric {h.get('lyric_version')}, {h.get('lyric_status')})"
        return res
    if not handoff or not os.path.exists(handoff):
        res["status"], res["detail"] = "MISSING", "events JSON not found, lyrics not compared"
        return res
    h = json.load(open(handoff, encoding="utf-8"))
    want, got = handoff_chinese(h), deck_chinese(pptx, *song["slides"])
    if want != got:
        i = next((k for k, (a, b) in enumerate(zip(want, got)) if a != b), min(len(want), len(got)))
        res["status"] = "EDITED"
        res["detail"] = f"deck lyrics differ from the handoff at character {i + 1}: …{got[max(0, i - 4):i + 4]}… vs …{want[max(0, i - 4):i + 4]}…"
        return res
    res["status"], res["detail"] = "current", f"lyric {h.get('lyric_version')} ({h.get('lyric_status')})"
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results, plain = [], []
    for root, dirs, files in os.walk(args.folder):
        dirs[:] = sorted(d for d in dirs if d != "_archive" and not d.startswith("."))
        for f in sorted(files):
            if not f.lower().endswith(".pptx") or f.startswith("~$"):
                continue
            pptx = os.path.join(root, f)
            try:
                prov = provenance(pptx)
            except (zipfile.BadZipFile, ET.ParseError, json.JSONDecodeError) as exc:
                results.append({"deck": pptx, "status": "UNREADABLE", "detail": str(exc)}); continue
            songs = (prov or {}).get("songs") or []
            if not songs:
                plain.append(pptx); continue
            for song in songs:
                results.append(check_song(root, pptx, song))
    bad = [r for r in results if r["status"] != "current"]
    if args.json:
        print(json.dumps({"songs": results, "no_handoff": plain, "needs_attention": len(bad)}, ensure_ascii=False, indent=2))
    else:
        base = os.path.abspath(args.folder)
        for r in results:
            print(f"{r['status']:<11} {os.path.relpath(r['deck'], base)}  ·  {r.get('title') or ''}  ·  {r['detail']}")
        for p in plain:
            print(f"{'no handoff':<11} {os.path.relpath(p, base)}")
        print(f"\n{len(results)} song(s) checked, {len(bad)} need attention, {len(plain)} deck(s) without handoff provenance")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
