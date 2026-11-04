"""Behavior tests use synthetic sources and minimal OOXML, never private sermon content."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

SKILL = Path(__file__).resolve().parents[1] / 'skill/teaching-slides'
sys.path.insert(0, str(SKILL / 'scripts'))
import project
import workflow

def pptx(path, texts, table=False, notes=None):
    p, a, r = (project.NS[key] for key in ['p', 'a', 'r'])
    with ZipFile(path, 'w') as archive:
        ids = ''.join(f'<p:sldId id="{255+i}" r:id="r{i}"/>' for i in range(1, len(texts)+1))
        archive.writestr('ppt/presentation.xml', f'<p:presentation xmlns:p="{p}" xmlns:r="{r}"><p:sldIdLst>{ids}</p:sldIdLst></p:presentation>')
        archive.writestr('ppt/_rels/presentation.xml.rels', '<Relationships>'+''.join(f'<Relationship Id="r{i}" Target="slides/slide{i}.xml"/>' for i in range(1,len(texts)+1))+'</Relationships>')
        for i, text in enumerate(texts, 1):
            body = f'<p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>'
            if table:
                body = '<p:graphicFrame><a:graphic><a:graphicData><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>'+text+'</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
            archive.writestr(f'ppt/slides/slide{i}.xml', f'<p:sld xmlns:p="{p}" xmlns:a="{a}"><p:cSld><p:spTree>{body}</p:spTree></p:cSld></p:sld>')
            if notes is not None:
                archive.writestr(f'ppt/slides/_rels/slide{i}.xml.rels', f'<Relationships><Relationship Id="n" Type="notes/notesSlide" Target="../notesSlides/notesSlide{i}.xml"/></Relationships>')
                archive.writestr(f'ppt/notesSlides/notesSlide{i}.xml', f'<p:notes xmlns:p="{p}" xmlns:a="{a}"><a:p><a:r><a:t>{notes}</a:t></a:r></a:p></p:notes>')

class RevisionDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.source = self.root/'manuscript.txt'; self.source.write_text('Alpha\n\nBeta',encoding='utf-8')
        self.folder = self.root/'demo'; project.init_project(self.folder, [self.source])
        self.deck = self.root/'synthetic.pptx'; pptx(self.deck, ['Alpha','Beta'])

    def tearDown(self): self.temp.cleanup()
    def data(self): return project.read(self.folder/'project.json')
    def save(self, data): project.write(self.folder/'project.json', data)
    def mapped(self):
        data=self.data(); data['content_authority']={'source_ids':['S01'],'basis':'Synthetic author instruction'}
        data['content_policy']='full_content_on_slides'
        data['slide_map']=[{'slide_id':f'slide-{i:03}','source_segments':[f'S01-P{i:04}'],'treatment':'verbatim','relationship':'synthesis','pattern_ids':[],'decision':'Synthetic exact wording'} for i in [1,2]]
        self.save(data)
    def registered(self):
        self.mapped();return workflow.register_output(self.folder,self.deck,'O1')['output']
    def reviewed(self):
        output=self.registered()
        for method in ['content_review','visual_review']:
            workflow.record_review(self.folder,output,method,'passed','full','Synthetic attestation for testing only','test fixture')
        return output
    def observation(self, **extra):
        return {'schema_version':1,'project_id':'demo','observations':[dict(id='fb-1',pattern_id='focused-statement',scope='project',target='demo',action='change',reason='Synthetic line should be clearer.',context='screen_review',reporter='test fixture',created_at='2026-11-03',**extra)]}

    def test_compare_reports_content_without_mutating_sources(self):
        new=self.root/'new.txt';new.write_text('Alpha revised\n\nBeta',encoding='utf-8')
        before=project.sha(self.source);report=workflow.compare(self.source,new)
        self.assertEqual(report['summary']['modified'],1)
        self.assertEqual(project.sha(self.source),before)
        self.assertIn('Alpha revised',workflow.markdown(report))

    def test_insert_does_not_make_unchanged_paragraphs_modified(self):
        new=self.root/'new.txt';new.write_text('Intro\n\nAlpha\n\nBeta',encoding='utf-8')
        self.assertEqual(workflow.compare(self.source,new)['summary'],{'added':1})

    def test_reorder_is_detected_without_automatic_mapping_transfer(self):
        new=self.root/'new.txt';new.write_text('Beta\n\nAlpha',encoding='utf-8')
        self.assertEqual(workflow.compare(self.source,new)['summary'],{'moved':1})

    def test_format_change_with_same_text_is_detected(self):
        w=project.NS['w'];old=self.root/'old.docx';new=self.root/'new.docx'
        for path, bold in [(old,'0'),(new,'1')]:
            with ZipFile(path,'w') as z:z.writestr('word/document.xml',f'<w:document xmlns:w="{w}"><w:body><w:p><w:r><w:rPr><w:b w:val="{bold}"/></w:rPr><w:t>Alpha</w:t></w:r></w:p></w:body></w:document>')
        self.assertEqual(workflow.compare(old,new)['summary'],{'structure_or_format':1})

    def test_table_text_and_speaker_note_changes_are_included(self):
        old=self.root/'old.pptx';new=self.root/'new.pptx'
        pptx(old,['Alpha'],table=True,notes='Old note');pptx(new,['Beta'],table=True,notes='New note')
        report=workflow.compare(old,new);self.assertEqual(report['summary'],{'modified':1,'notes_modified':1})
        self.assertEqual(project.extract(new,'S')['segments'][0]['notes_text'],'New note')
        pptx(new,['Alpha'],table=True,notes='New note')
        self.assertEqual(workflow.compare(old,new)['summary'],{'notes_modified':1})

    def test_revision_keeps_old_snapshot_and_decisions(self):
        self.mapped();before=copy.deepcopy(self.data())
        new=self.root/'new.txt';new.write_text('Alpha revised\n\nBeta',encoding='utf-8')
        result=workflow.revise(self.folder,'S01',new);after=self.data()
        self.assertEqual(after['slide_map'],before['slide_map']);self.assertEqual(after['decisions'],before['decisions'])
        self.assertEqual(project.sha(self.folder/'source/S01.txt'),before['sources'][0]['sha256'])
        self.assertTrue(Path(result['report']).is_file());self.assertEqual(len(after['sources']),2)
        self.assertEqual(after['source_revisions'][0]['status'],'pending')

    def test_note_page_numbers_are_not_reported_as_speaker_edits(self):
        old=self.root/'old.pptx';new=self.root/'new.pptx'
        p,a=project.NS['p'],project.NS['a']
        for file,number in [(old,'1'),(new,'2')]:
            pptx(file,['Alpha'])
            with ZipFile(file,'a') as z:
                z.writestr('ppt/slides/_rels/slide1.xml.rels','<Relationships><Relationship Id="n" Type="notes/notesSlide" Target="../notesSlides/notesSlide1.xml"/></Relationships>')
                z.writestr('ppt/notesSlides/notesSlide1.xml',f'<p:notes xmlns:p="{p}" xmlns:a="{a}"><p:sp><p:nvSpPr><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>{number}</a:t></a:r></a:p></p:txBody></p:sp></p:notes>')
        self.assertEqual(workflow.compare(old,new)['summary'],{})

    def test_revision_adoption_updates_authority_but_not_approved_mappings(self):
        self.mapped();original=self.data()['slide_map']
        new=self.root/'new.txt';new.write_text('Alpha revised\n\nBeta',encoding='utf-8')
        result=workflow.revise(self.folder,'S01',new)
        workflow.decide_revision(self.folder,result['revision'],'adopt','Use corrected draft','Synthetic author instruction')
        self.assertEqual(self.data()['content_authority']['source_ids'],[result['new_source']])
        self.assertEqual(self.data()['slide_map'],original)

    def test_keep_existing_resolves_revision_without_switching_sources(self):
        self.mapped();new=self.root/'new.txt';new.write_text('Alternate',encoding='utf-8')
        revision=workflow.revise(self.folder,'S01',new)['revision']
        workflow.decide_revision(self.folder,revision,'keep-existing','Retain current draft','Synthetic instruction')
        self.assertEqual(self.data()['content_authority']['source_ids'],['S01'])

    def test_valid_records_are_not_automatically_delivery_ready(self):
        self.assertEqual(project.check_project(self.folder)['errors'],[])
        result=workflow.delivery_check(self.folder,'missing')
        self.assertTrue(result['record_valid']);self.assertFalse(result['ready'])

    def test_registered_output_requires_current_full_content_and_visual_reviews(self):
        output=self.registered();self.assertFalse(workflow.delivery_check(self.folder,output)['ready'])
        workflow.record_review(self.folder,output,'content_review','passed','full','Synthetic','test')
        workflow.record_review(self.folder,output,'visual_review','passed','partial','Synthetic partial','test')
        self.assertFalse(workflow.delivery_check(self.folder,output)['ready'])
        workflow.record_review(self.folder,output,'visual_review','passed','full','Synthetic full','test')
        result=workflow.delivery_check(self.folder,output)
        self.assertTrue(result['ready']);self.assertFalse(result['live_use_recorded'])

    def test_changed_output_invalidates_reviews(self):
        output=self.reviewed();record=self.data()['outputs'][0]
        pptx(self.folder/record['path'],['Changed','Beta'])
        result=workflow.delivery_check(self.folder,output)
        self.assertFalse(result['ready']);self.assertIn('changed',' '.join(result['blockers']))

    def test_new_output_does_not_inherit_old_reviews(self):
        self.reviewed();second=workflow.register_output(self.folder,self.deck,'O2')['output']
        self.assertFalse(workflow.delivery_check(self.folder,second)['ready'])

    def test_mapping_change_requires_reregistering_output(self):
        output=self.reviewed();data=self.data();data['slide_map'][0]['decision']='Changed mapping rationale';self.save(data)
        self.assertIn('changed after output registration',' '.join(workflow.delivery_check(self.folder,output)['blockers']))

    def test_full_coverage_requires_mapping_or_explicit_omission(self):
        self.mapped();data=self.data();data['slide_map'][1]['source_segments']=[];self.save(data)
        output=workflow.register_output(self.folder,self.deck,'O1')['output']
        self.assertIn('lack a mapping',' '.join(workflow.delivery_check(self.folder,output)['blockers']))
        data=self.data();data['omissions']=[{'source_segments':['S01-P0002'],'reason':'Synthetic approved omission'}];self.save(data)
        output=workflow.register_output(self.folder,self.deck,'O2')['output']
        self.assertNotIn('lack a mapping',' '.join(workflow.delivery_check(self.folder,output)['blockers']))

    def test_pending_revision_blocks_delivery_until_disposition(self):
        output=self.reviewed();new=self.root/'new.txt';new.write_text('Alternate',encoding='utf-8')
        revision=workflow.revise(self.folder,'S01',new)['revision']
        self.assertIn('Unresolved source revision',' '.join(workflow.delivery_check(self.folder,output)['blockers']))
        workflow.decide_revision(self.folder,revision,'keep-existing','Not for this delivery','Synthetic instruction')
        self.assertTrue(workflow.delivery_check(self.folder,output)['ready'])

    def test_feedback_can_bind_to_a_specific_output(self):
        output=self.registered();batch=self.observation(output_id=output);project.import_feedback(self.folder,batch)
        self.assertEqual(self.data()['feedback'][0]['artifact_sha256'],self.data()['outputs'][0]['sha256'])
        self.assertEqual(project.import_feedback(self.folder,batch)['imported'],0)

    def test_wrong_feedback_output_hash_is_rejected_atomically(self):
        output=self.registered();before=(self.folder/'project.json').read_bytes()
        with self.assertRaises(ValueError):project.import_feedback(self.folder,self.observation(output_id=output,artifact_sha256='wrong'))
        self.assertEqual(before,(self.folder/'project.json').read_bytes())

    def test_applied_feedback_needs_output_and_preserves_original_observation(self):
        project.import_feedback(self.folder,self.observation());before=copy.deepcopy(self.data()['feedback'][0])
        with self.assertRaises(ValueError):workflow.resolve_feedback(self.folder,'fb-1','applied','Fixed','Synthetic instruction')
        output=self.registered();workflow.resolve_feedback(self.folder,'fb-1','applied','Fixed in this output','Synthetic instruction',output)
        feedback=self.data()['feedback'][0]
        self.assertEqual(feedback['reason'],before['reason']);self.assertEqual(feedback['scope'],before['scope'])
        self.assertEqual(feedback['resolution_history'][0]['output_id'],output)
        self.assertEqual(project.import_feedback(self.folder,self.observation())['imported'],0)

    def test_resolution_history_supersedes_explicitly(self):
        project.import_feedback(self.folder,self.observation())
        first=workflow.resolve_feedback(self.folder,'fb-1','deferred','Later','Synthetic decision')
        output=self.registered();second=workflow.resolve_feedback(self.folder,'fb-1','applied','Now fixed','Synthetic decision',output)
        self.assertEqual(len(self.data()['feedback'][0]['resolution_history']),2)
        prior=next(r for r in self.data()['decisions'] if r['id']==first['decision_id'])
        latest=next(r for r in self.data()['decisions'] if r['id']==second['decision_id'])
        self.assertEqual(prior['status'],'superseded');self.assertIn(prior['id'],latest['supersedes'])

    def test_material_feedback_blocks_but_ordinary_suggestions_warn(self):
        output=self.reviewed();project.import_feedback(self.folder,self.observation())
        result=workflow.delivery_check(self.folder,output);self.assertTrue(result['ready']);self.assertTrue(result['warnings'])
        data=self.data();data['feedback'][0]['delivery_blocking']=True;self.save(data)
        self.assertFalse(workflow.delivery_check(self.folder,output)['ready'])
        workflow.resolve_feedback(self.folder,'fb-1','deferred','Later','Synthetic decision')
        self.assertFalse(workflow.delivery_check(self.folder,output)['ready'])
        workflow.resolve_feedback(self.folder,'fb-1','declined','Not a defect','Synthetic decision')
        self.assertTrue(workflow.delivery_check(self.folder,output)['ready'])

    def test_review_issues_override_an_earlier_pass(self):
        output=self.reviewed();workflow.record_review(self.folder,output,'visual_review','issues','partial','Newly found problem','test')
        self.assertFalse(workflow.delivery_check(self.folder,output)['ready'])

    def test_delivery_cli_uses_distinct_exit_status(self):
        command=[sys.executable,str(SKILL/'scripts/project.py'),'check',str(self.folder)]
        self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
        result=subprocess.run(command+['--for-delivery','--output','missing'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,1);self.assertFalse(json.loads(result.stdout)['ready'])

if __name__=='__main__':unittest.main()
