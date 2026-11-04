#!/usr/bin/env python3
"""Check that each Chinese lyric line has the expected number of syllable slots.

Usage:  python check_counts.py --slots 8,6,8,6 draft.txt
        python check_counts.py --slots 8,6,8,6 --stdin < draft.txt
        python check_counts.py --slots 9 --variants candidates.txt

--variants: every non-blank line (lines starting with '#' are skipped) is one candidate
for a single line with the slot count given by --slots N. Each candidate is reported as
ok, OVER (+n) or UNDER (-n); the run itself exits 0 because rejected candidates are expected.

Counts CJK ideographs only (punctuation, spaces, Latin and 0-9 ignored).
Use --raw-lines for a plain lyric file without label filtering.
Default filtering retains every Chinese line, including one-character/mixed lines.
Counts are orthographic proxies, not pronunciation or music validation.
Lines that are blank or start with '[', '#', '>' or '```' are treated as labels and skipped.
Exit code 0 = all match, 1 = mismatch or wrong number of lines.
"""
import argparse, re, sys

CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

def lyric_lines(text):
    """Chinese lyric lines only: skip labels, English echo lines, bullets and status lines."""
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s[0] in "[#>-*" or s.startswith("```"):
            continue
        if s.startswith(("输入等级", "无需决策", "押韵", "高音区", "重音", "已自动处理")):
            continue
        if not CJK.search(s):
            continue          # English echo lines; never discard Chinese fragments
        yield s

def variants(text, want):
    """Compare every candidate line against one target slot count."""
    fit = total = 0
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        total += 1
        got = len(CJK.findall(s))
        if got == want:
            fit += 1
            print(f"ok    {got}/{want}  {s}")
        else:
            diff = got - want
            tag = f"OVER (+{diff})" if diff > 0 else f"UNDER ({diff})"
            print(f"{tag:<12}{got}/{want}  {s}")
    print(f"RESULT: {fit}/{total} candidates fit {want} slots")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--slots", required=True, help="comma-separated expected slots per line (a single number with --variants)")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--raw-lines", action="store_true", help="count every nonblank line; no label/English filtering")
    ap.add_argument("--variants", metavar="FILE", help="file of candidate lines for ONE slot count (use with --slots N)")
    a = ap.parse_args()
    try:
        want = [int(x.strip()) for x in a.slots.split(",")]
        if not want or any(x <= 0 for x in want):
            raise ValueError
    except ValueError:
        ap.error("--slots needs positive integers separated by commas")
    if a.variants:
        if len(want) != 1:
            ap.error("--variants needs a single number for --slots")
        variants(open(a.variants, encoding="utf-8").read(), want[0])
        return
    text = sys.stdin.read() if a.stdin or not a.file else open(a.file, encoding="utf-8").read()
    lines = ([s.strip() for s in text.splitlines() if s.strip()] if a.raw_lines
             else list(lyric_lines(text)))
    ok = len(lines) == len(want)
    if not ok:
        print(f"LINE COUNT MISMATCH: expected {len(want)} Chinese lines, found {len(lines)}")
    for i, (s, w) in enumerate(zip(lines, want), 1):
        got = len(CJK.findall(s))
        flag = "ok " if got == w else "BAD"
        if got != w:
            ok = False
        print(f"{flag} line {i}: expected {w}, got {got}  {s}")
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    # Piped Chinese text must not depend on the Windows locale code page.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    main()
