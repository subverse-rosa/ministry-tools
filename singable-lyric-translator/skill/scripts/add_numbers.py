#!/usr/bin/env python3
"""Preserve reviewed PDF system strips and append numbered notation from an explicit map."""
import argparse
from copy import copy
from fractions import Fraction
import hashlib
from io import BytesIO
import json
from pathlib import Path
from notation import degree, rhythm, pdf_token

def validate_map(data):
    if data.get('schema_version')!=1:raise ValueError('Map schema_version must be 1')
    degree(data['tonic'],data['tonic'],data.get('scale','major'))
    ids=set();event_index={}
    for system in data['systems']:
        x0,top,x1,bottom=system['crop']
        if not (0<=x0<x1 and 0<=top<bottom):raise ValueError('Invalid top-origin crop rectangle')
        if system.get('band_height',55)<0:raise ValueError('Negative number band height')
        groups={}
        for e in system.get('events',[]):
            if e['id'] in ids:raise ValueError('Duplicate event ID')
            ids.add(e['id'])
            event_index[e['id']]=e
            if not x0<=e['x']<x1:raise ValueError('Numbered event outside crop')
            lane=e.get('lane',0)
            if not isinstance(lane,int) or lane<0:raise ValueError('Invalid lane')
            for p in e['pitches']:degree(p,data['tonic'],data.get('scale','major'),data.get('octave_shift',0))
            rhythm(e.get('display_duration',e['duration']))
            if any(isinstance(e[k],(float,bool)) for k in ('onset','duration')):raise ValueError('Use exact rational-string times')
            start=Fraction(e['onset']);end=start+Fraction(e['duration'])
            if start<0 or end<=start:raise ValueError('Invalid event time')
            groups.setdefault((e['measure'],lane),[]).append((start,end))
        for (measure,lane),spans in groups.items():
            at=Fraction(0)
            for a,b in sorted(spans):
                if a!=at:raise ValueError('Gap/overlap in a voice; encode rests explicitly')
                at=b
            if at!=Fraction(system['measure_durations'][measure]):raise ValueError('Measure duration mismatch')
    for tie in data.get('ties',[]):
        if len(tie)!=2 or not set(tie)<=ids:raise ValueError('Tie references missing events')
        if not event_index[tie[0]]['pitches'] or event_index[tie[0]]['pitches']!=event_index[tie[1]]['pitches']:
            raise ValueError('Tie endpoints must have equal nonempty pitches')
    return True

