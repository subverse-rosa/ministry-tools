"""Regressions for silent omissions and empty-check false passes."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from support import scratch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checker', ROOT/'tests/run_checks.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class EvidenceStatusTests(unittest.TestCase):
    def test_no_checks_is_never_a_pass(self):
        result = checker.evaluate({'id': 'manual', 'assert': ['Read the score']}, 'nonsense')
        self.assertEqual(result['status'], 'MANUAL_REVIEW_REQUIRED')
        self.assertEqual(result['behavioral_validation'], 'not_tested')

    def test_empty_auto_object_still_needs_review(self):
        result = checker.evaluate({'id': 'manual', 'auto': {}}, '')
        self.assertEqual(result['status'], 'MANUAL_REVIEW_REQUIRED')

    def test_auto_pass_does_not_certify_assertions(self):
        result = checker.evaluate({'id': 'auto', 'auto': {'slots': [1]}}, '神')
        self.assertEqual(result['status'], 'AUTO_PASS')
        self.assertTrue(result['manual_review_required'])
        self.assertEqual(result['behavioral_validation'], 'not_tested')

    def test_extra_line_fails_instead_of_truncating(self):
        result = checker.evaluate({'id': 'auto', 'auto': {'slots': [3]}}, '我们信\n神')
        self.assertEqual(result['status'], 'AUTO_FAIL')

    def test_e29_cli_has_nonpass_exit_and_machine_status(self):
        with scratch() as folder:
            reply = folder/'reply.txt'
            reply.write_text('This is not a valid review.', encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
                                     str(ROOT/'tests/run_checks.py'), 'E29', str(reply), '--json'],
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'MANUAL_REVIEW_REQUIRED')


if __name__ == '__main__':
    unittest.main()
