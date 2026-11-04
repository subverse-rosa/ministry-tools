"""Validate/search the reference catalog and generate its offline HTML gallery."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'library'

def load(root=ROOT):
    return json.loads((Path(root) / 'catalog.json').read_text(encoding='utf-8-sig'))

def local_file(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Expected a library-relative preview')
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('Preview escapes library')
    if path.suffix.lower() != '.png' or not path.is_file():
        raise ValueError('Missing PNG preview: ' + relative)
    return path

def check(root=ROOT):
    root = Path(root)
    data = load(root)
    errors = []; ids = set(); source_ids = {s['id'] for s in data['sources']}
    relations = set(data['relationships'])
    if data.get('schema_version') != 1:
        errors.append('Unsupported catalog schema')
    for row in data['patterns']:
        pid = row.get('id', '')
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', pid) or pid in ids:
            errors.append('Invalid/duplicate pattern ID: ' + pid)
        ids.add(pid)
        if row.get('status') not in {'reference', 'tried', 'reusable', 'retired'}:
            errors.append('Invalid lifecycle: ' + pid)
        if not row.get('relationships') or set(row['relationships']) - relations:
            errors.append('Invalid relationship: ' + pid)
        for field in ['title', 'intent', 'spatial_form', 'adaptations', 'caveats']:
            if not row.get(field):
                errors.append(f'Missing {field}: {pid}')
        evidence = row.get('evidence', [])
        if row.get('status') in {'tried', 'reusable'} and not any(e.get('kind') == 'adapted_artifact' and e.get('artifact_sha256') for e in evidence):
            errors.append('Lifecycle lacks adapted artifact: ' + pid)
        if row.get('status') == 'reusable' and not row.get('promotion_basis'):
            errors.append('Reusable entry needs promotion basis: ' + pid)
        example_ids = set()
        for example in row.get('examples', []):
            example_id = example.get('id') or f"{example.get('source_id')}:{example.get('slide')}"
            if example_id in example_ids:
                errors.append('Duplicate example: ' + pid)
            example_ids.add(example_id)
            if example.get('source_id') not in source_ids or not isinstance(example.get('slide'), int) or example['slide'] < 1:
                errors.append('Invalid provenance: ' + pid)
            try:
                path = local_file(root, example['preview'])
                if hashlib.sha256(path.read_bytes()).hexdigest() != example['sha256']:
                    errors.append('Preview hash mismatch: ' + pid)
            except (KeyError, ValueError) as exc:
                errors.append(str(exc))
        if not row.get('examples'):
            errors.append('Reference needs an actual example: ' + pid)
    return {'errors': errors, 'patterns': len(data['patterns']),
            'example_count': sum(len(p['examples']) for p in data['patterns']),
            'unrepresented_relationships': sorted(relations - {r for p in data['patterns'] for r in p['relationships']})}

def script_json(value):
    # Prevent source strings from ending the non-executing JSON script element.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

def build(root=ROOT):
    root = Path(root)
    result = check(root)
    if result['errors']:
        raise ValueError('; '.join(result['errors']))
    data = load(root)
    images = {}
    for row in data['patterns']:
        for example in row['examples']:
            name = example['preview']
            images[name] = 'data:image/png;base64,' + base64.b64encode(local_file(root, name).read_bytes()).decode('ascii')
    shell = (root / 'gallery-shell.html').read_text(encoding='utf-8')
    slots = {'__CATALOG_JSON__': script_json(data), '__PREVIEWS_JSON__': script_json(images),
             '__GALLERY_SCRIPT__': (root / 'gallery.js').read_text(encoding='utf-8')}
    if any(shell.count(slot) != 1 for slot in slots):
        raise ValueError('Gallery shell needs one catalog, preview and script slot')
    html = re.sub('|'.join(re.escape(slot) for slot in slots), lambda m: slots[m.group()], shell)
    (root / 'index.html').write_text(html, encoding='utf-8', newline='\n')
    return dict(result, output=str(root / 'index.html'))

def find(query, root=ROOT):
    terms = query.casefold().split()
    result = []
    for row in load(root)['patterns']:
        haystack = json.dumps(row, ensure_ascii=False).casefold()
        if all(t in haystack for t in terms):
            result.append({k: row[k] for k in ['id', 'title', 'relationships', 'status']})
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'build', 'find'])
    parser.add_argument('query', nargs='?', default='')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = build(args.root) if args.command == 'build' else find(args.query, args.root) if args.command == 'find' else check(args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(isinstance(result, dict) and bool(result.get('errors')))
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
