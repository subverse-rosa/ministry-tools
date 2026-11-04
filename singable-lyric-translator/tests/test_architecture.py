"""Regression tests for annotated relation contracts and actual hook segmentation.

Annotations require a human/LLM reviewer; this is NOT semantic inference from text.
Run: python -m unittest discover -s tests -p "test_*.py"
"""
import json
import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = json.loads((HERE/'fixtures'/'architecture.json').read_text(encoding='utf-8'))

def chars(text):
    return ''.join(re.findall(r'[㐀-䶿一-鿿豈-﫿]', text))

def hook_fit(lines, hook=None, boundary=4, slots=8):
    hook = FIX['hook']['text'] if hook is None else hook
    return all(len(chars(line)) == slots and chars(line)[:boundary] == hook
               for line in lines)

def relation_errors(source, target):
    return [key for key in source if target.get(key) != source[key]]

class ArchitectureTests(unittest.TestCase):
    def test_six_parallel_lines(self):
        self.assertEqual(len(FIX['hook']['valid']), 6)
        self.assertTrue(hook_fit(FIX['hook']['valid']))
        self.assertEqual(len({chars(s)[4:] for s in FIX['hook']['valid']}), 6)

    def test_equal_count_wrong_boundary(self):
        bad = FIX['hook']['bad_segmentation']
        self.assertEqual(len(chars(bad[0])), 8)
        self.assertFalse(hook_fit(bad))

    def test_parallel_hook_drift(self):
        self.assertFalse(hook_fit(FIX['hook']['valid'] + FIX['hook']['bad_parallel']))

    def test_relation_contract_positive_and_negative(self):
        for case in FIX['relations']:
            with self.subTest(case=case['id']):
                self.assertEqual(relation_errors(case['source'], case['valid']), [])
                self.assertIn(case['id'], relation_errors(case['source'], case['invalid']))

    def test_quote_petition_speaker(self):
        good = '「求祢救我」我向主求'
        bad = '「求祢救我」祂向我求'
        self.assertEqual(len(chars(good)), 8)
        self.assertEqual(len(chars(bad)), 8)
        self.assertTrue(good.startswith('「求祢救我」'))
        self.assertNotEqual(good.split('」')[1], bad.split('」')[1])

if __name__ == '__main__':
    unittest.main()
