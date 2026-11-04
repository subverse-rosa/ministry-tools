#!/usr/bin/env python3
"""Validate the source tree and build reproducible runtime-only release artifacts."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {'.md', '.json', '.py', '.txt', '.mei'}
UPLOAD_ZIP = 'singable-lyric-translator_latest.zip'  # mutable, always the newest build; versioned copies live in dist/ and ../_archive/

def sha(data):
    return hashlib.sha256(data).hexdigest()

def config(root):
    cfg = json.loads((root/'release.json').read_text(encoding='utf-8'))
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', cfg['name']) or len(cfg['name']) > 64:
        raise ValueError('Invalid skill name')
    if not re.fullmatch(r'\d+\.\d+\.\d+', cfg['version']):
        raise ValueError('Version must be MAJOR.MINOR.PATCH')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', cfg['release_date']):
        raise ValueError('Release date must be YYYY-MM-DD')
    if cfg['profiles'] != {'standard':'named-folder', 'gemini':'zip-root', 'standalone':'skill-md-only'}:
        raise ValueError('Unsupported export profiles')
    return cfg

def runtime_payload(root, cfg):
    runtime = root/'skill'
    wanted = cfg['runtime_files']
    if len(set(wanted)) != len(wanted) or 'SKILL.md' not in wanted:
        raise ValueError('Runtime allowlist must be unique and include SKILL.md')
    payload = {}
    for rel in wanted:
        path = PurePosixPath(rel)
        if path.is_absolute() or '..' in path.parts or '\\' in rel or ':' in rel:
            raise ValueError(f'Unsafe runtime path: {rel}')
        if any(p.startswith('.') for p in path.parts) or path.suffix not in SUPPORTED:
            raise ValueError(f'Unsupported runtime type/path: {rel}')
        target = runtime/rel
        if target.is_symlink() or runtime.resolve() not in target.resolve().parents:
            raise ValueError(f'Runtime file escapes skill folder: {rel}')
        if any((runtime/Path(*path.parts[:i])).is_symlink() for i in range(1,len(path.parts))):
            raise ValueError(f'Symlink in runtime path: {rel}')
        data = target.read_bytes()
        data.decode('utf-8')
        if b'\x00' in data:
            raise ValueError(f'Binary content: {rel}')
        payload[rel] = data
    actual = {p.relative_to(runtime).as_posix() for p in runtime.rglob('*') if p.is_file()}
    if actual != set(wanted):
        raise ValueError(f'Unexpected/missing runtime files: {sorted(actual.symmetric_difference(wanted))}')
    if sum(map(len,payload.values())) > 100_000_000:
        raise ValueError('Runtime exceeds 100 MB')
    return payload

def check_version_stamp(text, cfg):
    """SKILL.md carries a visible version line that must match release.json (so any copy of the skill is identifiable)."""
    match = re.search(r'^\*\*Version:\*\* (\d+\.\d+\.\d+) \(released (\d{4}-\d{2}-\d{2})\)$', text, re.M)
    if not match:
        raise ValueError('SKILL.md needs a line: **Version:** X.Y.Z (released YYYY-MM-DD)')
    if (match.group(1), match.group(2)) != (cfg['version'], cfg['release_date']):
        raise ValueError(f"SKILL.md version stamp {match.group(1)} ({match.group(2)}) does not match release.json {cfg['version']} ({cfg['release_date']})")


def validate_source(root):
    cfg = config(root)
    payload = runtime_payload(root,cfg)
    text = payload['SKILL.md'].decode('utf-8')
    # This master deliberately uses only two single-line YAML fields. No PyYAML needed.
    match = re.match(r'\A---\r?\nname: ([^\r\n]+)\r?\ndescription: ([^\r\n]+)\r?\n---(?:\r?\n|$)',text)
    if not match or match.group(1) != cfg['name']:
        raise ValueError('SKILL.md must start with matching name and description frontmatter')
    description = match.group(2)
    if not 1 <= len(description) <= 1024 or any(c in description for c in '<>'):
        raise ValueError('Invalid skill description')
    if ': ' in description or ' #' in description:
        raise ValueError('Quote-free frontmatter description cannot contain YAML mapping/comment syntax')
    check_version_stamp(text, cfg)
    if '[TODO:' in text:
        raise ValueError('Unfinished skill scaffold')
    for ref in re.findall(r'\]\((references/[^)]+)\)',text):
        if ref not in payload:
            raise ValueError(f'Broken skill reference: {ref}')
    for old in ('core/','adapters/','templates/','evals/'):
        if re.search(r'(?<![A-Za-z0-9_-])'+re.escape(old), text):
            raise ValueError(f'Stale runtime dependency: {old}')
    for path in root.rglob('*.json'):
        if 'dist' not in path.relative_to(root).parts and '.git' not in path.relative_to(root).parts:
            json.loads(path.read_text(encoding='utf-8'))
    cases = json.loads((root/'tests/cases.json').read_text(encoding='utf-8'))['tests']
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Duplicate behavioral case IDs')
    for path in list((root/'skill').rglob('*.py')) + list((root/'tests').rglob('*.py')) + list((root/'tools').rglob('*.py')):
        compile(path.read_text(encoding='utf-8'),str(path),'exec')
    return cfg,payload

def command(root,args,expected=0,input_text=None):
    result = subprocess.run([sys.executable,'-B','-X','utf8',*args],cwd=root,input=input_text,capture_output=True,text=True,encoding='utf-8')
    if result.returncode != expected:
        raise ValueError(f"Check failed: {' '.join(args)}\n{result.stdout}{result.stderr}")
    return result.stdout+result.stderr

def verify_distribution(root,cfg,payload):
    """Check the tracked public ZIP without replacing it during development."""
    archive = root/UPLOAD_ZIP
    checksum = root/'SHA256.txt'
    if not archive.exists() and not checksum.exists():
        return {'status':'not_present'}
    if not archive.is_file() or not checksum.is_file():
        raise ValueError('Distribution ZIP and SHA256.txt must both exist')
    data = archive.read_bytes()
    if checksum.read_text(encoding='utf-8').strip() != f'{sha(data)}  {UPLOAD_ZIP}':
        raise ValueError('Distribution SHA256.txt does not match ZIP bytes')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            if len(names) != len(set(names)) or 'SKILL.md' not in names or z.testzip() is not None:
                raise ValueError('Invalid distribution entries or CRC')
            for rel in names:
                path = PurePosixPath(rel)
                if path.is_absolute() or '..' in path.parts or '\\' in rel or ':' in rel or any(p.startswith('.') for p in path.parts):
                    raise ValueError(f'Unsafe distribution path: {rel}')
            contents = {rel:z.read(rel) for rel in names}
            text = contents['SKILL.md'].decode('utf-8')
    except (zipfile.BadZipFile,UnicodeError) as exc:
        raise ValueError('Invalid distribution ZIP') from exc
    stamp = re.search(r'^\*\*Version:\*\* (\d+\.\d+\.\d+) \(released (\d{4}-\d{2}-\d{2})\)$',text,re.M)
    if not stamp:
        raise ValueError('Distribution has no release version stamp')
    version = stamp.group(1)
    if tuple(map(int,version.split('.'))) > tuple(map(int,cfg['version'].split('.'))):
        raise ValueError('Distribution version is newer than source release.json')
    if version == cfg['version']:
        if stamp.group(2) != cfg['release_date'] or contents != payload:
            raise ValueError('Same-version distribution differs from source; bump the source version')
        status = 'verified_same_version_source'
    else:
        status = 'verified_older_distribution'
    return {'status':status,'version':version,'sha256':sha(data),'bytes':len(data)}

def checks(root,history_dir=None):
    output = command(root,['-m','unittest','discover','-s','tests','-p','test_*.py'])
    print(output.strip())
    fixtures = json.loads((root/'tests/fixtures/checker_replays.json').read_text(encoding='utf-8'))['replays']
    exit_codes = {'AUTO_PASS':0,'AUTO_FAIL':1,'MANUAL_REVIEW_REQUIRED':2}
    for fixture in fixtures:
        result = json.loads(command(root,['tests/run_checks.py',fixture['case'],'-','--json'],
                                    exit_codes[fixture['status']],fixture['reply']))
        if result['status'] != fixture['status'] or result['behavioral_validation'] != 'not_tested':
            raise ValueError('Unexpected synthetic checker status')
    replay_statuses = {}
    if history_dir is not None:
        history_dir = Path(history_dir).resolve()
        required = [history_dir/f'E{i:02}.txt' for i in range(1,18)]
        if not all(path.is_file() for path in required):
            raise ValueError('Optional history directory must contain all E01-E17 reply files')
        expected_statuses = json.loads((root/'tests/fixtures/historical_checker_expectations.json').read_text(encoding='utf-8'))['statuses']
        for path in required:
            tid = path.stem
            result = json.loads(command(root,['tests/run_checks.py',tid,str(path),'--json'],exit_codes[expected_statuses[tid]]))
            replay_statuses[tid] = result['status']
            if result['status'] != expected_statuses[tid]:
                raise ValueError(f'Unexpected historical checker status: {tid}')
    command(root,['skill/scripts/check_counts.py','--slots','8,6,8,6','tests/fixtures/example_level_b.md'])
    command(root,['skill/scripts/check_rhythm.py','skill/references/capacity-example.json'])
    print(f'Completed: {len(fixtures)} synthetic checker fixtures, count and rhythm examples; {len(replay_statuses)} optional historical replays')
    test_count = re.search(r'Ran (\d+) tests?',output)
    return {'automated_regressions':'passed','automated_regression_count':int(test_count[1]) if test_count else None,
            'synthetic_checker_replays':len(fixtures),'historical_checker_replays':len(replay_statuses),
            'historical_checker_statuses':replay_statuses,'synthetic_rhythm_example':'passed','worked_example_count':'passed',
            'fresh_model_behavior':'not independently evaluated','platform_upload_acceptance':'not tested','real_singer_validation':'not performed'}

def zip_bytes(payload,prefix=''):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for rel,data in sorted(payload.items()):
            info=zipfile.ZipInfo(prefix+rel,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3
            info.external_attr=0o100644 << 16
            z.writestr(info,data)
    result=buf.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failed')
    return result

def export_plan(cfg,payload,validation):
    base=f"{cfg['name']}_v{cfg['version']}"
    artifacts={
        base+'_standard.zip':zip_bytes(payload,cfg['name']+'/'),
        base+'_gemini.zip':zip_bytes(payload),
        base+'_standalone/SKILL.md':payload['SKILL.md']
    }
    manifest={
        'name':cfg['name'],'version':cfg['version'],'release_date':cfg['release_date'],
        'runtime_files':{p:{'sha256':sha(data),'bytes':len(data)} for p,data in sorted(payload.items())},
        'artifacts':{p:{'sha256':sha(data),'bytes':len(data)} for p,data in sorted(artifacts.items())},
        'validation':validation
    }
    artifacts[base+'_manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    return artifacts

def write_plan(dest,artifacts):
    # Preflight every target before any write; same-version differing releases are immutable.
    for rel,data in artifacts.items():
        path=dest/rel
        if path.exists() and path.read_bytes()!=data:
            raise ValueError(f'Existing release differs: {path}; bump release.json version')
    for rel,data in artifacts.items():
        path=dest/rel
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            with path.open('xb') as f: f.write(data)

def update_upload_zip(root,payload):
    """Refresh the explicitly mutable Spark upload entrypoint (UPLOAD_ZIP) after a successful release."""
    target=root/UPLOAD_ZIP
    data=zip_bytes(payload)
    if target.exists() and target.read_bytes()==data:
        return target
    temporary=root/(UPLOAD_ZIP+'.tmp')
    if temporary.exists():
        raise ValueError('Upload ZIP temporary file exists; inspect it before retrying')
    with temporary.open('xb') as f:
        f.write(data)
    temporary.replace(target)
    return target

def export_release(root,cfg,payload,validation,output_dir=None):
    """Explicit output folders leave the tracked distribution untouched."""
    root = Path(root).resolve()
    destination = (Path(output_dir) if output_dir is not None else root/'dist').resolve()
    if output_dir is not None and (destination == root or any(
            (root/p) == destination or (root/p) in destination.parents
            for p in ('skill','tests','tools','.git'))):
        raise ValueError('--output-dir must be outside source/runtime folders (dist/ is allowed)')
    write_plan(destination,export_plan(cfg,payload,validation))
    upload_root = destination if output_dir is not None else root
    update_upload_zip(upload_root,payload)
    if output_dir is None:
        (root/'SHA256.txt').write_text(sha((root/UPLOAD_ZIP).read_bytes())+'  '+UPLOAD_ZIP+'\n',encoding='utf-8')
    return destination

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='validate and test without exporting')
    parser.add_argument('--output-dir',type=Path,help='build into this directory without changing the tracked ZIP/checksum')
    parser.add_argument('--history-dir',type=Path,help='optional local directory containing original E01-E17 reply files')
    args=parser.parse_args()
    if args.check and args.output_dir is not None:
        parser.error('--check and --output-dir are separate validation/build modes')
    try:
        cfg,payload=validate_source(ROOT)
        distribution=verify_distribution(ROOT,cfg,payload)
        validation=checks(ROOT,args.history_dir)
        if not args.check:
            destination = export_release(ROOT,cfg,payload,validation,args.output_dir)
            print(f"Built {cfg['version']}: standard ZIP, Gemini ZIP, standalone SKILL.md and manifest")
            print('Build destination: '+str(destination))
        print('Tracked distribution: '+distribution['status'])
        print('PASS: source validation, JSON, Python syntax, references and runtime allowlist')
    except (ValueError,OSError,KeyError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
