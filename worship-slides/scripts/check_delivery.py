"""Delivery check for worship-slides decks: rebuild from the delivered inputs and compare.

    python3 check_delivery.py <service.yaml> <delivered.pptx>      # one deck
    python3 check_delivery.py <folder> [--json]                    # every song folder under a library

One deck. The yaml is built with this skill's build_service.py into a temporary folder (inputs are read
from the yaml's own folder, as the operator would), then compared with the delivered file:
  slides   slide count equal
  text     per-slide text equal (runs, tables, grouped shapes)
  xml      per-slide XML equal (catches style, colour, transition or property drift)

Library folder. Each song folder is checked against the layout in references/song-library.md:
  layout   only the public files at top level (deck, score PDF, 说明.txt) and the 制作资料（勿改）/ folder;
           the production folder holds only music/ slides/ records/ data/ lyrics/ source/ (no stray files)
  styles   no copy of styles.json anywhere in a song folder (the skill is the single source of truth)
  rebuild  every slides/*.yaml that names a delivered deck is rebuilt and compared as above
Exit code 1 when any check fails. Delivered files are read only; rebuild output goes to a temp folder.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile
from xml.etree import ElementTree as ET
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build_service.py")
PRODUCTION = "制作资料（勿改）"
PRODUCTION_DIRS = {"music", "slides", "records", "data", "lyrics", "source"}
PUBLIC_EXTRA = {"说明.txt"}


def slide_fingerprints(pptx):
    """Return (text list, xml hash list) for every slide."""
    from pptx import Presentation
    from lxml import etree
    prs = Presentation(pptx)
    texts, hashes = [], []
    for s in prs.slides:
        parts = []
        for el in s._element.iter():
            if el.tag.endswith("}t") and el.text:
                parts.append(el.text)
        texts.append("".join(parts))
        hashes.append(hashlib.sha256(etree.tostring(s._element, method="c14n")).hexdigest()[:16])
    return texts, hashes


def compare(built, delivered):
    bt, bh = slide_fingerprints(built)
    dt, dh = slide_fingerprints(delivered)
    problems = []
    if len(bt) != len(dt):
        problems.append(f"slides: built {len(bt)}, delivered {len(dt)}")
    for i, (a, b) in enumerate(zip(bt, dt), 1):
        if a != b:
            problems.append(f"text on slide {i} differs")
    for i, (a, b) in enumerate(zip(bh, dh), 1):
        if a != b:
            problems.append(f"xml on slide {i} differs")
    return problems


def rebuild(yaml_path, delivered):
    """Build the yaml into a temp folder and compare with the delivered deck."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "rebuilt.pptx")
        proc = subprocess.run([sys.executable, BUILD, os.path.abspath(yaml_path), out],
                              cwd=os.path.dirname(os.path.abspath(yaml_path)), capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.exists(out):
            return [f"build failed: {(proc.stderr or proc.stdout).strip().splitlines()[-1:]}"]
        return compare(out, delivered)


def check_deck(yaml_path, delivered):
    problems = rebuild(yaml_path, delivered)
    return {"deck": delivered, "yaml": yaml_path, "status": "ok" if not problems else "MISMATCH", "problems": problems}


def check_folder(folder):
    results, layout = [], []
    base = os.path.abspath(folder)
    for entry in sorted(os.listdir(base)):
        song = os.path.join(base, entry)
        if not os.path.isdir(song) or entry.startswith((".", "_")):
            continue
        for root, dirs, files in os.walk(song):
            dirs[:] = [d for d in dirs if not d.startswith((".", "_"))]
            for f in files:
                if f == "styles.json":
                    layout.append({"song": entry, "status": "styles", "detail": os.path.relpath(os.path.join(root, f), base)})
        top = set(os.listdir(song))
        for name in sorted(top):
            full = os.path.join(song, name)
            if os.path.isdir(full):
                if name == PRODUCTION or name.startswith("_archive"):
                    continue
                layout.append({"song": entry, "status": "layout", "detail": f"unexpected folder {name}/ at top level"})
            elif not (name.lower().endswith((".pptx", ".pdf")) or name in PUBLIC_EXTRA or name.startswith("~$")):
                layout.append({"song": entry, "status": "layout", "detail": f"stray file {name}"})
        prod = os.path.join(song, PRODUCTION)
        if os.path.isdir(prod):
            for name in sorted(os.listdir(prod)):
                if name not in PRODUCTION_DIRS and not name.startswith("."):
                    layout.append({"song": entry, "status": "layout", "detail": f"stray entry in production folder: {name}"})
        for root, dirs, files in os.walk(song):
            dirs[:] = [d for d in dirs if d != "_archive" and not d.startswith(".")]
            for f in sorted(files):
                if not f.lower().endswith((".yaml", ".yml")) or os.path.basename(root) != "slides":
                    continue
                yaml_path = os.path.join(root, f)
                deck = find_delivered_deck(yaml_path, song)
                if deck is None:
                    layout.append({"song": entry, "status": "rebuild", "detail": f"{os.path.relpath(yaml_path, base)}: no delivered deck found"})
                else:
                    results.append(check_deck(yaml_path, deck))
    return results, layout


def find_delivered_deck(yaml_path, song):
    """The deck built from a slides/*.yaml sits beside it (one .pptx) or is the song's single top-level deck."""
    beside = [n for n in sorted(os.listdir(os.path.dirname(yaml_path))) if n.lower().endswith(".pptx") and not n.startswith("~$")]
    if len(beside) == 1:
        return os.path.join(os.path.dirname(yaml_path), beside[0])
    decks = [os.path.join(song, n) for n in sorted(os.listdir(song)) if n.lower().endswith(".pptx") and not n.startswith("~$")]
    return decks[0] if len(decks) == 1 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="a service.yaml or a library folder")
    ap.add_argument("deck", nargs="?", help="the delivered .pptx when target is a yaml")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.target.lower().endswith((".yaml", ".yml")):
        if not args.deck:
            ap.error("give the delivered deck after the yaml")
        results, layout = [check_deck(args.target, args.deck)], []
    else:
        results, layout = check_folder(args.target)
    bad = [r for r in results if r["status"] != "ok"] + layout
    if args.json:
        print(json.dumps({"decks": results, "layout": layout, "needs_attention": len(bad)}, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"{r['status']:<9} {os.path.basename(r['deck'])}")
            for p in r["problems"][:20]:
                print(f"          - {p}")
        for item in layout:
            print(f"{item['status']:<9} {item['song']}: {item['detail']}")
        print(f"\n{len(results)} deck(s) rebuilt, {len(bad)} problem(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
