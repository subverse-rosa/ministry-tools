"""Version-bound revision, feedback and delivery operations. Standard library only."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile
import project as core

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def next_id(rows, prefix):
    ids = {r['id'] for r in rows}
    number = 1
    while f'{prefix}{number:04}' in ids:
        number += 1
    return f'{prefix}{number:04}'

def require_text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + ' is required')
    return value.strip()

def item(rows, identity):
    matches = [r for r in rows if r['id'] == identity]
    if len(matches) != 1:
        raise ValueError('Missing or duplicate ID: ' + identity)
    return matches[0]

def normalized(text):
    return ' '.join(text.split())

def package_context(path):
    if Path(path).suffix.lower() not in {'.docx', '.pptx'}:
        return {}
    with ZipFile(path) as archive:
        prefixes = ('word/styles', 'word/numbering', 'word/media/', 'word/footnotes', 'word/endnotes',
                    'word/header', 'word/footer', 'ppt/theme/', 'ppt/slideMasters/', 'ppt/slideLayouts/', 'ppt/media/', 'ppt/charts/', 'ppt/embeddings/', 'ppt/fonts/')
        return {name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
                if name.startswith(prefixes) and not name.endswith('/')}

def compare(old_path, new_path):
    old_path, new_path = Path(old_path), Path(new_path)
    if old_path.suffix.lower() != new_path.suffix.lower() or old_path.suffix.lower() not in {'.txt', '.md', '.docx', '.pptx'}:
        raise ValueError('Compare two supported files of the same type')
    before = core.extract(old_path, 'OLD')['segments']
    after = core.extract(new_path, 'NEW')['segments']
    left = [normalized(r['text']) for r in before]
    right = [normalized(r['text']) for r in after]
    changes = []; removed = []; added = []
    def row(kind, old=None, new=None, **extra):
        return dict(kind=kind, old_segment=old['id'] if old else None,
                    new_segment=new['id'] if new else None,
                    old_text=old['text'] if old else None, new_text=new['text'] if new else None, **extra)
    def notes(a, b):
        if a.get('notes_text', '') != b.get('notes_text', ''):
            changes.append(dict(row('notes_modified', a, b), old_text=a.get('notes_text', ''), new_text=b.get('notes_text', '')))
    for tag, i, j, k, m in SequenceMatcher(None, left, right, autojunk=False).get_opcodes():
        if tag == 'equal':
            for a, b in zip(before[i:j], after[k:m]):
                old_form = {key: value for key, value in a.items() if key not in {'id', 'slide', 'notes_text'}}
                new_form = {key: value for key, value in b.items() if key not in {'id', 'slide', 'notes_text'}}
                if old_form != new_form:
                    changes.append(row('structure_or_format', a, b))
                notes(a, b)
        elif tag == 'replace' and j-i == m-k:
            for a, b in zip(before[i:j], after[k:m]):
                changes.append(row('modified', a, b, matching='positional candidate; review before transferring decisions'))
                notes(a, b)
        else:
            removed.extend(before[i:j]); added.extend(after[k:m])
    # Only pair unique exact text among unmatched rows. Repeated text remains ambiguous.
    old_counts = Counter(normalized(r['text']) for r in removed)
    new_counts = Counter(normalized(r['text']) for r in added)
    moved = {key for key in old_counts if key and old_counts[key] == new_counts[key] == 1}
    for a in removed:
        key = normalized(a['text'])
        if key in moved:
            b = next(r for r in added if normalized(r['text']) == key)
            changes.append(row('moved', a, b, matching='unique text match; appearance still requires review'))
            notes(a, b)
        else:
            changes.append(row('removed', a))
    for b in added:
        if normalized(b['text']) not in moved:
            changes.append(row('added', new=b))
    old_context, new_context = package_context(old_path), package_context(new_path)
    context_changes = [name for name in sorted(old_context.keys() | new_context.keys()) if old_context.get(name) != new_context.get(name)]
    return {'schema_version': 1, 'old': {'name': old_path.name, 'sha256': core.sha(old_path)},
            'new': {'name': new_path.name, 'sha256': core.sha(new_path)},
            'summary': dict(Counter(r['kind'] for r in changes)), 'changes': changes,
            'style_or_asset_parts_changed': context_changes,
            'limits': 'Text/structure comparison, not rendered appearance or semantic equivalence. Matches never rewrite mappings or confirmed decisions.'}

def markdown(report):
    lines = ['# 修订比对', '', f"原稿：{report['old']['name']}", f"新版：{report['new']['name']}", '',
             '## 变化概览', '', json.dumps(report['summary'], ensure_ascii=False), '', report['limits'], '']
    names = {'modified': '文字修改（位置匹配候选）', 'added': '新增', 'removed': '移除',
             'moved': '位置变化', 'structure_or_format': '结构或格式变化', 'notes_modified': '讲员备注修改'}
    for r in report['changes']:
        lines += [f"## {names[r['kind']]}：{r['old_segment'] or '—'} / {r['new_segment'] or '—'}", '']
        for label, key in [('原稿', 'old_text'), ('新版', 'new_text')]:
            if r[key] is not None:
                lines += [label + '：', '', '> ' + r[key].replace('\n', '\n> '), '']
    if report['style_or_asset_parts_changed']:
        lines += ['## 样式、图像或其他上下文部件', ''] + ['- ' + p for p in report['style_or_asset_parts_changed']]
    return '\n'.join(lines) + '\n'

def load_project(directory):
    root = Path(directory).resolve()
    result = core.check_project(root)
    if result['errors']:
        raise ValueError('Project record errors: ' + '; '.join(result['errors']))
    return root, core.read(root / 'project.json')

def decision(data, scope, target, wording, basis, supersedes=()):
    require_text(basis, 'Decision basis'); require_text(wording, 'Decision wording')
    if scope not in core.SCOPES:
        raise ValueError('Invalid decision scope')
    rows = data.setdefault('decisions', [])
    for identity in supersedes:
        item(rows, identity)['status'] = 'superseded'
    record = {'id': next_id(rows, 'D'), 'scope': scope, 'target': target, 'status': 'confirmed',
              'wording': wording, 'basis': basis, 'supersedes': list(supersedes), 'created_at': now()}
    rows.append(record)
    return record['id']

def revise(directory, source_id, new_file):
    root, data = load_project(directory)
    old = item(data['sources'], source_id)
    path = Path(new_file).resolve()
    report = compare(core.contained(root, old['path']), path)
    sid = next_id(data['sources'], 'S')
    rid = next_id(data.get('source_revisions', []), 'V')
    dest = core.contained(root, 'source/' + sid + path.suffix.lower())
    record = core.contained(root, 'records/' + sid + '.json')
    report_path = core.contained(root, 'records/' + rid + '.json')
    if any(p.exists() for p in [dest, record, report_path, report_path.with_suffix('.md')]):
        raise ValueError('Revision destination already exists')
    extracted = core.extract(path, sid)
    shutil.copy2(path, dest); core.write(record, extracted); core.write(report_path, report)
    report_path.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
    data['sources'].append({'id': sid, 'original_name': path.name, 'path': dest.relative_to(root).as_posix(),
                            'sha256': core.sha(dest), 'records': record.relative_to(root).as_posix(),
                            'records_sha256': core.sha(record), 'segments': len(extracted['segments']), 'revises': source_id})
    data.setdefault('source_revisions', []).append({'id': rid, 'old_source': source_id, 'new_source': sid,
                                                   'report': report_path.relative_to(root).as_posix(),
                                                   'report_sha256': core.sha(report_path), 'status': 'pending', 'created_at': now()})
    core.write(root / 'project.json', data)
    return {'revision': rid, 'new_source': sid, 'summary': report['summary'], 'report': str(report_path.with_suffix('.md')),
            'status': 'pending; mappings, authority and confirmed wording retained'}

def decide_revision(directory, revision_id, outcome, reason, basis):
    root, data = load_project(directory)
    revision = item(data.get('source_revisions', []), revision_id)
    if revision['status'] != 'pending' or outcome not in {'adopt', 'keep-existing'}:
        raise ValueError('Resolve a pending revision with adopt or keep-existing')
    require_text(reason, 'Revision reason')
    did = decision(data, 'project', revision_id, outcome + ': ' + reason, basis)
    revision.update(status=outcome, decision_id=did, resolved_at=now())
    authority = data.get('content_authority')
    if outcome == 'adopt' and isinstance(authority, dict):
        authority['source_ids'] = [revision['new_source'] if s == revision['old_source'] else s for s in authority.get('source_ids', [])]
    core.write(root / 'project.json', data)
    return {'revision': revision_id, 'outcome': outcome, 'decision': did,
            'mapping_action': 'Review mappings explicitly; no segment IDs or approved wording were transferred.'}

def content_snapshot(data):
    return {k: data.get(k) for k in ['content_authority', 'content_policy', 'content_policy_basis', 'slide_map', 'omissions']}

def snapshot_hash(snapshot):
    return hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

def register_output(directory, file, output_id=None, source_ids=None):
    root, data = load_project(directory)
    file = Path(file).resolve()
    if file.suffix.lower() != '.pptx' or not file.is_file():
        raise ValueError('Register an existing PPTX output')
    parsed = core.extract(file, 'OUTPUT')
    if not parsed['segments']:
        raise ValueError('Output has no slides')
    rows = data.setdefault('outputs', [])
    identity = output_id or next_id(rows, 'O')
    if not identity.isalnum() or any(r['id'] == identity for r in rows):
        raise ValueError('Output ID must be unique and alphanumeric')
    if not source_ids:
        authority = data.get('content_authority')
        source_ids = authority.get('source_ids', []) if isinstance(authority, dict) else []
    sources = [item(data['sources'], sid) for sid in source_ids]
    dest = core.contained(root, 'outputs/' + identity + '.pptx')
    snap_path = core.contained(root, 'outputs/' + identity + '.mapping.json')
    if dest.exists() or snap_path.exists():
        raise ValueError('Output snapshot destination exists')
    dest.parent.mkdir(exist_ok=True)
    shutil.copy2(file, dest)
    snapshot = content_snapshot(data); core.write(snap_path, snapshot)
    record = {'id': identity, 'original_name': file.name, 'path': dest.relative_to(root).as_posix(),
              'sha256': core.sha(dest), 'source_snapshot': [{'id': s['id'], 'sha256': s['sha256']} for s in sources],
              'mapping_path': snap_path.relative_to(root).as_posix(), 'mapping_sha256': core.sha(snap_path),
              'content_snapshot_sha256': snapshot_hash(snapshot), 'slide_count': len(parsed['segments']),
              'slide_ids': [r['slide_id'] for r in data['slide_map']], 'created_at': now()}
    rows.append(record); core.write(root / 'project.json', data)
    return {'output': identity, 'sha256': record['sha256'], 'slide_count': record['slide_count'],
            'status': 'registered snapshot; not a delivery pass'}

def checked_output(root, data, identity):
    output = item(data.get('outputs', []), identity)
    path = core.contained(root, output['path'])
    if not path.is_file() or core.sha(path) != output['sha256']:
        raise ValueError('Output snapshot is missing or changed: ' + identity)
    mapping = core.contained(root, output['mapping_path'])
    if not mapping.is_file() or core.sha(mapping) != output['mapping_sha256']:
        raise ValueError('Output mapping snapshot is missing or changed: ' + identity)
    return output

def resolve_feedback(directory, feedback_id, outcome, reason, basis, output_id=None, scope=None, target=None):
    root, data = load_project(directory)
    feedback = item(data['feedback'], feedback_id)
    if outcome not in {'applied', 'declined', 'deferred'}:
        raise ValueError('Choose applied, declined or deferred')
    require_text(reason, 'Resolution reason')
    output = checked_output(root, data, output_id) if output_id else None
    if outcome == 'applied' and output is None:
        raise ValueError('Applied feedback requires a registered output snapshot')
    history = feedback.setdefault('resolution_history', [])
    previous = [history[-1]['decision_id']] if history else []
    did = decision(data, scope or feedback['scope'], target or feedback['target'], outcome + ': ' + reason, basis, previous)
    resolution = {'outcome': outcome, 'reason': reason, 'decision_id': did, 'created_at': now(),
                  'output_id': output['id'] if output else None, 'artifact_sha256': output['sha256'] if output else None}
    history.append(resolution); feedback['status'] = outcome
    core.write(root / 'project.json', data)
    return dict(resolution, feedback_id=feedback_id, note='Recorded disposition; no automatic deck edit or library promotion.')

def record_review(directory, output_id, method, status, coverage, basis, reviewer):
    root, data = load_project(directory)
    output = checked_output(root, data, output_id)
    if method not in {'content_review', 'visual_review', 'native_powerpoint', 'projection', 'teaching_use'}:
        raise ValueError('Unknown review method')
    if status not in {'passed', 'issues', 'unverified'} or coverage not in {'full', 'partial'}:
        raise ValueError('Invalid review result or coverage')
    require_text(basis, 'Review evidence'); require_text(reviewer, 'Reviewer')
    reviews = data.setdefault('reviews', [])
    record = {'id': next_id(reviews, 'R'), 'output_id': output_id, 'artifact_sha256': output['sha256'],
              'method': method, 'status': status, 'coverage': coverage, 'basis': basis,
              'reviewer': reviewer, 'created_at': now(), 'evidence_type': 'recorded-review-attestation'}
    reviews.append(record); core.write(root / 'project.json', data)
    return record

def delivery_check(directory, output_id):
    root = Path(directory).resolve()
    report = core.check_project(root)
    blockers = list(report['errors']); warnings = []
    data = core.read(root / 'project.json')
    authority = data.get('content_authority')
    active = authority.get('source_ids', []) if isinstance(authority, dict) else []
    if not active or not authority.get('basis'):
        blockers.append('Content authority needs source_ids and a recorded basis.')
    policy = data.get('content_policy')
    if policy not in {'full_content_on_slides', 'summary_with_notes', 'user_defined'}:
        blockers.append('Content coverage policy is unresolved.')
    if policy == 'user_defined' and not data.get('content_policy_basis'):
        blockers.append('User-defined coverage needs its recorded basis.')
    for revision in data.get('source_revisions', []):
        if revision.get('status') == 'pending':
            blockers.append('Unresolved source revision: ' + revision['id'])
        try:
            path = core.contained(root, revision['report'])
            if core.sha(path) != revision['report_sha256']:
                blockers.append('Revision report changed: ' + revision['id'])
        except (ValueError, OSError):
            blockers.append('Revision report unavailable: ' + revision['id'])
    for feedback in data['feedback']:
        if feedback.get('status') in {'pending', 'deferred'}:
            message = 'Unresolved feedback: ' + feedback['id']
            (blockers if feedback.get('delivery_blocking') is True else warnings).append(message)
        for resolution in feedback.get('resolution_history', []):
            try:
                item(data['decisions'], resolution['decision_id'])
                if resolution['outcome'] == 'applied':
                    linked = checked_output(root, data, resolution['output_id'])
                    if linked['sha256'] != resolution['artifact_sha256']:
                        blockers.append('Feedback output binding changed: ' + feedback['id'])
            except (ValueError, KeyError):
                blockers.append('Feedback resolution link is invalid: ' + feedback['id'])
    output = None
    try:
        output = checked_output(root, data, output_id)
        if output['content_snapshot_sha256'] != snapshot_hash(content_snapshot(data)):
            blockers.append('Content/mappings changed after output registration; register the revised output.')
        snapshots = {s['id']: s['sha256'] for s in output['source_snapshot']}
        for sid in active:
            source = item(data['sources'], sid)
            if snapshots.get(sid) != source['sha256']:
                blockers.append('Output is not bound to the active content source: ' + sid)
        if len(data['slide_map']) != output['slide_count']:
            blockers.append('Map each output slide once, in output order.')
        records = [core.read(core.contained(root, item(data['sources'], sid)['records'])) for sid in active]
        expected = {r['id'] for rec in records for r in rec['segments']}
        used = {s for row in data['slide_map'] + data['omissions'] for s in row.get('source_segments', [])}
        if policy == 'full_content_on_slides' and expected - used:
            blockers.append(f'{len(expected-used)} active source segments lack a mapping or explicit omission.')
        for method in ['content_review', 'visual_review']:
            matching = [r for r in data['reviews'] if r.get('output_id') == output_id and
                        r.get('artifact_sha256') == output['sha256'] and r.get('method') == method]
            latest = matching[-1] if matching else None
            if not latest or latest.get('status') != 'passed' or latest.get('coverage') != 'full' or not latest.get('basis') or not latest.get('reviewer'):
                blockers.append('Full recorded review required for this output: ' + method)
    except (ValueError, OSError, KeyError) as exc:
        blockers.append(str(exc))
    blockers = list(dict.fromkeys(blockers))
    return {'record_valid': not report['errors'], 'ready': not blockers, 'blockers': blockers, 'warnings': warnings,
            'output_id': output_id, 'artifact_sha256': output['sha256'] if output else None,
            'review_basis': 'Recorded content/visual attestations plus file/mapping checks; not automatic semantic or visual verification.',
            'live_use_required_for_delivery': False,
            'live_use_recorded': any(output and r.get('output_id') == output_id and r.get('artifact_sha256') == output['sha256'] and r.get('method') == 'teaching_use' and r.get('status') == 'passed' for r in data['reviews'])}
