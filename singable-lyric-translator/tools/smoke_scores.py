"""Exercise both score routes with invented public material; not a musical acceptance trial."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skill/scripts'))
from engrave_score import render, print_pdf
from add_numbers import add_numbers

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output_dir',type=Path);ap.add_argument('--browser',type=Path)
    args=ap.parse_args();out=args.output_dir
    out.mkdir(parents=True,exist_ok=False)
    profile=json.loads((ROOT/'skill/references/score-profile.json').read_text(encoding='utf-8'))
    audit=render(ROOT/'skill/references/score-example.mei',out/'engraved',profile,True)
    assert audit['numbered_events']==12 and audit['source_unchanged']
    assert '晨' in (out/'engraved/score.html').read_text(encoding='utf-8')
    assert 'jianpu-tie' in (out/'engraved/page-01.svg').read_text(encoding='utf-8')
    if args.browser:print_pdf(out/'engraved',args.browser)
    handoff=render(ROOT/'tests/fixtures/handoff-example.mei',out/'handoff',profile,True)
    assert handoff['numbered_events']==16
    imported=render(ROOT/'tests/fixtures/score-import.musicxml',out/'imported',dict(profile,tonic='F4'),True)
    assert imported['numbered_events']==4
    assert [e['pitches'] for e in imported['events'].values()]==[['F4'],['G4'],['A4'],['Bb4']]
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader
    source=out/'preserve-source.pdf'
    c=canvas.Canvas(str(source),pagesize=(595,842))
    c.setTitle('Invented PDF-preserve test')
    for y in (710,704,698,692,686):c.line(45,y,550,y)
    c.line(84,680,96,680)
    for x,y in ((90,680),(190,683),(290,686),(390,689)):
        c.ellipse(x-4,y-2,x+4,y+2,fill=1);c.line(x+4,y,x+4,y+30)
    c.setFont('Times-Roman',12)
    for x,text in zip((90,190,290,390),('Day','light','guides','us')):c.drawCentredString(x,660,text)
    c.save()
    data={'schema_version':1,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
          'title':'Invented staff and numbered guide','tonic':'C4','scale':'major',
          'copyright':'Original public test material. Not singer-tested.',
          'systems':[{'page':1,'crop':[40,100,555,195],'barlines':[545],
                      'measure_durations':{'1':4},'events':[
                          {'id':f'e{i}','measure':'1','x':x,'pitches':[p],'onset':i,'duration':1}
                          for i,(x,p) in enumerate(zip((90,190,290,390),('C4','D4','E4','F4')))]}]}
    (out/'reviewed-map.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    result=add_numbers(source,out/'preserved.pdf',data)
    assert result['source_unchanged'] and result['numbered_events']==4
    assert 'guides' in PdfReader(out/'preserved.pdf').pages[0].extract_text()
    data['source_sha256']='0'*64
    try:add_numbers(source,out/'must-not-exist.pdf',data)
    except ValueError as exc:assert 'SHA-256' in str(exc)
    else:raise AssertionError('Wrong source hash was accepted')
    assert not (out/'must-not-exist.pdf').exists()
    print(json.dumps({'route_a':'rendered 12 events','route_b':'preserved strip + 4 events','wrong_source':'rejected','pdf_a':bool(args.browser),'performance_status':'not_performed'}))

if __name__=='__main__':main()
