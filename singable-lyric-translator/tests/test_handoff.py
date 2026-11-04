"""Projection handoff contract: metadata, performance route, lyric attacks and ties (invented fixture)."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skill/scripts'))
from handoff import build, HandoffError
from support import scratch

FIXTURE = ROOT/'tests/fixtures/handoff-example.mei'
SOURCE = FIXTURE.read_text(encoding='utf-8')


def variant(folder, *pairs):
    """Fixture copy with each (old, new) replacement applied exactly once."""
    text = SOURCE
    for old, new in zip(pairs[::2], pairs[1::2]):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    path = folder/'variant.mei'
    path.write_text(text, encoding='utf-8')
    return path


def cli(*args):
    return subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT/'skill/scripts/handoff.py'), *map(str, args)],
                          capture_output=True, text=True, encoding='utf-8')


class HandoffTests(unittest.TestCase):
    def test_fixture_route_metadata_and_events(self):
        data, problems = build(FIXTURE)
        self.assertEqual(problems, [])
        self.assertEqual([s['label'] for s in data['sections']], ['Verse 1', 'Chorus', 'Verse 2', 'Chorus'])
        self.assertEqual((data['title'], data['title_en'], data['lyric_status']), ('晨光小径', 'Morning Path', 'text-approved'))
        events = {e['id']: e for s in data['sections'] for m in s['measures'] for e in m['events']}
        self.assertEqual((events['c1']['number'], events['c1']['dot'], events['c1']['zh_con']), (6, True, 'u'))
        self.assertEqual((events['c3']['number'], events['c3']['octave']), (1, 1))
        self.assertTrue(events['a4']['tie_next'] and events['a5']['continuation'])
        self.assertTrue(events['c2']['melisma'])
        self.assertEqual(events['c2']['en'], 'on')
        self.assertTrue(events['a6']['rest'])

    def test_missing_handoff_record_is_unusable(self):
        with scratch() as d, self.assertRaisesRegex(HandoffError, 'extMeta'):
            build(variant(d, '<handoff xmlns', '<other xmlns'))

    def test_repeats_need_a_performance_route(self):
        with scratch() as d, self.assertRaisesRegex(HandoffError, 'expansion'):
            build(variant(d, '<expansion xml:id="perf" type="performance" plist="#v1 #ch #v2 #ch"/>', '',
                          '<measure n="4" right="end">', '<measure n="4" right="rptend">'))

    def test_route_rejects_unknown_plist_target(self):
        with scratch() as d, self.assertRaisesRegex(HandoffError, 'not a section'):
            build(variant(d, 'plist="#v1 #ch #v2 #ch"', 'plist="#v1 #c1"'))

    def test_lyric_on_tied_continuation_and_unlabelled_attack(self):
        with scratch() as d:
            _, problems = build(variant(d, '<note xml:id="a5" pname="g" oct="4" dur="4"/>',
                                        '<note xml:id="a5" pname="g" oct="4" dur="4"><verse n="1"><syl>又</syl></verse></note>'))
            self.assertTrue(any('tied continuation' in p for p in problems))
            _, problems = build(variant(d, '<verse n="1"><syl con="u">同</syl></verse>', '<verse n="1"><syl>同</syl></verse>'))
            self.assertTrue(any('without a Chinese syllable' in p for p in problems))

    def test_measure_outside_labelled_section(self):
        with scratch() as d, self.assertRaisesRegex(HandoffError, 'outside'):
            build(variant(d, '<section xml:id="v2" label="Verse 2">', '<section xml:id="v2">'))

    def test_status_values_and_approval_gate(self):
        with scratch() as d:
            _, problems = build(variant(d, 'lyric-status="text-approved"', 'lyric-status="final"'))
            self.assertTrue(any('lyric-status' in p for p in problems))
            draft = variant(d, 'lyric-status="text-approved"', 'lyric-status="draft"')
            self.assertEqual(cli('check', draft).returncode, 0)
            gated = cli('check', draft, '--require-approved')
            self.assertEqual(gated.returncode, 1)
            self.assertIn('approval required', gated.stdout)

    def test_events_export_refuses_existing_output_and_problems(self):
        with scratch() as d:
            out = d/'events.json'
            self.assertEqual(cli('events', FIXTURE, out).returncode, 0)
            self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['schema'], 'lyric-handoff/1')
            self.assertEqual(cli('events', FIXTURE, out).returncode, 1)
            bad = variant(d, '<verse n="1"><syl con="u">同</syl></verse>', '<verse n="1"><syl>同</syl></verse>')
            result = cli('events', bad, d/'other.json')
            self.assertEqual(result.returncode, 1)
            self.assertFalse((d/'other.json').exists())


if __name__ == '__main__':
    unittest.main()
