#!/usr/bin/env python3
"""Check internal consistency of a manually entered rhythmic map, not music.

Usage: python scripts/check_rhythm.py map.json
Exit 0: internally consistent; 1: invalid map or unaccepted changes; 2: CLI error.
All times use exact rational beats (integer or fraction string; no floats).
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys


class MapError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise MapError(message)


def beat(value):
    require(type(value) is int or isinstance(value, str),
            'beats must be integers or fraction strings, not floats/bools')
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise MapError('invalid beat value') from exc


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def intervals(items, label):
    require(isinstance(items, list) and items, label + ' must be a nonempty list')
    result = []
    for item in items:
        start, end = beat(item['start']), beat(item['end'])
        require(start < end, label + ': empty or reversed span')
        require(not result or start >= result[-1][1], label + ': overlap or unsorted')
        result.append((start, end))
    return result


def check_coverage(slots, notes, boundaries, label):
    for start, end in slots:
        require(not any(start < b < end for b in boundaries),
                label + ': slot crosses a hard phrase/breath boundary')
        covered = sum((min(end, b) - max(start, a)
                       for a, b in notes if max(start, a) < min(end, b)), Fraction())
        require(covered == end - start, label + ': slot consumes rest or unscored time')
    for start, end in notes:
        covered = sum((min(end, b) - max(start, a)
                       for a, b in slots if max(start, a) < min(end, b)), Fraction())
        require(covered == end - start, label + ': pitched duration not fully allocated')


def validate(data):
    require(data['schema_version'] == 1, 'unsupported schema_version')
    mode = data['mode']
    require(mode in ('Strict', 'Adaptive', 'Recomposition'), 'unknown mode')
    require(nonempty(data['map_version']), 'map_version required')
    require(nonempty(data['beat_unit']), 'beat_unit required')
    if mode == 'Recomposition':
        require(nonempty(data.get('authorization')) and
                nonempty(data.get('original_map_version')) and
                data['original_map_version'] != data['map_version'],
                'Recomposition requires user authorization and a separate map version')
    phrases = data['phrases']
    require(isinstance(phrases, list) and phrases, 'phrases required')
    ids, summaries = set(), []
    ledger = data.get('ledger', [])
    require(isinstance(ledger, list), 'ledger must be a list')
    ledger_ids = set()
    for entry in ledger:
        require(nonempty(entry['id']) and entry['id'] not in ledger_ids, 'duplicate/empty ledger ID')
        ledger_ids.add(entry['id'])
        require(entry['status'] in ('proposed', 'accepted', 'rejected', 'superseded'), 'invalid ledger status')
        for key in ('phrase', 'source', 'uncertainty', 'mode', 'before', 'after',
                    'alternatives', 'semantic_cost', 'musical_cost', 'recommendation',
                    'decision_owner', 'reason'):
            require(nonempty(entry.get(key)), 'ledger field required: ' + key)
        require(entry['mode'] == mode, 'ledger mode does not match map')
        if entry['status'] == 'superseded':
            require(nonempty(entry.get('superseded_by')), 'superseded_by required')
    for entry in ledger:
        if entry['status'] == 'superseded':
            require(entry['superseded_by'] in ledger_ids and entry['superseded_by'] != entry['id'],
                    'invalid supersession link')
    for phrase in phrases:
        pid = phrase['id']
        require(nonempty(pid) and pid not in ids, 'duplicate/empty phrase ID')
        ids.add(pid)
        for key in ('source', 'meter', 'uncertainty'):
            require(nonempty(phrase[key]), pid + ': missing ' + key)
        events = phrase['events']
        spans = intervals(events, pid + ' events')
        for previous, current in zip(spans, spans[1:]):
            require(previous[1] == current[0], pid + ': timeline gap; encode rests explicitly')
        notes, tied_ranges = [], []
        for index, (event, span) in enumerate(zip(events, spans)):
            require(event['kind'] in ('note', 'rest'), pid + ': unknown event kind')
            require(type(event.get('tie_from_previous', False)) is bool, 'tie flag must be boolean')
            if event['kind'] == 'rest':
                require(not event.get('tie_from_previous'), 'rest cannot be tied')
                continue
            require(nonempty(event['pitch']), pid + ': pitch token required')
            require(event['stress'] in ('strong', 'weak'), pid + ': stress required')
            notes.append(span)
            if event.get('tie_from_previous'):
                require(index > 0 and events[index - 1]['kind'] == 'note' and
                        events[index - 1]['pitch'] == event['pitch'], pid + ': invalid tie')
                if tied_ranges and tied_ranges[-1][1] == spans[index - 1][1]:
                    tied_ranges[-1] = (tied_ranges[-1][0], span[1])
                else:
                    tied_ranges.append((spans[index - 1][0], span[1]))
        require(notes, pid + ': no pitched events')
        boundaries = [beat(b) for b in phrase['boundaries']]
        require(all(spans[0][0] <= b <= spans[-1][1] for b in boundaries), 'boundary outside phrase')
        baseline = intervals(phrase['baseline_slots'], pid + ' baseline')
        target = intervals(phrase['target_slots'], pid + ' target')
        check_coverage(baseline, notes, boundaries, pid + ' baseline')
        check_coverage(target, notes, boundaries, pid + ' target')
        note_onsets = {a for a, _ in notes}
        require(all(a in note_onsets for a, _ in baseline), pid + ': baseline onset not a note onset')
        for label, slots in [('baseline', baseline), ('target', target)]:
            require(not any(a < start < b for a, b in tied_ranges for start, _ in slots),
                    pid + ': ' + label + ' reattacks inside a tie')
        if 'supplied_count' in phrase:
            require(type(phrase['supplied_count']) is int and phrase['supplied_count'] == len(baseline),
                    pid + ': supplied count conflicts with baseline; resolve before adoption')
        changed = baseline != target
        if mode == 'Strict':
            require(not changed, pid + ': Strict cannot change underlay')
        elif mode == 'Adaptive' and changed:
            # A merge removes old attacks. Permit only untied same-pitch events
            # between the retained attack and the final removed attack.
            removed = {a for a, _ in baseline} - {a for a, _ in target}
            for start, end in target:
                lost = [x for x in removed if start < x < end]
                if lost:
                    stop = max(lost)
                    pitches = {e['pitch'] for e, (a, b) in zip(events, spans)
                               if e['kind'] == 'note' and b > start and a <= stop}
                    require(len(pitches) == 1, pid + ': Adaptive merge spans different pitches')
        if mode != 'Strict' and changed:
            require(any(e['phrase'] == pid and e['status'] == 'accepted' and
                        e.get('baseline_slots') == phrase['baseline_slots'] and
                        e.get('target_slots') == phrase['target_slots'] for e in ledger),
                    pid + ': change requires accepted ledger entry matching allocations')
        expected = phrase.get('expected_target')
        if expected is not None:
            require(type(expected) is int and expected == len(target), pid + ': target count mismatch')
        summaries.append({'phrase': pid, 'baseline': len(baseline), 'target': len(target), 'changed': changed})
    require(all(e['phrase'] in ids for e in ledger), 'ledger references unknown phrase')
    return {'result': 'CONSISTENT_MANUAL_MAP', 'mode': mode, 'phrases': summaries,
            'limitation': 'No score/audio transcription, musical validation or M0-M4 gate certification.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.file.read_text(encoding='utf-8-sig')))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        print(json.dumps({'result': 'INVALID_MAP', 'error': str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
