#!/usr/bin/env python3
"""Check a reviewed MEI as a projection handoff and list its sung-order numbered events.

check  : validate metadata, sections, performance route, lyric attacks and ties; print a summary
events : write the sung-order events (numbered notation + Chinese/English syllables) as JSON

Standard library only. It checks the supplied encoding; it does not certify source matching,
Chinese quality, approval decisions or real singing.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from notation import degree, rhythm
from engrave_score import mei_events, xml_input

M = '{http://www.music-encoding.org/ns/mei}'
X = '{http://www.w3.org/XML/1998/namespace}id'
LANG = '{http://www.w3.org/XML/1998/namespace}lang'
H = '{urn:singable-lyric-translator:handoff:1}'
STATUSES = ('draft', 'text-approved', 'performed')
KINDS = ('Verse', 'Pre-Chorus', 'Chorus', 'Bridge', 'Ending', 'Tag', 'Intro', 'Interlude', 'Outro', 'Refrain')
REPEATS = ('rptstart', 'rptend', 'rptboth')


class HandoffError(ValueError):
    pass


def load(path):
    raw = Path(path).read_bytes()
    return raw, ET.fromstring(xml_input(raw))


def text(el):
    return ' '.join(''.join(el.itertext()).split()) if el is not None else ''


def metadata(doc, problems):
    head = doc.find(M + 'meiHead')
    if head is None:
        raise HandoffError('Handoff needs <meiHead> with titles and the handoff record')
    titles = head.findall('.//' + M + 'titleStmt/' + M + 'title')
    zh = next((t for t in titles if t.get(LANG, '').startswith('zh')), titles[0] if titles else None)
    en = next((t for t in titles if t.get(LANG, '').startswith('en') and t is not zh), None)
    rec = head.find('.//' + M + 'extMeta/' + H + 'handoff')
    if rec is None:
        raise HandoffError('Missing <extMeta><handoff xmlns="urn:singable-lyric-translator:handoff:1" .../>')
    meta = {k.replace('-', '_'): v for k, v in rec.attrib.items()}
    for key in ('lyric_version', 'lyric_status', 'tonic'):
        if not meta.get(key):
            problems.append(f'handoff record needs {key.replace("_", "-")}')
    if meta.get('lyric_status') and meta['lyric_status'] not in STATUSES:
        problems.append(f'lyric-status must be one of {", ".join(STATUSES)}')
    if meta.get('scale', 'major') not in ('major', 'minor'):
        problems.append('scale must be major or minor (minor uses tonic=1)')
    try:
        meta['octave_shift'] = int(meta.get('octave_shift', '0'))
    except ValueError:
        problems.append('octave-shift must be an integer')
        meta['octave_shift'] = 0
    if meta.get('tonic'):
        try:
            degree(meta['tonic'], meta['tonic'])
        except ValueError as exc:
            problems.append(f'tonic: {exc}')
    if not text(zh):
        problems.append('titleStmt needs a title (Chinese title with xml:lang="zh")')
    return {
        'title': text(zh), 'title_en': text(en),
        'credits': text(head.find('.//' + M + 'availability/' + M + 'useRestrict')),
        'key_label': meta.get('key_label', ''),
        'lyric_version': meta.get('lyric_version', ''), 'lyric_status': meta.get('lyric_status', ''),
        'tonic': meta.get('tonic', ''), 'scale': meta.get('scale', 'major'), 'octave_shift': meta['octave_shift'],
        'staff': meta.get('staff', '1'), 'layer': meta.get('layer', '1'),
        'zh_verse': meta.get('zh_verse', '1'), 'en_verse': meta.get('en_verse', '2'),
    }


def route(doc, problems):
    """Performance route as (label, element) pairs: <expansion> if present, else written-out document order."""
    music = doc.find('.//' + M + 'music')
    if music is None:
        raise HandoffError('No <music> element')
    parents = {c: p for p in music.iter() for c in p}
    labelled = [s for s in music.iter(M + 'section') if s.get('label')]
    if not labelled:
        raise HandoffError('Label every sung section: <section xml:id="v1" label="Verse 1">')
    for s in labelled:
        p = parents.get(s)
        while p is not None:
            if p.tag == M + 'section' and p.get('label'):
                raise HandoffError(f'Labelled sections must not nest: {s.get("label")} inside {p.get("label")}')
            p = parents.get(p)
        if not s.get('label').split()[0] in KINDS:
            problems.append(f'section label "{s.get("label")}" does not start with {"/".join(KINDS)}')
    for m in music.iter(M + 'measure'):
        p, inside = parents.get(m), False
        while p is not None:
            if p.tag in (M + 'section', M + 'ending') and (p.get('label') or p.tag == M + 'ending'):
                inside = True
                break
            p = parents.get(p)
        if not inside:
            raise HandoffError(f'Measure {m.get("n", "?")} is outside every labelled section')
    expansions = list(music.iter(M + 'expansion'))
    if len(expansions) > 1:
        expansions = [e for e in expansions if e.get('type') == 'performance']
        if len(expansions) != 1:
            raise HandoffError('Several <expansion> elements: mark exactly one type="performance"')
    if not expansions:
        if music.find('.//' + M + 'ending') is not None or any(
                m.get('left') in REPEATS or m.get('right') in REPEATS for m in music.iter(M + 'measure')):
            raise HandoffError('Repeats/endings need an <expansion plist> or written-out sections')
        return [(s.get('label'), s) for s in labelled]
    ids = {e.get(X): e for e in music.iter() if e.get(X)}
    out, last = [], None
    for token in expansions[0].get('plist', '').split():
        el = ids.get(token.lstrip('#'))
        if el is None or el.tag not in (M + 'section', M + 'ending'):
            raise HandoffError(f'expansion plist item {token} is not a section or ending')
        label = el.get('label') if el.tag == M + 'section' else (el.get('label') or last)
        if not label:
            raise HandoffError(f'{token}: an ending needs a label when it starts the route')
        out.append((label, el))
        last = label
    if not out:
        raise HandoffError('Empty expansion plist')
    return out


def syllables(event, verse_n):
    for v in event.iter(M + 'verse'):
        if v.get('n', '1') == verse_n:
            syls = v.findall(M + 'syl')
            if syls:
                return ''.join(s.text or '' for s in syls), syls[-1].get('con', '')
    return None, ''


def build(path):
    """Return (summary dict, problems list). Raises HandoffError for an unusable encoding."""
    raw, doc = load(path)
    problems = []
    meta = metadata(doc, problems)
    passes = route(doc, problems)
    try:
        timing = mei_events(doc, meta['staff'], meta['layer'])
    except ValueError as exc:
        raise HandoffError(str(exc)) from exc
    tie_to = {}
    for t in doc.iter(M + 'tie'):
        tie_to[t.get('startid', '').lstrip('#')] = t.get('endid', '').lstrip('#')
    sections = []
    for label, el in passes:
        measures, melisma, prev, prev_tie_attr = [], False, None, None
        for m in el.iter(M + 'measure'):
            events = []
            for st in m.findall(M + 'staff'):
                if st.get('n') != meta['staff']:
                    continue
                for la in st.findall(M + 'layer'):
                    if la.get('n') != meta['layer']:
                        continue
                    if la.find('.//' + M + 'mRest') is not None or la.find('.//' + M + 'space') is not None:
                        problems.append(f'{label} m{m.get("n", "?")}: encode mRest/space as explicit rests in the guide layer')
                    in_chord = {n for c in la.iter(M + 'chord') for n in c.iter(M + 'note')}
                    for e in la.iter():
                        tag = e.tag.removeprefix(M)
                        if tag not in ('note', 'rest', 'chord') or (tag == 'note' and e in in_chord):
                            continue
                        eid = e.get(X)
                        info = timing[eid]
                        zh, zh_con = syllables(e, meta['zh_verse'])
                        en, en_con = syllables(e, meta['en_verse'])
                        where = f'{label} m{m.get("n", "?")} {eid}'
                        cont = prev is not None and (tie_to.get(prev) == eid or (prev_tie_attr in ('i', 'm')))
                        if not info['pitches']:
                            if zh or en:
                                problems.append(f'{where}: lyric on a rest')
                            melisma, prev, prev_tie_attr = False, None, None
                            ev = {'id': eid, 'rest': True, 'number': 0, 'octave': 0, 'alter': 0}
                        else:
                            if cont and zh:
                                problems.append(f'{where}: tied continuation carries a new syllable "{zh}"')
                            if not cont and not zh and not melisma:
                                problems.append(f'{where}: sung note without a Chinese syllable (and no extender/tie before it)')
                            if prev is not None and tie_to.get(prev) == eid and timing[prev]['pitches'] != info['pitches']:
                                problems.append(f'{where}: tie joins different pitches')
                            if zh:
                                melisma = zh_con == 'u'
                            ev = {'id': eid, 'rest': False,
                                  **degree(info['pitches'][0], meta['tonic'], meta['scale'], meta['octave_shift'])}
                            prev = eid
                            prev_tie_attr = (e.get('tie') or (e.find(M + 'note').get('tie') if tag == 'chord' and e.find(M + 'note') is not None else None))
                        shape = rhythm(info['duration'])
                        ev.update({'duration': info['duration'], 'actual_duration': info['actual_duration'],
                                   'tuplet': info['tuplet'], **shape,
                                   'tie_next': bool(ev['rest'] is False and (tie_to.get(eid) or prev_tie_attr in ('i', 'm'))),
                                   'continuation': bool(not ev['rest'] and cont),
                                   'melisma': bool(not ev['rest'] and not cont and not zh),
                                   'zh': zh, 'zh_con': zh_con, 'en': en, 'en_con': en_con})
                        events.append(ev)
            measures.append({'n': m.get('n', ''), 'events': events})
        sections.append({'label': label, 'source_id': el.get(X, ''), 'measures': measures})
    return {'schema': 'lyric-handoff/1', 'source_sha256': hashlib.sha256(raw).hexdigest(),
            **{k: meta[k] for k in ('title', 'title_en', 'credits', 'key_label', 'lyric_version', 'lyric_status',
                                    'tonic', 'scale', 'octave_shift')},
            'sections': sections, 'performance_status': 'not_performed' if meta['lyric_status'] != 'performed' else 'reported_performed'}, problems


def summary_lines(data, problems):
    yield f"{data['title']}{' / ' + data['title_en'] if data['title_en'] else ''}  ·  lyric {data['lyric_version'] or '?'} ({data['lyric_status'] or '?'})"
    yield f"1 = {data['tonic']} {data['scale']}{'  ' + data['key_label'] if data['key_label'] else ''}"
    if data['credits']:
        yield 'credits: ' + data['credits']
    yield f"route: {len(data['sections'])} passes"
    for i, s in enumerate(data['sections'], 1):
        ev = [e for m in s['measures'] for e in m['events']]
        zh = ''.join(e['zh'] or '' for e in ev)
        ms = [m['n'] for m in s['measures']]
        yield f"  {i:>2} {s['label']:<12} m{ms[0]}-{ms[-1]}  {len(zh):>3} 字  {zh[:24]}{'…' if len(zh) > 24 else ''}"
    yield ('OK' if not problems else f'{len(problems)} problem(s):')
    for p in problems:
        yield '  - ' + p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check')
    c.add_argument('score', type=Path)
    c.add_argument('--require-approved', action='store_true', help='fail unless lyric-status is text-approved or performed')
    c.add_argument('--json', action='store_true')
    e = sub.add_parser('events')
    e.add_argument('score', type=Path)
    e.add_argument('output', type=Path, help='new JSON file (an existing path is refused)')
    args = ap.parse_args()
    try:
        data, problems = build(args.score)
    except (HandoffError, ET.ParseError, OSError, KeyError) as exc:
        ap.exit(1, f'NOT USABLE: {exc}\n')
    if args.cmd == 'check':
        if args.require_approved and data['lyric_status'] not in ('text-approved', 'performed'):
            problems.append(f"lyric-status is {data['lyric_status'] or 'missing'}; approval required")
        if args.json:
            print(json.dumps({'ok': not problems, 'problems': problems,
                              'passes': [s['label'] for s in data['sections']],
                              **{k: data[k] for k in ('title', 'lyric_version', 'lyric_status', 'source_sha256', 'performance_status')}},
                             ensure_ascii=False, indent=2))
        else:
            print('\n'.join(summary_lines(data, problems)))
        sys.exit(1 if problems else 0)
    if problems:
        ap.exit(1, 'NOT EXPORTED: run check and fix:\n' + '\n'.join('  - ' + p for p in problems) + '\n')
    if args.output.exists():
        ap.exit(1, f'{args.output} exists; choose a new file\n')
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"{args.output}: {len(data['sections'])} passes, lyric {data['lyric_version']} ({data['lyric_status']})")


if __name__ == '__main__':
    main()
