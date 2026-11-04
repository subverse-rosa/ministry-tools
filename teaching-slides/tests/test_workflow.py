import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import sys
import unittest
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / 'skill/teaching-slides'
sys.path.insert(0, str(SKILL / 'scripts'))

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    item = importlib.util.module_from_spec(spec); spec.loader.exec_module(item)
    return item

project = module('project_test', SKILL / 'scripts/project.py')
library = module('library_test', SKILL / 'scripts/library.py')
release = module('release_test', REPO / 'tools/release.py')

class RecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.source = self.root / 'manuscript.txt'; self.source.write_text('First paragraph.\n\nSecond paragraph.', encoding='utf-8')
        self.folder = self.root / 'demo'; project.init_project(self.folder, [self.source])

    def tearDown(self):
        self.temp.cleanup()

    def observation(self):
        return {'schema_version': 1, 'project_id': 'demo', 'observations': [{
            'id': 'fb-1', 'pattern_id': 'paired-positions', 'scope': 'project', 'target': 'demo',
            'action': 'keep', 'reason': 'The comparison was easy to follow.', 'context': 'teaching_use',
            'reporter': 'speaker', 'created_at': '2026-10-31'}]}

    def test_source_retention_and_partial_coverage(self):
        result = project.check_project(self.folder)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['unmapped'], 2)
        self.assertFalse(result['authority_resolved'])
        self.assertEqual((self.folder / 'source/S01.txt').read_bytes(), self.source.read_bytes())
        with self.assertRaises(ValueError): project.init_project(self.folder, [self.source])

    def test_source_and_record_tampering_detected(self):
        (self.folder / 'source/S01.txt').write_text('changed', encoding='utf-8')
        (self.folder / 'records/S01.json').write_text('{"segments":[]}', encoding='utf-8')
        self.assertEqual(len(project.check_project(self.folder)['errors']), 2)

    def test_mapping_ids_and_omission_reasons(self):
        data = project.read(self.folder / 'project.json')
        data['slide_map'] = [{'slide_id': 'one', 'treatment': 'summary', 'decision': 'Opening', 'source_segments': ['S01-P0001']}]
        data['omissions'] = [{'source_segments': ['S01-P0002'], 'reason': 'Author requested excerpt.'}]
        project.write(self.folder / 'project.json', data)
        self.assertEqual(project.check_project(self.folder)['unmapped'], 0)
        data['slide_map'][0]['source_segments'] = ['unknown']
        project.write(self.folder / 'project.json', data)
        self.assertIn('Unknown source segments', ' '.join(project.check_project(self.folder)['errors']))

    def test_paths_cannot_escape_project(self):
        data = project.read(self.folder / 'project.json'); data['sources'][0]['path'] = '../manuscript.txt'
        project.write(self.folder / 'project.json', data)
        self.assertIn('escapes', ' '.join(project.check_project(self.folder)['errors']))

    def test_feedback_is_pending_deduplicated_and_keeps_decisions(self):
        before = project.read(self.folder / 'project.json')
        batch = self.observation(); self.assertEqual(project.import_feedback(self.folder, batch)['imported'], 1)
        self.assertEqual(project.import_feedback(self.folder, batch)['imported'], 0)
        after = project.read(self.folder / 'project.json')
        self.assertEqual(after['feedback'][0]['status'], 'pending')
        self.assertEqual(before['decisions'], after['decisions'])

    def test_invalid_batch_is_atomic_and_id_conflicts_rejected(self):
        batch = self.observation(); project.import_feedback(self.folder, batch)
        original = (self.folder / 'project.json').read_bytes()
        changed = copy.deepcopy(batch); changed['observations'][0]['reason'] = 'different'
        with self.assertRaises(ValueError): project.import_feedback(self.folder, changed)
        malformed = self.observation(); malformed['observations'][0]['id'] = 'fb-2'
        malformed['observations'].append(dict(malformed['observations'][0], id='fb-3', scope='all-future-projects'))
        with self.assertRaises(ValueError): project.import_feedback(self.folder, malformed)
        self.assertEqual(original, (self.folder / 'project.json').read_bytes())

    def test_feedback_cannot_approve_itself_or_use_wrong_project(self):
        batch = self.observation(); batch['observations'][0]['status'] = 'confirmed'
        with self.assertRaises(ValueError): project.import_feedback(self.folder, batch)

    def test_mixed_gallery_export_routes_by_project_id(self):
        batch = self.observation(); batch['project_id'] = None
        batch['observations'][0]['project_id'] = 'demo'
        batch['observations'].append(dict(batch['observations'][0], id='fb-other', project_id='elsewhere'))
        result = project.import_feedback(self.folder, batch)
        self.assertEqual(result['imported'], 1)
        self.assertEqual(result['skipped_other_projects'], 1)
        self.assertEqual(len(project.read(self.folder / 'project.json')['feedback']), 1)
        batch = self.observation(); batch['project_id'] = 'elsewhere'
        with self.assertRaises(ValueError): project.import_feedback(self.folder, batch)

    def test_decision_link_must_point_to_retained_record(self):
        data = project.read(self.folder / 'project.json')
        data['decisions'] = [{'id': 'd2', 'scope': 'project', 'target': 'demo', 'status': 'confirmed',
                              'wording': 'Keep text', 'basis': 'User instruction', 'supersedes': ['missing']}]
        project.write(self.folder / 'project.json', data)
        self.assertIn('superseded', ' '.join(project.check_project(self.folder)['errors']))

    def test_docx_run_false_is_preserved(self):
        doc = self.root / 'sample.docx'
        with ZipFile(doc, 'w') as z:
            z.writestr('word/document.xml', '<w:document xmlns:w="'+project.NS['w']+'"><w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:rPr><w:b w:val="0"/><w:i/></w:rPr><w:t>Sample</w:t></w:r></w:p></w:body></w:document>')
        row = project.extract(doc, 'S01')['segments'][0]
        self.assertFalse(row['runs'][0]['bold']); self.assertTrue(row['runs'][0]['italic'])
        self.assertEqual(row['style'], 'Heading1')

    def test_pptx_uses_presentation_order(self):
        doc = self.root / 'sample.pptx'
        with ZipFile(doc, 'w') as z:
            z.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="'+project.NS['p']+'" xmlns:r="'+project.NS['r']+'"><p:sldIdLst><p:sldId id="256" r:id="r2"/><p:sldId id="257" r:id="r1"/></p:sldIdLst></p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels', '<Relationships><Relationship Id="r1" Target="slides/slide1.xml"/><Relationship Id="r2" Target="slides/slide2.xml"/></Relationships>')
            for n in [1, 2]:
                z.writestr(f'ppt/slides/slide{n}.xml', f'<p:sld xmlns:p="{project.NS["p"]}" xmlns:a="{project.NS["a"]}"><p:sp><p:txBody><a:p><a:r><a:t>Slide {n}</a:t></a:r></a:p></p:txBody></p:sp></p:sld>')
        self.assertEqual([r['text'] for r in project.extract(doc, 'S01')['segments']], ['Slide 2', 'Slide 1'])

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name) / 'library'
        shutil.copytree(SKILL / 'assets/library', self.root)

    def tearDown(self): self.temp.cleanup()

    def test_real_catalog_and_missing_relationships(self):
        result = library.check(self.root)
        self.assertEqual(result['errors'], [])
        self.assertIn('causality', result['unrepresented_relationships'])
        found = {row['id'] for row in library.find('比较', self.root)}
        self.assertTrue({'paired-positions', 'terms-comparison'}.issubset(found))
        self.assertEqual(library.find('nonexistent unique marker', self.root), [])

    def test_tampered_preview_prevents_build(self):
        data = library.load(self.root)
        (self.root / data['patterns'][0]['examples'][0]['preview']).write_bytes(b'not-the-preview')
        with self.assertRaises(ValueError): library.build(self.root)

    def test_duplicate_examples_are_rejected(self):
        data = library.load(self.root)
        data['patterns'][0]['examples'].append(copy.deepcopy(data['patterns'][0]['examples'][0]))
        (self.root / 'catalog.json').write_text(json.dumps(data), encoding='utf-8')
        self.assertIn('Duplicate example', ' '.join(library.check(self.root)['errors']))

    def test_data_cannot_substitute_gallery_build_slots(self):
        data = library.load(self.root); data['patterns'][0]['title'] = '__GALLERY_SCRIPT__'
        (self.root / 'catalog.json').write_text(json.dumps(data), encoding='utf-8')
        library.build(self.root)
        from html.parser import HTMLParser
        class Parser(HTMLParser):
            def __init__(self): super().__init__(); self.capture=False; self.value=''
            def handle_starttag(self, tag, attrs): self.capture=tag=='script' and dict(attrs).get('id')=='catalog-data'
            def handle_data(self, text):
                if self.capture:self.value+=text
            def handle_endtag(self, tag):
                if tag=='script':self.capture=False
        parser=Parser();parser.feed((self.root/'index.html').read_text(encoding='utf-8'))
        self.assertEqual(json.loads(parser.value)['patterns'][0]['title'],'__GALLERY_SCRIPT__')

    def test_reusable_status_requires_adaptation_evidence(self):
        data = library.load(self.root); data['patterns'][0]['status'] = 'reusable'
        (self.root / 'catalog.json').write_text(json.dumps(data), encoding='utf-8')
        self.assertIn('artifact', ' '.join(library.check(self.root)['errors']))

    def test_gallery_safe_embedding_and_reproducibility(self):
        data = library.load(self.root); payload = '</script><script>window.bad=true</script>'
        data['patterns'][0]['title'] = payload
        (self.root / 'catalog.json').write_text(json.dumps(data), encoding='utf-8')
        library.build(self.root); first = (self.root / 'index.html').read_bytes()
        self.assertNotIn(payload.encode(), first)
        self.assertIn(b'\\u003c/script', first)
        library.build(self.root); self.assertEqual(first, (self.root / 'index.html').read_bytes())

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        shutil.copytree(REPO / 'skill', self.repo / 'skill')
        shutil.copy2(REPO / 'release.json', self.repo / 'release.json')

    def tearDown(self): self.temp.cleanup()

    def test_package_is_reproducible_and_contains_only_runtime(self):
        first = release.build(self.repo); second = release.build(self.repo)
        self.assertEqual(first['package'], json.loads((self.repo / 'release.json').read_text(encoding='utf-8'))['package_name'])
        self.assertEqual(first['package_sha256'], second['package_sha256'])
        with ZipFile(self.repo / 'dist' / first['package']) as z:
            self.assertTrue(all(n.startswith('teaching-slides/') for n in z.namelist()))
            self.assertEqual(len(z.namelist()), len(first['files']))

    def test_install_is_exact_and_refuses_unmanaged_edits(self):
        target = self.root / 'skills/teaching-slides'
        result = release.install(target, self.repo)
        self.assertTrue(result['verified_equal'])
        self.assertEqual(release.inventory(target), release.inventory(self.repo / 'skill/teaching-slides'))
        (target / 'SKILL.md').write_text('local edit', encoding='utf-8')
        with self.assertRaises(ValueError): release.install(target, self.repo)
        self.assertEqual((target / 'SKILL.md').read_text(), 'local edit')

    def test_managed_update_keeps_backup(self):
        target = self.root / 'skills/teaching-slides'; release.install(target, self.repo)
        file = self.repo / 'skill/teaching-slides/references/feedback.md'; file.write_text(file.read_text()+'\nA scoped clarification.\n', encoding='utf-8')
        result = release.install(target, self.repo)
        self.assertTrue(Path(result['backup']).is_dir())
        self.assertTrue((Path(result['backup']) / 'SKILL.md').is_file())
        self.assertEqual(release.inventory(target), release.inventory(self.repo / 'skill/teaching-slides'))

if __name__ == '__main__': unittest.main()