def add_numbers(source,output,data):
    try:
        from pypdf import PdfReader,PdfWriter,Transformation
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as exc:raise ValueError('PDF-preserve route needs optional reportlab and pypdf') from exc
    validate_map(data)
    raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if digest!=data['source_sha256']:raise ValueError('Source PDF SHA-256 differs from reviewed map')
    if output.resolve()==source.resolve():raise ValueError('Output must differ from source PDF')
    if output.exists():raise ValueError('Output exists; choose a new version/path')
    reader=PdfReader(BytesIO(raw))
    font='Helvetica'
    if data.get('font_file'):
        font='LyricCJK';pdfmetrics.registerFont(TTFont(font,data['font_file'],subfontIndex=0))
    elif any(ord(c)>127 for c in data.get('title','')+data.get('copyright','')):
        raise ValueError('A CJK font_file is required for non-ASCII title/copyright')
    width,height=595.276,841.89
    margin=38;cursor=65;page_no=0;blocks=[];positions={}
    for system in data['systems']:
        page=reader.pages[system['page']-1]
        if page.rotation or float(page.mediabox.left)!=0 or float(page.mediabox.bottom)!=0:
            raise ValueError('Normalize rotated/offset source pages before mapping coordinates')
        x0,top,x1,bottom=system['crop']
        if x1>float(page.mediabox.width) or bottom>float(page.mediabox.height):raise ValueError('Crop exceeds source page')
        scale=(width-2*margin)/(x1-x0)
        band=system.get('band_height',55)
        block_height=(bottom-top)*scale+band
        if block_height>height-125:raise ValueError('System is too tall for an A4 page')
        if cursor+block_height>height-55:page_no+=1;cursor=65
        block={'system':system,'page':page_no,'top':cursor,'scale':scale,'music_height':(bottom-top)*scale}
        blocks.append(block)
        for e in system.get('events',[]):
            y=height-cursor-block['music_height']-20-e.get('lane',0)*24
            if 20+e.get('lane',0)*24+max(0,len(e['pitches'])-1)*17+14>band:raise ValueError('Numbered band too short for lanes/chords/octave dots')
            positions[e['id']]=(page_no,margin+(e['x']-x0)*scale,y,block)
        cursor+=block_height+12
    buf=BytesIO();c=canvas.Canvas(buf,pagesize=(width,height))
    for p in range(page_no+1):
        c.setFont(font,14);c.drawString(margin,height-33,data.get('title','Staff and numbered notation'))
        c.setFont('Helvetica',8);c.drawString(margin,height-48,'1 = '+data['tonic']+' | '+data.get('register_label','written pitch')+' | Not singer-tested')
        for block in (b for b in blocks if b['page']==p):
            system=block['system'];scale=block['scale'];x0,_,x1,_=system['crop']
            by_lane={}
            for e in system.get('events',[]):by_lane.setdefault(e.get('lane',0),[]).append(e)
            c.setFont('Times-Roman',12);c.setLineWidth(.4)
            for lane,events in by_lane.items():
                events.sort(key=lambda e:e['x'])
                for i,e in enumerate(events):
                    _,x,y,_=positions[e['id']]
                    right=positions[events[i+1]['id']][1] if i+1<len(events) else width-margin
                    pdf_token(c,x,y,e['pitches'],e.get('display_duration',e['duration']),data['tonic'],data.get('scale','major'),data.get('octave_shift',0),right)
                    if e.get('tuplet'):
                        c.setFont('Times-Roman',7);c.drawCentredString(x,y+20,str(e['tuplet']));c.setFont('Times-Roman',12)
            base=height-block['top']-block['music_height']-20
            for xx in system.get('barlines',[]):
                x=margin+(xx-x0)*scale;c.line(x,base+12,x,base-system.get('band_height',55)+25)
        for a,b in data.get('ties',[]):
            pa,x1,y1,ba=positions[a];pb,x2,y2,bb=positions[b]
            if pa==pb==p and ba is bb:
                path=c.beginPath();path.moveTo(x1+1,y1+15);path.curveTo(x1+(x2-x1)/3,y1+24,x1+2*(x2-x1)/3,y1+24,x2-1,y2+15);c.drawPath(path)
            else:
                for pp,xx,yy,ending in ((pa,x1,y1,True),(pb,x2,y2,False)):
                    if pp==p:
                        edge=width-margin if ending else margin
                        path=c.beginPath();path.moveTo(xx,yy+15);path.curveTo((xx+edge)/2,yy+24,(xx+edge)/2,yy+24,edge,yy+18);c.drawPath(path)
        c.setFont(font,7);c.drawString(margin,28,data.get('copyright',''))
        c.setFont('Helvetica',7);c.drawRightString(width-margin,17,f'{p+1} / {page_no+1}')
        c.showPage()
    c.save();buf.seek(0)
    overlay=PdfReader(buf);writer=PdfWriter()
    for i,target in enumerate(overlay.pages):
        for block in (b for b in blocks if b['page']==i):
            system=block['system'];part=copy(reader.pages[system['page']-1])
            x0,top,x1,bottom=system['crop'];source_height=float(part.mediabox.height)
            part.cropbox.lower_left=(x0,source_height-bottom);part.cropbox.upper_right=(x1,source_height-top)
            s=block['scale']
            transform=Transformation().scale(s).translate(margin-x0*s,height-block['top']-(source_height-top)*s)
            target.merge_transformed_page(part,transform,over=False,expand=False)
        writer.add_page(target)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as f:writer.write(f)
    audit={'pages':len(writer.pages),'source_sha256':digest,'source_unchanged':raw==source.read_bytes(),
           'systems':len(blocks),'numbered_events':len(positions),'staff_and_lyrics':'original PDF strips',
           'map_review':'provided by caller; not independent transcription verification','performance_status':'not_performed'}
    output.with_suffix('.audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    return audit

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path);ap.add_argument('map',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args()
    try:
        data=json.loads(args.map.read_text(encoding='utf-8'))
        if data.get('font_file'):data['font_file']=str((args.map.parent/data['font_file']).resolve())
        print(json.dumps(add_numbers(args.source,args.output,data)))
    except (ValueError,OSError,KeyError,IndexError) as exc:ap.exit(1,str(exc)+'\n')

if __name__=='__main__':main()
