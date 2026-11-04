"""Shared numbered-notation arithmetic. No score recognition or singing validation."""
from fractions import Fraction
import re

LETTERS='CDEFGAB'
SEMITONES=(0,2,4,5,7,9,11)

def pitch(value):
    m=re.fullmatch(r'([A-G])(bb|##|b|#|n)?(-?\d+)',value)
    if not m:
        raise ValueError(f'Unsupported spelled pitch: {value}')
    letter,acc,octave=m.groups()
    alter={'':0,None:0,'n':0,'b':-1,'bb':-2,'#':1,'##':2}[acc]
    step=LETTERS.index(letter)
    return step,int(octave),alter

def degree(value,tonic,scale='major',octave_shift=0):
    """1 is the supplied tonic at its supplied octave; spelling preserves alterations."""
    step,octave,alter=pitch(value)
    base,base_oct,base_alter=pitch(tonic)
    offset=(octave+octave_shift-base_oct)*7+step-base
    register,number=divmod(offset,7)
    intervals={'major':(0,2,4,5,7,9,11),'minor':(0,2,3,5,7,8,10)}
    if scale not in intervals:
        raise ValueError('Scale must be major or minor (minor uses tonic=1)')
    actual=(octave+octave_shift-base_oct)*12+SEMITONES[step]+alter-SEMITONES[base]-base_alter
    accidental=actual-register*12-intervals[scale][number]
    if abs(accidental)>2:
        raise ValueError('Pitch spelling needs an unsupported numbered accidental')
    return {'number':number+1,'octave':register,'alter':accidental}

def rhythm(duration):
    """Quarter-note units; unsupported values must be encoded as explicit tied parts."""
    if isinstance(duration,(float,bool)):raise ValueError('Use integer or rational-string durations')
    d=Fraction(duration)
    for flags in range(5):
        base=Fraction(1,2**flags)
        if d==base or d==base*Fraction(3,2):
            return {'underlines':flags,'dot':d!=base,'dashes':0}
    if d.denominator==1 and d>=2:
        return {'underlines':0,'dot':False,'dashes':int(d)-1}
    raise ValueError(f'Unsupported numbered duration {d}; use tied standard values')

def svg_token(parent,x,y,pitches,duration,tonic,scale='major',octave_shift=0,right=None):
    import xml.etree.ElementTree as ET
    ns='{http://www.w3.org/2000/svg}'
    def node(tag,attrs,text=None):
        el=ET.SubElement(parent,ns+tag,{k:str(v) for k,v in attrs.items()})
        el.text=text
        return el
    def text(xx,yy,value,size=370):
        node('text',{'x':xx,'y':yy,'font-family':'Times New Roman,serif','font-size':size,'text-anchor':'middle'},str(value))
    def dot(xx,yy):node('circle',{'cx':xx,'cy':yy,'r':22,'fill':'black','stroke':'none'})
    shape=rhythm(duration)
    for lane,p in enumerate(pitches or [None]):
        yy=y+lane*600
        info=degree(p,tonic,scale,octave_shift) if p else {'number':0,'octave':0,'alter':0}
        text(x,yy,info['number'])
        if info['alter']:text(x-180,yy,{1:'♯',2:'𝄪',-1:'♭',-2:'𝄫'}[info['alter']],260)
        for i in range(abs(info['octave'])):dot(x,yy-470-i*110 if info['octave']>0 else yy+220+i*110)
        if shape['dot']:dot(x+155,yy-130)
        for i in range(shape['underlines']):
            node('path',{'d':f'M{x-110} {yy+65+i*65}h220','stroke':'black','stroke-width':14,'fill':'none'})
        for i in range(shape['dashes']):
            text(x+((right or x+800)-x)*(i+1)/(shape['dashes']+1),yy,'−')

def pdf_token(c,x,y,pitches,duration,tonic,scale='major',octave_shift=0,right=None):
    """Canvas coordinates, bottom origin; number font must already be selected."""
    shape=rhythm(duration)
    for lane,p in enumerate(pitches or [None]):
        yy=y-lane*17
        info=degree(p,tonic,scale,octave_shift) if p else {'number':0,'octave':0,'alter':0}
        c.drawCentredString(x,yy,str(info['number']))
        if info['alter']:
            # ASCII accidentals avoid assuming a music-symbol font in preserved PDFs.
            c.drawRightString(x-4,yy,{-2:'bb',-1:'b',1:'#',2:'##'}[info['alter']])
        for i in range(abs(info['octave'])):c.circle(x,yy+11+i*3 if info['octave']>0 else yy-7-i*3,.65,stroke=0,fill=1)
        if shape['dot']:c.circle(x+5,yy+3,.65,stroke=0,fill=1)
        for i in range(shape['underlines']):c.line(x-3.5,yy-2-i*2.3,x+3.5,yy-2-i*2.3)
        for i in range(shape['dashes']):c.drawCentredString(x+((right or x+25)-x)*(i+1)/(shape['dashes']+1),yy,'-')
