"""Focused regression/negative tests; no claims about actual musical quality."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from support import scratch
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rhythm', ROOT / 'skill/scripts/check_rhythm.py')
rhythm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rhythm)


def example():
    return json.loads((ROOT / 'skill/references/capacity-example.json').read_text(encoding='utf-8'))


def accept(data):
    p = data['phrases'][0]
    data['ledger'] = [dict(
        id='D1', phrase=p['id'], source='user turn demo', uncertainty='illustrative',
        mode=data['mode'], before='one melisma', after='two attacks',
        alternatives='retain underlay', semantic_cost='none in this map-only fixture',
        musical_cost='extra attack; needs sing-through', recommendation='split',
        status='accepted', decision_owner='user', reason='explicit demo acceptance',
        baseline_slots=copy.deepcopy(p['baseline_slots']),
        target_slots=copy.deepcopy(p['target_slots']))]


class RhythmTests(unittest.TestCase):
    def test_melisma_is_not_note_count(self):
        result = rhythm.validate(example())
        self.assertEqual(result['phrases'][0]['baseline'], 1)
        self.assertIn('No score/audio transcription', result['limitation'])

    def test_strict_rejects_changed_underlay(self):
        d = example()
        d['phrases'][0]['target_slots'] = [{'start': 0, 'end': 1}, {'start': 1, 'end': 2}]
        with self.assertRaisesRegex(rhythm.MapError, 'Strict'):
            rhythm.validate(d)

    def adaptive(self):
        d = example()
        d['mode'] = 'Adaptive'
        d['phrases'][0]['target_slots'] = [{'start': 0, 'end': '1/2'}, {'start': '1/2', 'end': 2}]
        d['phrases'][0]['expected_target'] = 2
        return d

    def test_rational_split_with_accepted_allocation(self):
        d = self.adaptive()
        accept(d)
        self.assertEqual(rhythm.validate(d)['phrases'][0]['target'], 2)

    def test_proposed_recommended_is_not_accepted(self):
        d = self.adaptive()
        accept(d)
        d['ledger'][0]['status'] = 'proposed'
        with self.assertRaisesRegex(rhythm.MapError, 'accepted ledger'):
            rhythm.validate(d)

    def test_acceptance_must_match_actual_allocation(self):
        d = self.adaptive()
        accept(d)
        d['ledger'][0]['target_slots'][0]['end'] = '1/3'
        with self.assertRaisesRegex(rhythm.MapError, 'accepted ledger'):
            rhythm.validate(d)

    def test_tie_cannot_be_subdivided(self):
        d = self.adaptive()
        d['phrases'][0]['events'][1]['tie_from_previous'] = True
        accept(d)
        with self.assertRaisesRegex(rhythm.MapError, 'tie'):
            rhythm.validate(d)

    def test_silence_not_capacity(self):
        d = example()
        d['phrases'][0]['target_slots'][0]['end'] = 4
        with self.assertRaises(rhythm.MapError):
            rhythm.validate(d)

    def test_hard_boundary_cannot_be_crossed(self):
        d = example()
        d['phrases'][0]['boundaries'].append(1)
        with self.assertRaisesRegex(rhythm.MapError, 'hard'):
            rhythm.validate(d)

    def test_source_count_discrepancy_blocks_adoption(self):
        d = example()
        d['phrases'][0]['supplied_count'] = 2
        with self.assertRaisesRegex(rhythm.MapError, 'conflicts'):
            rhythm.validate(d)

    def test_float_beats_rejected(self):
        d = example()
        d['phrases'][0]['events'][0]['end'] = 1.0
        with self.assertRaisesRegex(rhythm.MapError, 'floats'):
            rhythm.validate(d)

    def test_pickup_tuplet_durations_are_exact(self):
        d = example()
        p = d['phrases'][0]
        p['events'] = [
            dict(start='-1/3', end=0, kind='note', pitch='C4', stress='weak'),
            dict(start=0, end='2/3', kind='note', pitch='D4', stress='strong'),
            dict(start='2/3', end=1, kind='rest')]
        p['boundaries'] = ['-1/3', '2/3', 1]
        p['baseline_slots'] = p['target_slots'] = [dict(start='-1/3', end='2/3')]
        self.assertEqual(rhythm.validate(d)['phrases'][0]['target'], 1)

    def test_overlapping_slots_rejected(self):
        d = self.adaptive()
        d['phrases'][0]['target_slots'][0]['end'] = 1
        with self.assertRaisesRegex(rhythm.MapError, 'overlap'):
            rhythm.validate(d)

    def test_gap_requires_explicit_rest(self):
        d = example()
        d['phrases'][0]['events'][2]['start'] = 3
        with self.assertRaisesRegex(rhythm.MapError, 'gap'):
            rhythm.validate(d)

    def test_different_pitch_merge_rejected(self):
        d = example()
        d['mode'] = 'Adaptive'
        p = d['phrases'][0]
        p['baseline_slots'] = [{'start': 0, 'end': 1}, {'start': 1, 'end': 2}]
        p['supplied_count'] = 2
        p['events'][1]['pitch'] = 'D4'
        accept(d)
        with self.assertRaisesRegex(rhythm.MapError, 'different pitches'):
            rhythm.validate(d)

    def test_same_pitch_merge_allowed(self):
        d = example()
        d['mode'] = 'Adaptive'
        p = d['phrases'][0]
        p['baseline_slots'] = [{'start': 0, 'end': 1}, {'start': 1, 'end': 2}]
        p['supplied_count'] = 2
        accept(d)
        self.assertEqual(rhythm.validate(d)['phrases'][0]['target'], 1)

    def test_recomposition_requires_explicit_request_new_version(self):
        d = example()
        d['mode'] = 'Recomposition'
        with self.assertRaisesRegex(rhythm.MapError, 'authorization'):
            rhythm.validate(d)
        d.update(authorization='user asks for new melody', original_map_version='demo-0')
        self.assertEqual(rhythm.validate(d)['mode'], 'Recomposition')

    def test_cli_invalid_input_no_traceback(self):
        with scratch() as temp:
            p = Path(temp) / 'bad.json'
            p.write_text('{}', encoding='utf-8')
            run = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'skill/scripts/check_rhythm.py'), str(p)],
                                 capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(run.returncode, 1)
            self.assertEqual(json.loads(run.stdout)['result'], 'INVALID_MAP')
            self.assertNotIn('Traceback', run.stderr)



if __name__ == '__main__':
    unittest.main()
