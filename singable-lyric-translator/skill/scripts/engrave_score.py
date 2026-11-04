#!/usr/bin/env python3
"""Render reviewed MEI/MusicXML to bilingual staff HTML/SVG and optional numbered guide/PDF."""
import argparse
import base64
from fractions import Fraction
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from notation import svg_token, rhythm, pitch, SEMITONES

M='{http://www.music-encoding.org/ns/mei}'
S='{http://www.w3.org/2000/svg}'
X='{http://www.w3.org/XML/1998/namespace}id'
ACC={'s':'#','f':'b','ss':'##','ff':'bb','n':''}

def xml_input(raw):
    if b'<!ENTITY' in raw:raise ValueError('XML entity declarations are unsupported')
    # Common MusicXML public DTD declarations are metadata, not needed for rendering.
    clean=re.sub(br'<!DOCTYPE\s+(?:score-partwise|score-timewise|mei)\s+[^>\[]*>',b'',raw)
    if b'<!DOCTYPE' in clean:raise ValueError('Internal/unknown XML document declarations are unsupported')
    return clean.decode('utf-8')

def mei_events(doc,staff='1',layer='1'):
    parents={c:p for p in doc.iter() for c in p}
    keys={};global_key='0';staff_context={}
    def key_accidentals(sig):
        if sig in ('0',''):return {}
        match=re.fullmatch(r'([1-7])([sf])',sig)
        if not match:raise ValueError('Unsupported key signature; encode explicit pitches')
        order='FCGDAEB' if match[2]=='s' else 'BEADGCF'
        return {letter:ACC[match[2]] for letter in order[:int(match[1])]}
    for node in doc.iter():
        if node.tag==M+'scoreDef' and node.get('keysig') is not None:global_key=node.get('keysig')
        if node.tag==M+'staffDef' and node.get('keysig') is not None:keys[node.get('n')]=node.get('keysig')
        if node.tag==M+'keySig':
            parent=parents.get(node)
            if parent is not None and parent.tag==M+'staffDef':keys[parent.get('n')]=node.get('sig','0')
            elif parent is not None and parent.tag==M+'scoreDef':global_key=node.get('sig','0')
            else:raise ValueError('Inline key changes need explicit section encoding before adding numbers')
        if node.tag==M+'staff':staff_context[node]=key_accidentals(keys.get(node.get('n'),global_key))
    events={}
    for st in doc.iter(M+'staff'):
        if st.get('n')!=staff:continue
        carried={}
        for la in st.findall(M+'layer'):
            if la.get('n')!=layer:continue
            for e in la.iter():
                tag=e.tag.removeprefix(M)
                if tag not in ('note','rest','chord') or parents.get(e).tag==M+'chord':continue
                eid=e.get(X)
                if not eid or eid in events:raise ValueError('Guide events need unique xml:id values')
                if not e.get('dur','').isdigit():raise ValueError(f'Explicit numeric duration required: {eid}')
                d=Fraction(4,int(e.get('dur')))
                dots=int(e.get('dots','0'))
                if dots>1:raise ValueError('Numbered guide supports one augmentation dot; encode tied parts')
                if dots:d*=Fraction(3,2)
                rhythm(str(d))
                actual=d
                p=parents.get(e)
                tuplet=None
                while p is not None and p is not la:
                    if p.tag==M+'tuplet':
                        actual*=Fraction(int(p.get('numbase','2')),int(p.get('num','3')))
                        tuplet=p.get('num','3')
                    p=parents.get(p)
                notes=[e] if tag=='note' else list(e.findall(M+'note'))
                ps=[]
                for note in notes:
                    letter=note.get('pname','').upper();octave=note.get('oct','')
                    written=note.get('accid')
                    accidental=note.find(M+'accid')
                    if accidental is not None:written=accidental.get('accid',written)
                    ges=note.get('accid.ges')
                    if accidental is not None:ges=accidental.get('accid.ges',ges)
                    if written is not None:
                        if written not in ACC:raise ValueError(f'Unsupported accidental {written}')
                        carried[(letter,octave)]=ACC[written]
                    if ges is not None:
                        if ges not in ACC:raise ValueError(f'Unsupported accidental {ges}')
                        alter=ACC[ges]
                    else:
                        if len(st.findall(M+'layer'))>1:raise ValueError('Multiple voices require explicit accid.ges pitches in the guide')
                        alter=carried.get((letter,octave),staff_context[st].get(letter,''))
                    ps.append(letter+alter+octave)
                def height(value):
                    step,octave,alter=pitch(value)
                    return octave*12+SEMITONES[step]+alter
                guide=[max(ps,key=height)] if ps else []
                events[eid]={'pitches':guide,'staff_pitches':ps,'duration':str(d),'actual_duration':str(actual),'tuplet':tuplet}
    if not events:raise ValueError('No supported events in selected guide staff/layer')
    return events

