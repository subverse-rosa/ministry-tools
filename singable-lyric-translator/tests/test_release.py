"""Validate actual export payload, distribution integrity and build isolation."""
import importlib.util
import io
from pathlib import Path
import unittest
import zipfile
from support import scratch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_builder',ROOT/'tools/build_release.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
spec2=importlib.util.spec_from_file_location('release_archiver',ROOT/'tools/archive_release.py')
archiver=importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(archiver)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.cfg,self.payload=builder.validate_source(ROOT)

    def test_platform_payloads_are_identical(self):
        standard=builder.zip_bytes(self.payload,self.cfg['name']+'/')
        gemini=builder.zip_bytes(self.payload)
        with zipfile.ZipFile(io.BytesIO(standard)) as a,zipfile.ZipFile(io.BytesIO(gemini)) as b:
            self.assertIn('SKILL.md',b.namelist())
            self.assertEqual(set(b.namelist()), set(self.payload))
            self.assertEqual(set(a.namelist()), {self.cfg['name']+'/'+p for p in self.payload})
            for rel,data in self.payload.items():
                self.assertEqual(a.read(self.cfg['name']+'/'+rel),data)
                self.assertEqual(b.read(rel),data)
            self.assertFalse(any('/tests/' in n or 'VERSION' in n or '__pycache__' in n for n in a.namelist()))

    def test_reproducible_export(self):
        self.assertEqual(builder.zip_bytes(self.payload),builder.zip_bytes(self.payload))

    def distribution(self,folder):
        data=builder.zip_bytes(self.payload)
        (folder/builder.UPLOAD_ZIP).write_bytes(data)
        (folder/'SHA256.txt').write_text(builder.sha(data)+'  '+builder.UPLOAD_ZIP+'\n',encoding='utf-8')

    def test_tracked_distribution_checks_bytes_and_source(self):
        with scratch() as folder:
            self.distribution(folder)
            result=builder.verify_distribution(folder,self.cfg,self.payload)
            self.assertEqual(result['status'],'verified_same_version_source')
            changed=dict(self.payload)
            changed['SKILL.md']+=b'\n'
            with self.assertRaisesRegex(ValueError,'Same-version distribution differs'):
                builder.verify_distribution(folder,self.cfg,changed)

    def test_distribution_rejects_bad_checksum_and_missing_pair(self):
        with scratch() as folder:
            self.distribution(folder)
            (folder/'SHA256.txt').write_text('0'*64+'  '+builder.UPLOAD_ZIP,encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'does not match'):
                builder.verify_distribution(folder,self.cfg,self.payload)
            (folder/'SHA256.txt').unlink()
            with self.assertRaisesRegex(ValueError,'must both exist'):
                builder.verify_distribution(folder,self.cfg,self.payload)

    def test_next_source_version_may_keep_previous_distribution(self):
        with scratch() as folder:
            self.distribution(folder)
            future=dict(self.cfg,version='999.0.0')
            self.assertEqual(builder.verify_distribution(folder,future,self.payload)['status'],'verified_older_distribution')
            older=dict(self.cfg,version='0.0.1')
            with self.assertRaisesRegex(ValueError,'newer than source'):
                builder.verify_distribution(folder,older,self.payload)

    def test_explicit_output_preserves_tracked_distribution(self):
        with scratch() as folder:
            self.distribution(folder)
            paths=(folder/builder.UPLOAD_ZIP,folder/'SHA256.txt')
            before=[p.read_bytes() for p in paths]
            destination=builder.export_release(folder,self.cfg,self.payload,{'status':'test'},folder/'dist')
            self.assertEqual([p.read_bytes() for p in paths],before)
            self.assertEqual((destination/builder.UPLOAD_ZIP).read_bytes(),builder.zip_bytes(self.payload))
            self.assertTrue((destination/f"{self.cfg['name']}_v{self.cfg['version']}_manifest.json").is_file())

    def test_output_cannot_pollute_source_folders(self):
        with scratch() as folder:
            for rel in ('','skill','skill/subfolder','tests','tools','tools/subfolder','.git'):
                with self.subTest(path=rel),self.assertRaisesRegex(ValueError,'outside source/runtime'):
                    builder.export_release(folder,self.cfg,self.payload,{},folder/rel)
            self.assertEqual(list(folder.iterdir()),[])

    def test_current_upload_zip_refreshes_and_matches_gemini(self):
        with scratch() as folder:
            target=builder.update_upload_zip(folder,self.payload)
            self.assertEqual(target.read_bytes(),builder.zip_bytes(self.payload))
            newer=dict(self.payload)
            newer['SKILL.md']+=b'\n'
            builder.update_upload_zip(folder,newer)
            self.assertEqual(target.read_bytes(),builder.zip_bytes(newer))
            self.assertFalse((folder/(builder.UPLOAD_ZIP+'.tmp')).exists())

    def test_upload_zip_name_is_latest_not_master(self):
        self.assertEqual(builder.UPLOAD_ZIP,'singable-lyric-translator_latest.zip')

    def test_version_stamp_must_match_release_json(self):
        text=self.payload['SKILL.md'].decode('utf-8')
        builder.check_version_stamp(text,self.cfg)
        with self.assertRaises(ValueError):
            builder.check_version_stamp(text.replace('**Version:** '+self.cfg['version'],'**Version:** 0.0.0'),self.cfg)
        with self.assertRaises(ValueError):
            builder.check_version_stamp(text.replace('**Version:**','Version:'),self.cfg)

    def test_archiver_refuses_current_and_malformed_versions(self):
        with self.assertRaises(ValueError):
            archiver.ensure_archivable(self.cfg['version'],self.cfg)
        with self.assertRaises(ValueError):
            archiver.ensure_archivable('1.3',self.cfg)
        archiver.ensure_archivable('0.0.1',self.cfg)

    def test_standalone_uses_exact_rulebook(self):
        plan=builder.export_plan(self.cfg,self.payload,{'status':'test'})
        standalone=next(data for p,data in plan.items() if p.endswith('/SKILL.md'))
        self.assertEqual(standalone,self.payload['SKILL.md'])

    def test_same_version_refuses_changed_artifacts_before_writes(self):
        with scratch() as folder:
            dest=Path(folder)
            builder.write_plan(dest,{'existing.txt':b'first'})
            builder.write_plan(dest,{'existing.txt':b'first'})
            with self.assertRaises(ValueError):
                builder.write_plan(dest,{'new.txt':b'new','existing.txt':b'changed'})
            self.assertFalse((dest/'new.txt').exists())
            self.assertEqual((dest/'existing.txt').read_bytes(),b'first')

    def test_rejects_traversal_and_unlisted_files(self):
        with scratch() as folder:
            root=Path(folder)
            (root/'skill').mkdir()
            (root/'skill/SKILL.md').write_text('safe',encoding='utf-8')
            with self.assertRaises(ValueError):
                builder.runtime_payload(root,{'runtime_files':['SKILL.md','../outside.md']})
            (root/'skill/VERSION').write_text('1.0.0',encoding='utf-8')
            with self.assertRaises(ValueError):
                builder.runtime_payload(root,{'runtime_files':['SKILL.md']})


if __name__=='__main__':
    unittest.main()
