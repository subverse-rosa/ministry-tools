"""Formatting-tolerant declaration lint; it does not establish model compliance."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT/'tests/fixtures/rule_inventory.json').read_text(encoding='utf-8'))['rules']
SKILL = (ROOT/'skill/SKILL.md').read_text(encoding='utf-8')


def missing_rules(text):
    text = re.sub(r'(?m)^\s{0,3}#{1,6}\s*','',text).replace('**','').replace('`','')
    return [r['id']+': '+r['name'] for r in RULES if not re.search(r['pattern'],text,re.S|re.I)]


class ContractTests(unittest.TestCase):
    def test_established_rule_declarations_remain_present(self):
        self.assertEqual(missing_rules(SKILL),[])

    def test_declared_defaults_and_retired_rejection(self):
        plain = SKILL.replace('**','')
        self.assertRegex(plain,r'Default\s+Adaptive analysis')
        self.assertNotRegex(plain,r'Default\s+Strict')
        self.assertNotIn('is not evaluated as-is',plain)
        self.assertIn('Strict mismatch',plain)

    def test_lint_accepts_plain_markdown_formatting(self):
        plain = re.sub(r'(?m)^#{1,6}\s*','',SKILL).replace('**','').replace('`','')
        self.assertEqual(missing_rules(plain),[])


if __name__ == '__main__':
    unittest.main()