def numbered_pages(pages,events,ties,profile):
    positions={}
    for root in pages:
        for system in root.findall('.//'+S+'g[@class="system"]'):
            guides=system.findall('.//'+S+'g[@class="verse"][@data-n="1"]')
            baselines=[float(t.get('y')) for v in guides for t in v.findall('.//'+S+'text')]
            if not baselines:raise ValueError('No numbered baseline in a system; encode a guide note or use PDF-preserve route for all-rest systems')
            y=max(baselines)
            for parent in system.iter():
                for child in list(parent):
                    if child in guides:parent.remove(child)
            for measure in system.findall('./'+S+'g[@class="measure"]'):
                row=[]
                for g in measure.iter(S+'g'):
                    eid=g.get('id')
                    if eid not in events:continue
                    use=g.find('.//'+S+'g[@class="notehead"]/'+S+'use')
                    if use is None:use=g.find('.//'+S+'use')
                    if use is None:raise ValueError(f'Missing guide graphic: {eid}')
                    at=re.search(r'translate\(([-\d.]+),\s*([-\d.]+)\)',use.get('transform',''))
                    if not at:raise ValueError('Unsupported SVG note positioning')
                    row.append((eid,float(at[1])+90))
                ends=[]
                for p in measure.findall('.//'+S+'g[@class="barLine"]/'+S+'path'):
                    at=re.match(r'M\s*([-\d.]+)',p.get('d',''))
                    if at:ends.append(float(at[1]))
                for i,(eid,x) in enumerate(row):
                    right=row[i+1][1] if i+1<len(row) else max(ends) if ends else x+700
                    g=ET.SubElement(system,S+'g',{'class':'jianpu','data-event':eid})
                    e=events[eid]
                    svg_token(g,x,y,e['pitches'],e['duration'],profile['tonic'],profile.get('scale','major'),profile.get('octave_shift',0),right)
                    if e['tuplet']:
                        ET.SubElement(g,S+'text',{'x':str(x),'y':str(y-760),'font-size':'220','text-anchor':'middle'}).text=e['tuplet']
                    positions[eid]=(system,x,y)
                for x in set(ends):ET.SubElement(system,S+'path',{'d':f'M{x} {y-430}v600','stroke':'black','stroke-width':'12'})
    if set(positions)!=set(events):raise ValueError('Numbered guide does not cover every selected event exactly once')
    for a,b in ties:
        if a not in positions or b not in positions:continue
        sa,x1,y1=positions[a];sb,x2,y2=positions[b]
        if sa is sb:
            curves=[(sa,f'M{x1+20} {y1-560}Q{(x1+x2)/2} {y1-830} {x2-20} {y1-560}')]
        else:
            same_a=[v[1] for v in positions.values() if v[0] is sa]
            same_b=[v[1] for v in positions.values() if v[0] is sb]
            curves=[(sa,f'M{x1+20} {y1-560}q250 -250 {max(same_a)-x1+200} -80'),
                    (sb,f'M{min(same_b)-200} {y2-640}Q{x2-200} {y2-830} {x2-20} {y2-560}')]
        for parent,d in curves:ET.SubElement(parent,S+'path',{'class':'jianpu-tie','d':d,'stroke':'black','stroke-width':'14','fill':'none'})

