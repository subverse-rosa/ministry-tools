"""New renderer input/conversion invariants, independent of optional PDF libraries."""
import copy
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skill/scripts'))
from notation import degree, rhythm
from engrave_score import mei_events, xml_input
from add_numbers import validate_map

def pdf_map():
    return {'schema_version':1,'tonic':'C4','systems':[{'page':1,'crop':[0,0,500,200],
        'measure_durations':{'1':'2'},'events':[
            {'id':'a','measure':'1','x':50,'pitches':['C4'],'onset':0,'duration':1},
            {'id':'b','measure':'1','x':90,'pitches':['C4'],'onset':1,'duration':1}]}],'ties':[['a','b']]}

class NotationTests(unittest.TestCase):
    def test_musicxml_public_doctype_without_entity_resolution(self):
        self.assertEqual(xml_input(b'<!DOCTYPE score-partwise PUBLIC "test" "https://example.invalid/dtd"><score-partwise/>'),'<score-partwise/>')
        with self.assertRaises(ValueError):xml_input(b'<!DOCTYPE x [<!ENTITY secret SYSTEM "file:///x">]><x/>')

    def test_flat_key_and_reference_octave(self):
        self.assertEqual(degree('Bb3','Bb3'),{'number':1,'octave':0,'alter':0})
        self.assertEqual(degree('Bb4','Bb3'),{'number':1,'octave':1,'alter':0})
        self.assertEqual(degree('Eb4','Bb3')['number'],4)
        self.assertEqual(degree('B3','Bb3')['alter'],1)

    def test_written_and_sounding_register_are_explicit(self):
        self.assertEqual(degree('C5','C4')['octave'],1)
        self.assertEqual(degree('C5','C4',octave_shift=-1)['octave'],0)

    def test_sharp_key_spelling_and_minor_convention(self):
        self.assertEqual(degree('D#4','B3')['alter'],0)
        self.assertEqual(degree('E4','A3','minor')['number'],5)
        self.assertEqual(degree('C4','A3','minor')['alter'],0)
        self.assertEqual(degree('C#4','A3','minor')['alter'],1)

    def test_durations_keep_dots_flags_and_extension(self):
        self.assertEqual(rhythm('3/4'),{'underlines':1,'dot':True,'dashes':0})
        self.assertEqual(rhythm('1/4')['underlines'],2)
        self.assertEqual(rhythm(4)['dashes'],3)
        self.assertEqual(rhythm(3)['dashes'],2)

    def test_unhandled_values_are_not_approximated(self):
        for value in ('1/3',0,-1,0.5):
            with self.subTest(value=value),self.assertRaises(ValueError):rhythm(value)
        with self.assertRaises(ValueError):degree('C+4','C4')

    def test_mei_example_events_and_syllable_extender(self):
        doc=ET.parse(ROOT/'skill/references/score-example.mei').getroot()
        events=mei_events(doc)
        self.assertEqual(len(events),12)
        self.assertEqual(events['n7']['duration'],'3/2')
        self.assertEqual(events['r1']['pitches'],[])
        self.assertEqual(events['n10']['pitches'],['C5'])

    def test_key_signature_accidentals_carry_and_reset(self):
        doc=ET.fromstring('''<mei xmlns="http://www.music-encoding.org/ns/mei"><scoreDef keysig="1f"/>
        <measure><staff n="1"><layer n="1"><note xml:id="a" pname="b" oct="4" dur="4"/>
        <note xml:id="b" pname="b" oct="4" dur="4" accid="n"/>
        <note xml:id="c" pname="b" oct="4" dur="4"/></layer></staff></measure>
        <measure><staff n="1"><layer n="1"><note xml:id="d" pname="b" oct="4" dur="4"/></layer></staff></measure></mei>''')
        events=mei_events(doc)
        self.assertEqual([events[x]['pitches'] for x in 'abcd'],[['Bb4'],['B4'],['B4'],['Bb4']])

    def test_tuplet_display_and_elapsed_time_are_separate(self):
        doc=ET.fromstring('''<mei xmlns="http://www.music-encoding.org/ns/mei"><staff n="1"><layer n="1">
        <tuplet num="3" numbase="2"><note xml:id="a" pname="c" oct="4" dur="8"/></tuplet></layer></staff></mei>''')
        event=mei_events(doc)['a']
        self.assertEqual((event['duration'],event['actual_duration'],event['tuplet']),('1/2','1/3','3'))

    def test_valid_pdf_map_preserves_voice_coverage(self):
        self.assertTrue(validate_map(pdf_map()))

    def test_map_rejects_gap_overlap_and_wrong_measure_total(self):
        for start in ('1/2','3/2'):
            data=pdf_map();data['systems'][0]['events'][1]['onset']=start
            with self.assertRaisesRegex(ValueError,'Gap/overlap'):validate_map(data)
        data=pdf_map();data['systems'][0]['measure_durations']['1']='3'
        with self.assertRaisesRegex(ValueError,'Measure duration'):validate_map(data)

    def test_map_rejects_tie_to_different_pitch(self):
        data=pdf_map();data['systems'][0]['events'][1]['pitches']=['D4']
        with self.assertRaisesRegex(ValueError,'equal nonempty'):validate_map(data)

    def test_map_rejects_duplicate_and_outside_crop(self):
        data=pdf_map();data['systems'][0]['events'][1]['id']='a'
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate_map(data)
        data=pdf_map();data['systems'][0]['events'][0]['x']=501
        with self.assertRaisesRegex(ValueError,'outside crop'):validate_map(data)

if __name__=='__main__':unittest.main()
