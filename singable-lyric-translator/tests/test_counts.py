"""One home for count-helper CLI cases previously spread across three modules."""
import unittest
from support import run_count, scratch


class CountTests(unittest.TestCase):
    def test_positive_negative_and_extra_lines(self):
        for text,slots,expected in [('让天歌唱\n','4',0),('让天歌唱啊\n','4',1),
                                    ('让天歌唱\n让天歌唱\n','4',1)]:
            with self.subTest(text=text):
                run = run_count(text,'--slots',slots,'--stdin')
                self.assertEqual(run.returncode,expected,run.stdout+run.stderr)

    def test_bilingual_default_filter(self):
        run = run_count('输入等级：B（未验证旋律）\n[Verse]\nMorning light\n清晨微光，引我前行\n盼望常伴着我\n无需决策\n',
                        '--slots','8,6','--stdin')
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_raw_mode_preserves_one_character(self):
        run = run_count('主\n你爱我\n','--slots','1,3','--stdin','--raw-lines')
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_default_one_character_is_a_valid_line(self):
        run = run_count('神\n我们信\n','--slots','1,3','--stdin')
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)

    def test_one_character_cannot_disappear(self):
        run = run_count('神\n我们信\n','--slots','3','--stdin')
        self.assertEqual(run.returncode,1)
        self.assertIn('found 2',run.stdout)

    def test_mixed_chinese_cannot_disappear(self):
        run = run_count('主 Jesus\n我们信\n','--slots','3','--stdin')
        self.assertEqual(run.returncode,1)
        self.assertIn('found 2',run.stdout)

    def test_invalid_slot_lists_fail_loudly(self):
        for slots in ('','0','-1','1,','a',','):
            with self.subTest(slots=slots):
                run = run_count('神\n','--slots',slots,'--stdin')
                self.assertEqual(run.returncode,2)
                self.assertIn('positive integers',run.stderr)

    def test_piped_utf8_without_interpreter_utf8_mode(self):
        run = run_count('神\n','--slots','1','--stdin',python_utf8=False)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('神',run.stdout)

    def test_variants_report_fit_over_under_and_skipped_comments(self):
        with scratch() as folder:
            path = folder/'variants.txt'
            path.write_text('让天歌唱\n让天歌唱啊\n让天\n# skipped\n',encoding='utf-8')
            run = run_count('','--slots','4','--variants',str(path))
            self.assertEqual(run.returncode,0)
            self.assertIn('OVER (+1)',run.stdout)
            self.assertIn('UNDER (-2)',run.stdout)
            self.assertIn('1/3 candidates fit 4 slots',run.stdout)

    def test_variants_exit_zero_does_not_mean_fit(self):
        with scratch() as folder:
            path = folder/'variants.txt'
            path.write_text('让天歌唱啊\n',encoding='utf-8')
            run = run_count('','--slots','4','--variants',str(path))
            self.assertEqual(run.returncode,0)
            self.assertIn('0/1 candidates fit',run.stdout)

    def test_variants_require_one_slot_and_a_readable_file(self):
        with scratch() as folder:
            path = folder/'variants.txt'
            path.write_text('让天歌唱\n',encoding='utf-8')
            for slots,file in [('4,3',str(path)),('4',str(folder/'missing.txt'))]:
                with self.subTest(slots=slots,file=file):
                    run = run_count('','--slots',slots,'--variants',file)
                    self.assertNotEqual(run.returncode,0)


if __name__ == '__main__':
    unittest.main()
