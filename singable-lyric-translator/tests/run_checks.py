#!/usr/bin/env python3
"""Deterministic checks for tests/cases.json.

python tests/run_checks.py E01 reply.txt
Checks the machine-checkable 'auto' items only. All 'assert' items need review.
Exit 0: AUTO_PASS; 1: AUTO_FAIL; 2: MANUAL_REVIEW_REQUIRED (or usage error).
"""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('count_helper', HERE.parent/'skill/scripts/check_counts.py')
counter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(counter)
CJK = counter.CJK
CARD = "核心冲突决策"  # legacy marker
CARD_RE = re.compile(r"决策\s*\d+\s*/\s*\d+")

def zh_lines(text):
    return list(counter.lyric_lines(text))

def evaluate(t, text):
    auto = t.get("auto", {})
    results = []
    def rec(name, ok, detail=""):
        results.append(dict(name=name, passed=ok, detail=detail))
    if "slots" in auto:
        want = auto["slots"]; lines = zh_lines(text)
        counts = [len(CJK.findall(s)) for s in lines]
        rec("slot counts", counts == want, f"want {want} got {counts}")
    for s in auto.get("must_contain", []):
        rec(f"contains '{s}'", s in text)
    for s in auto.get("must_not_contain", []):
        rec(f"does not contain '{s}'", s not in text)
    n_cards = len(CARD_RE.findall(text))
    if auto.get("card") is True:  rec("has a decision card", n_cards >= 1, f"cards={n_cards}")
    if auto.get("card") is False: rec("has no decision card", n_cards == 0 and CARD not in text, f"cards={n_cards}")
    if "max_cards" in auto: rec(f"at most {auto['max_cards']} cards", n_cards <= auto["max_cards"], f"cards={n_cards}")
    status = ("MANUAL_REVIEW_REQUIRED" if not results else
              "AUTO_PASS" if all(c['passed'] for c in results) else "AUTO_FAIL")
    return dict(case=t['id'], status=status, checks=results,
                manual_review_required=True, behavioral_validation='not_tested')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case')
    ap.add_argument('reply', type=Path, help='UTF-8 reply file, or - for stdin')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    tests = {t['id']: t for t in json.loads((HERE/'cases.json').read_text(encoding='utf-8'))['tests']}
    if args.case not in tests:
        ap.error(f'unknown case: {args.case}')
    reply = sys.stdin.read() if args.reply == Path('-') else args.reply.read_text(encoding='utf-8')
    result = evaluate(tests[args.case], reply)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for check in result['checks']:
            print(('PASS ' if check['passed'] else 'FAIL ') + check['name'] + '  ' + check['detail'])
        print('Manual review of all assert items is required; behavioral validation: not tested.')
        print('RESULT:', result['status'])
    return {'AUTO_PASS': 0, 'AUTO_FAIL': 1, 'MANUAL_REVIEW_REQUIRED': 2}[result['status']]

if __name__ == "__main__":
    raise SystemExit(main())
