"""Private source snapshots, mappings and scoped feedback. Standard library only."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
SCOPES = {'page', 'project', 'series', 'library'}
CONTEXTS = {'screen_review', 'native_powerpoint', 'live_projection', 'teaching_use', 'unspecified'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, data):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp')
    if temp.exists():
        raise ValueError(f'Unresolved temporary file: {temp}')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)

def contained(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Expected a project-relative path')
    resolved = (Path(root) / relative).resolve()
    if not resolved.is_relative_to(Path(root).resolve()):
        raise ValueError(f'Path escapes project: {relative}')
    return resolved

def explicit_bool(element):
    if element is None:
        return None
    return element.get('{' + NS['w'] + '}val', 'true').lower() not in {'0', 'false', 'off'}

def extract(path, source_id):
    path = Path(path)
    segments = []
    if path.suffix.lower() == '.docx':
        with ZipFile(path) as archive:
            root = ET.fromstring(archive.read('word/document.xml'))
            for idx, para in enumerate(root.findall('.//w:body//w:p', NS), 1):
                text = ''.join(x.text or '' for x in para.findall('.//w:t', NS))
                if not text.strip():
                    continue
                style = para.find('w:pPr/w:pStyle', NS)
                runs = []
                for run in para.findall('.//w:r', NS):
                    prop = run.find('w:rPr', NS)
                    color = prop.find('w:color', NS) if prop is not None else None
                    runs.append({'text': ''.join(x.text or '' for x in run.findall('w:t', NS)),
                                 'bold': explicit_bool(prop.find('w:b', NS)) if prop is not None else None,
                                 'italic': explicit_bool(prop.find('w:i', NS)) if prop is not None else None,
                                 'color': color.get('{' + NS['w'] + '}val') if color is not None else None,
                                 'properties_xml': ET.tostring(prop, encoding='unicode') if prop is not None else None})
                segments.append({'id': f'{source_id}-P{idx:04}', 'text': text,
                                 'paragraph_xml_sha256': hashlib.sha256(ET.tostring(para)).hexdigest(),
                                 'style': style.get('{' + NS['w'] + '}val') if style is not None else None, 'runs': runs})
    elif path.suffix.lower() == '.pptx':
        with ZipFile(path) as archive:
            pres = ET.fromstring(archive.read('ppt/presentation.xml'))
            rels = ET.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
            relmap = {x.get('Id'): x.get('Target') for x in rels}
            import posixpath
            for idx, entry in enumerate(pres.findall('p:sldIdLst/p:sldId', NS), 1):
                target = relmap[entry.get('{' + NS['r'] + '}id')]
                name = target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/' + target)
                root = ET.fromstring(archive.read(name))
                shapes = []
                for shape in root.findall('.//p:sp', NS):
                    info = shape.find('p:nvSpPr/p:cNvPr', NS)
                    xfrm = shape.find('p:spPr/a:xfrm', NS)
                    shapes.append({'id': info.get('id') if info is not None else None,
                                   'text': '\n'.join(''.join(x.text or '' for x in p.findall('.//a:t', NS)) for p in shape.findall('.//a:p', NS)),
                                   'geometry_xml': ET.tostring(xfrm, encoding='unicode') if xfrm is not None else None,
                                   'text_xml': ET.tostring(shape.find('p:txBody', NS), encoding='unicode') if shape.find('p:txBody', NS) is not None else None})
                notes_text = ''
                slide_rels = posixpath.dirname(name) + '/_rels/' + posixpath.basename(name) + '.rels'
                if slide_rels in archive.namelist():
                    for rel in ET.fromstring(archive.read(slide_rels)):
                        if (rel.get('Type') or '').endswith('/notesSlide') and rel.get('TargetMode') != 'External':
                            note_target = rel.get('Target', '')
                            note_name = note_target.lstrip('/') if note_target.startswith('/') else posixpath.normpath(posixpath.dirname(name) + '/' + note_target)
                            notes_root = ET.fromstring(archive.read(note_name))
                            note_shapes = notes_root.findall('.//p:sp', NS)
                            if note_shapes:
                                parts = []
                                for note_shape in note_shapes:
                                    ph = note_shape.find('p:nvSpPr/p:nvPr/p:ph', NS)
                                    if ph is not None and ph.get('type') in {'sldNum', 'dt', 'hdr', 'ftr'}:
                                        continue
                                    parts.extend(x.text or '' for x in note_shape.findall('.//a:t', NS))
                                notes_text = '\n'.join(parts)
                            else:
                                notes_text = '\n'.join(x.text or '' for x in notes_root.findall('.//a:t', NS))
                segments.append({'id': f'{source_id}-S{idx:03}', 'slide': idx,
                                 'text': '\n'.join(''.join(x.text or '' for x in p.findall('.//a:t', NS)) for p in root.findall('.//a:p', NS)), 'shapes': shapes,
                                 'notes_text': notes_text,
                                 'slide_xml_sha256': hashlib.sha256(ET.tostring(root)).hexdigest(),
                                 'picture_count': len(root.findall('.//p:pic', NS)),
                                 'table_count': len(root.findall('.//a:tbl', NS))})
    else:
        for idx, para in enumerate(re.split(r'\n\s*\n', path.read_text(encoding='utf-8-sig')), 1):
            if para.strip():
                segments.append({'id': f'{source_id}-P{idx:04}', 'text': para.strip()})
    return {'source_id': source_id, 'segments': segments, 'extraction': 'structure-and-explicit-properties; not visual or semantic verification'}

def init_project(directory, sources):
    root = Path(directory).resolve()
    if root.exists():
        raise ValueError(f'Project already exists: {root}')
    paths = [Path(p).resolve() for p in sources]
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in {'.docx', '.pptx', '.md', '.txt'}:
            raise ValueError(f'Unsupported or missing input: {path}')
    records = [(path, extract(path, f'S{idx:02}')) for idx, path in enumerate(paths, 1)]
    (root / 'source').mkdir(parents=True)
    (root / 'records').mkdir()
    inventory = []
    for idx, (path, extracted) in enumerate(records, 1):
        sid = f'S{idx:02}'
        dest = root / 'source' / (sid + path.suffix.lower())
        shutil.copy2(path, dest)
        record = root / 'records' / (sid + '.json')
        write(record, extracted)
        inventory.append({'id': sid, 'original_name': path.name, 'path': dest.relative_to(root).as_posix(),
                          'sha256': sha(dest), 'records': record.relative_to(root).as_posix(),
                          'records_sha256': sha(record), 'segments': len(extracted['segments'])})
    data = {'schema_version': 1, 'project_id': root.name, 'content_authority': None, 'content_policy': None,
            'sources': inventory, 'slide_map': [], 'omissions': [], 'decisions': [], 'feedback': [], 'reviews': []}
    write(root / 'project.json', data)
    return data

def check_project(directory):
    root = Path(directory).resolve()
    data = read(root / 'project.json')
    errors = []; segments = set(); used = set(); source_ids = set()
    for source in data['sources']:
        if source['id'] in source_ids:
            errors.append('Duplicate source ID: ' + source['id'])
        source_ids.add(source['id'])
        for key, hashkey in [('path', 'sha256'), ('records', 'records_sha256')]:
            try:
                path = contained(root, source[key])
                if not path.is_file() or sha(path) != source[hashkey]:
                    errors.append('Missing or changed: ' + source[key])
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
        try:
            records = read(contained(root, source['records']))
            for row in records['segments']:
                if row['id'] in segments:
                    errors.append('Duplicate segment ID: ' + row['id'])
                segments.add(row['id'])
        except (ValueError, KeyError, OSError) as exc:
            errors.append(str(exc))
    slide_ids = set()
    for row in data['slide_map']:
        if row['slide_id'] in slide_ids:
            errors.append('Duplicate mapped slide: ' + row['slide_id'])
        slide_ids.add(row['slide_id'])
        if row.get('treatment') not in {'verbatim', 'excerpt', 'summary', 'original'}:
            errors.append('Invalid treatment: ' + row['slide_id'])
        if not row.get('decision'):
            errors.append('Missing mapping rationale: ' + row['slide_id'])
        used.update(row.get('source_segments', []))
    for row in data['omissions']:
        if not row.get('reason'):
            errors.append('Omission needs reason')
        used.update(row.get('source_segments', []))
    if used - segments:
        errors.append('Unknown source segments: ' + ', '.join(sorted(used - segments)))
    for row in data.get('reference_extractions', []):
        if not row.get('pattern_id') or not row.get('source_segments') or set(row['source_segments']) - segments:
            errors.append('Invalid reference extraction mapping')
    decision_ids = set()
    for row in data['decisions']:
        if row['id'] in decision_ids:
            errors.append('Duplicate decision ID: ' + row['id'])
        decision_ids.add(row['id'])
        if row.get('scope') not in SCOPES or row.get('status') not in {'confirmed', 'proposed', 'superseded'}:
            errors.append('Invalid decision scope/status: ' + row['id'])
        if not all(row.get(k) for k in ['target', 'wording', 'basis']):
            errors.append('Incomplete decision: ' + row['id'])
    for row in data['decisions']:
        if any(ref not in decision_ids or ref == row['id'] for ref in row.get('supersedes', [])):
            errors.append('Invalid superseded decision link: ' + row['id'])
    return {'errors': errors, 'sources': len(data['sources']), 'segments': len(segments),
            'mapped_or_deliberately_omitted': len(used & segments), 'unmapped': len(segments - used),
            'pending_feedback': sum(r.get('status') == 'pending' for r in data['feedback']),
            'reference_extractions': len(data.get('reference_extractions', [])),
            'authority_resolved': data.get('content_authority') is not None,
            'coverage_is_semantic_verification': False}

def import_feedback(directory, batch):
    root = Path(directory).resolve()
    data = read(root / 'project.json')
    if batch.get('schema_version') != 1 or not isinstance(batch.get('observations'), list):
        raise ValueError('Invalid feedback batch')
    if batch.get('project_id') not in {None, '', data['project_id']}:
        raise ValueError('Feedback belongs to another project')
    existing = {r['id']: r for r in data['feedback']}
    new = []; skipped = 0
    for obs in batch['observations']:
        if not isinstance(obs, dict) or not all(isinstance(obs.get(k), str) and obs[k].strip() for k in ['id', 'pattern_id', 'target', 'reason', 'reporter', 'created_at']):
            raise ValueError('Feedback needs ID, pattern, target, reason, reporter and date')
        if obs.get('scope') not in SCOPES or obs.get('context') not in CONTEXTS or obs.get('action') not in {'keep', 'change', 'reject'}:
            raise ValueError('Invalid feedback scope, context or action')
        if any(key in obs for key in ['status', 'resolution_history', 'resolution']):
            raise ValueError('Feedback cannot declare approval/status')
        if 'delivery_blocking' in obs and not isinstance(obs['delivery_blocking'], bool):
            raise ValueError('delivery_blocking must be true or false')
        if obs.get('project_id') not in {None, '', data['project_id']}:
            skipped += 1
            continue
        obs = dict(obs)
        if obs.get('output_id'):
            from workflow import checked_output
            output = checked_output(root, data, obs['output_id'])
            if obs.get('artifact_sha256') and obs['artifact_sha256'] != output['sha256']:
                raise ValueError('Feedback output hash does not match its registered version')
            obs['artifact_sha256'] = output['sha256']
        record = dict(obs, status='pending')
        previous = existing.get(record['id'])
        if previous:
            comparable = {k: v for k, v in previous.items() if k not in {'status', 'resolution_history', 'resolution'}}
            if comparable != obs:
                raise ValueError('Conflicting feedback ID: ' + record['id'])
            continue
        existing[record['id']] = record
        new.append(record)
    data['feedback'].extend(new)
    write(root / 'project.json', data)
    return {'imported': len(new), 'skipped_other_projects': skipped,
            'status': 'pending; no decisions or patterns changed'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('init'); p.add_argument('directory'); p.add_argument('--source', action='append', required=True)
    p = sub.add_parser('check'); p.add_argument('directory'); p.add_argument('--for-delivery', action='store_true'); p.add_argument('--output')
    p = sub.add_parser('feedback'); p.add_argument('directory'); p.add_argument('--input', required=True)
    p = sub.add_parser('compare'); p.add_argument('old'); p.add_argument('new'); p.add_argument('--report', type=Path)
    p = sub.add_parser('revise'); p.add_argument('directory'); p.add_argument('--source', required=True); p.add_argument('--file', required=True)
    p = sub.add_parser('revision-decision'); p.add_argument('directory'); p.add_argument('--revision', required=True); p.add_argument('--outcome', choices=['adopt', 'keep-existing'], required=True); p.add_argument('--reason', required=True); p.add_argument('--basis', required=True)
    p = sub.add_parser('register-output'); p.add_argument('directory'); p.add_argument('--file', required=True); p.add_argument('--id'); p.add_argument('--source', action='append')
    p = sub.add_parser('resolve'); p.add_argument('directory'); p.add_argument('--feedback', required=True); p.add_argument('--outcome', choices=['applied', 'declined', 'deferred'], required=True); p.add_argument('--reason', required=True); p.add_argument('--basis', required=True); p.add_argument('--output'); p.add_argument('--scope', choices=sorted(SCOPES)); p.add_argument('--target')
    p = sub.add_parser('review'); p.add_argument('directory'); p.add_argument('--output', required=True); p.add_argument('--method', required=True); p.add_argument('--status', choices=['passed', 'issues', 'unverified'], required=True); p.add_argument('--coverage', choices=['full', 'partial'], required=True); p.add_argument('--basis', required=True); p.add_argument('--reviewer', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            data = init_project(args.directory, args.source)
            result = {'project': args.directory, 'sources': len(data['sources']), 'authority': 'unresolved'}
        elif args.command == 'check' and not args.for_delivery:
            result = check_project(args.directory)
        elif args.command == 'feedback':
            result = import_feedback(args.directory, read(args.input))
        else:
            import workflow as flow
            if args.command == 'check':
                if not args.output:
                    raise ValueError('Delivery check requires --output')
                result = flow.delivery_check(args.directory, args.output)
            elif args.command == 'compare':
                result = flow.compare(args.old, args.new)
                if args.report:
                    if args.report.exists():
                        raise ValueError('Comparison report already exists')
                    args.report.write_text(flow.markdown(result), encoding='utf-8')
            elif args.command == 'revise':
                result = flow.revise(args.directory, args.source, args.file)
            elif args.command == 'revision-decision':
                result = flow.decide_revision(args.directory, args.revision, args.outcome, args.reason, args.basis)
            elif args.command == 'register-output':
                result = flow.register_output(args.directory, args.file, args.id, args.source)
            elif args.command == 'resolve':
                result = flow.resolve_feedback(args.directory, args.feedback, args.outcome, args.reason, args.basis, args.output, args.scope, args.target)
            elif args.command == 'review':
                result = flow.record_review(args.directory, args.output, args.method, args.status, args.coverage, args.basis, args.reviewer)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('errors') or result.get('ready') is False else 0
    except (ValueError, OSError, KeyError, ET.ParseError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