def render(source,destination,profile,numbered=False):
    try:import verovio
    except ImportError as exc:raise ValueError('Missing optional dependency: pip install verovio (tested 6.3.0)') from exc
    raw=source.read_bytes()
    kit=verovio.toolkit()
    kit.setOptions({'xmlIdSeed':180,'breaks':profile.get('breaks','auto')})
    if not kit.loadData(xml_input(raw)):raise ValueError(kit.getLog())
    doc=ET.fromstring(kit.getMEI())
    events={};ties=[]
    if numbered:
        if 'tonic' not in profile:raise ValueError('Numbered guide requires tonic with reference octave, e.g. Bb3')
        events=mei_events(doc,str(profile.get('staff',1)),str(profile.get('layer',1)))
        ties=[(e.get('startid','').lstrip('#'),e.get('endid','').lstrip('#')) for e in doc.iter(M+'tie')]
        for e in doc.iter(M+'verse'):e.set('n',str(int(e.get('n','1'))+1))
        for e in doc.iter():
            if e.get(X) in events and events[e.get(X)]['pitches']:
                ET.SubElement(ET.SubElement(e,M+'verse',{'n':'1'}),M+'syl').text='1'
    ET.register_namespace('',M[1:-1])
    encoded=ET.tostring(doc,encoding='unicode')
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'layout.mei').write_text(encoded,encoding='utf-8')
    kit.setOptions({'pageWidth':1900,'pageHeight':2400,'scale':40,'header':'none','footer':'none',
                    'shrinkToFit':True,
                    'breaks':profile.get('breaks','auto'),'svgViewBox':True,'lyricSize':4.6,
                    'lyricHeightFactor':1.8 if numbered else 1.25,'lyricTopMinMargin':8,'lyricWordSpace':1.8,
                    'spacingSystem':12,'systemMaxPerPage':5,'svgAdditionalAttribute':['verse@n'],
                    'svgCss':'.verse text{font-family:LyricCJK,"Noto Serif SC",SimSun,serif;} .verse[data-n="'+('3' if numbered else '2')+'"] text{font-family:"Times New Roman",serif;}'})
    if not kit.loadData(encoded):raise ValueError(kit.getLog())
    pages=[ET.fromstring(kit.renderToSVG(i)) for i in range(1,kit.getPageCount()+1)]
    if numbered:numbered_pages(pages,events,ties,profile)
    ET.register_namespace('',S[1:-1])
    ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
    # HTML's inline SVG parser recognises href/xlink:href, not arbitrary ns1:href.
    for root in pages:
        for use in root.iter(S+'use'):
            ref=use.get('{http://www.w3.org/1999/xlink}href')
            if ref:use.set('href',ref)
    svgs=[ET.tostring(p,encoding='unicode') for p in pages]
    for i,svg in enumerate(svgs,1):(destination/f'page-{i:02}.svg').write_text(svg,encoding='utf-8')
    font_css=''
    if profile.get('font_file'):
        font=Path(profile['font_file'])
        font_css='@font-face{font-family:LyricCJK;src:url(data:font/ttf;base64,'+base64.b64encode(font.read_bytes()).decode()+')}'
    style='''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;color:#111;font-family:LyricCJK,"Noto Serif SC",SimSun,serif}.page{width:210mm;height:297mm;position:relative;break-after:page}.page:last-child{break-after:auto}.head{position:absolute;left:13mm;right:13mm;top:7mm}h1{font-size:18pt;margin:0}.credits{font-size:8pt}.subtitle{font-size:10pt;margin-top:2mm}.score{position:absolute;left:10mm;top:34mm;width:190mm;height:240mm}.score svg{width:190mm;height:240mm}.foot{position:absolute;left:13mm;right:13mm;bottom:7mm;font-size:7pt}'''
    content=['<!doctype html><html><head><meta charset="utf-8"><title>'+escape(profile.get('title',source.stem))+'</title><style>'+font_css+style+'</style></head><body>']
    for i,svg in enumerate(svgs,1):
        content.append('<section class="page"><div class="head"><h1>'+escape(profile.get('title',source.stem))+'</h1><div class="credits">'+escape(profile.get('credits',''))+'</div><div class="subtitle">'+escape(profile.get('subtitle','五线谱／简谱／中文／英文' if numbered else '中文／英文双语五线谱'))+'</div></div><div class="score">'+svg+'</div><div class="foot">'+escape(profile.get('copyright',''))+'<br>未经真人试唱验证 · '+str(i)+' / '+str(len(svgs))+'</div></section>')
    content.append('</body></html>')
    (destination/'score.html').write_text('\n'.join(content),encoding='utf-8')
    audit={'engine':kit.getVersion(),'pages':len(pages),'source_sha256':hashlib.sha256(raw).hexdigest(),
           'source_unchanged':raw==source.read_bytes(),'numbered_events':len(events),'guide':profile if numbered else None,
           'events':events,'score_identity':'requires comparison with reviewed source','performance_status':'not_performed'}
    (destination/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    (destination/'engraver.log').write_text(kit.getLog(),encoding='utf-8')
    return audit

def print_pdf(folder,browser):
    target=(folder/'score.pdf').resolve()
    if target.exists():raise ValueError('PDF exists; render a new version/folder')
    profile=folder.resolve()/('browser-'+uuid.uuid4().hex)
    profile.mkdir()
    try:
        result=subprocess.run([str(browser),'--headless','--disable-gpu','--no-first-run','--no-pdf-header-footer',
                        '--user-data-dir='+str(profile),'--print-to-pdf='+str(target),(folder/'score.html').resolve().as_uri()],timeout=60,capture_output=True)
        if result.returncode:raise ValueError('Browser print failed: '+result.stderr.decode('utf-8',errors='replace')[-2000:])
        def ready():
            if not target.is_file():return False
            try:
                with target.open('rb') as f:
                    f.seek(max(0,target.stat().st_size-100));return b'%%EOF' in f.read()
            except OSError:return False
        deadline=time.monotonic()+20
        while not ready() and time.monotonic()<deadline:time.sleep(.2)
        if not ready():raise ValueError('Browser did not finish score.pdf; HTML/SVG remain available')
    finally:
        if profile.resolve().parent==folder.resolve():shutil.rmtree(profile,ignore_errors=True)
    if not target.is_file():raise ValueError('Browser did not produce score.pdf; HTML/SVG remain available')
    return target

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path);ap.add_argument('output_dir',type=Path)
    ap.add_argument('--profile',type=Path,required=True);ap.add_argument('--numbered',action='store_true')
    ap.add_argument('--browser',type=Path,help='Chrome/Edge/Chromium executable; also produces PDF')
    args=ap.parse_args()
    try:
        profile=json.loads(args.profile.read_text(encoding='utf-8'))
        if profile.get('font_file'):profile['font_file']=str((args.profile.parent/profile['font_file']).resolve())
        audit=render(args.source,args.output_dir,profile,args.numbered)
        if args.browser:print_pdf(args.output_dir,args.browser)
        print(json.dumps({k:audit[k] for k in ('pages','numbered_events','source_unchanged','performance_status')}))
    except (ValueError,OSError,ET.ParseError,subprocess.SubprocessError) as exc:
        ap.exit(1,str(exc)+'\n')

if __name__=='__main__':main()
