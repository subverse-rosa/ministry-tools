"""Build a reproducible skill ZIP and synchronize a managed installation."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import uuid
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

REPO = Path(__file__).resolve().parents[1]
MARKER = '.teaching-slides-install.json'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def inventory(root):
    root = Path(root).resolve()
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlinks are not packaged: ' + str(path))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc' and path.name != MARKER:
            files[path.relative_to(root).as_posix()] = digest(path)
    return files

def prepare(repo=REPO):
    repo = Path(repo)
    release = json.loads((repo / 'release.json').read_text(encoding='utf-8'))
    source = (repo / release['source']).resolve()
    if not source.is_relative_to(repo.resolve()) or not (source / 'SKILL.md').is_file():
        raise ValueError('Invalid canonical skill path')
    version = re.search(r'^  version: ([^\r\n]+)$', (source / 'SKILL.md').read_text(encoding='utf-8'), re.M)
    if not version or version.group(1) != release['version']:
        raise ValueError('Skill/release version mismatch')
    spec = importlib.util.spec_from_file_location('teaching_library_release', source / 'scripts/library.py')
    lib = importlib.util.module_from_spec(spec); spec.loader.exec_module(lib)
    result = lib.build(source / 'assets/library')
    if result['errors']:
        raise ValueError('Invalid library')
    if lib.load(source / 'assets/library')['version'] != release['version']:
        raise ValueError('Catalog/release version mismatch')
    return source, release, inventory(source)

def build(repo=REPO):
    repo = Path(repo)
    source, release, files = prepare(repo)
    dist = repo / 'dist'; dist.mkdir(exist_ok=True)
    package_name = release.get('package_name', f"teaching-slides_v{release['version']}_private.zip")
    if Path(package_name).name != package_name or not package_name.endswith('.zip'):
        raise ValueError('Package name must be a ZIP filename')
    package = dist / package_name
    with ZipFile(package, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            released = datetime.fromisoformat(release['date'])
            info = ZipInfo('teaching-slides/' + name, date_time=(released.year, released.month, released.day, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (source / name).read_bytes())
    manifest = {'name': release['name'], 'version': release['version'], 'distribution': release['distribution'],
                'package': package.name, 'package_sha256': digest(package), 'files': files}
    (dist / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest

def install(target, repo=REPO):
    source, release, files = prepare(repo)
    raw = Path(target)
    if raw.is_symlink():
        raise ValueError('Installation target is a symlink')
    target = raw.resolve()
    if target.name != 'teaching-slides' or target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError('Use a separate, explicitly named teaching-slides installation directory')
    backup = None
    if target.exists():
        marker = target / MARKER
        if not marker.is_file():
            raise ValueError('Existing installation is unmanaged; reconcile before replacing')
        old = json.loads(marker.read_text(encoding='utf-8'))
        if inventory(target) != old['files']:
            raise ValueError('Installed files have changed; reconcile edits into source first')
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.parent / ('.teaching-slides-stage-' + uuid.uuid4().hex)
    stage.mkdir()
    for name in files:
        dest = stage / name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, dest)
    if inventory(stage) != files:
        raise ValueError('Staged installation differs from source')
    (stage / MARKER).write_text(json.dumps({'version': release['version'], 'files': files}, indent=2) + '\n', encoding='utf-8')
    if target.exists():
        backup_root = target.parent / '.teaching-slides-backups'
        backup_root.mkdir(exist_ok=True)
        backup = backup_root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
        if not backup.resolve().is_relative_to(backup_root.resolve()):
            raise ValueError('Invalid backup path')
        target.rename(backup)
    try:
        stage.rename(target)
    except OSError:
        if backup is not None and not target.exists():
            backup.rename(target)
        raise
    if inventory(target) != files:
        raise ValueError('Installed file hashes differ from canonical source')
    return {'target': str(target), 'version': release['version'], 'files': len(files),
            'verified_equal': True, 'backup': str(backup) if backup else None}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'install'])
    parser.add_argument('--target', type=Path)
    parser.add_argument('--export-dir', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'install':
            if args.target is None:
                parser.error('install requires --target')
            result = install(args.target)
        else:
            manifest = build()
            if args.export_dir is not None:
                export = args.export_dir.resolve(); export.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO / 'dist' / manifest['package'], export / 'teaching-slides_latest.zip')
                shutil.copy2(REPO / 'skill/teaching-slides/assets/library/index.html', export / '视觉表达参考库.html')
                exported = dict(manifest, exported_package='teaching-slides_latest.zip')
                (export / 'teaching-slides_manifest.json').write_text(json.dumps(exported, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            result = {k: v for k, v in manifest.items() if k != 'files'}
            result['files'] = len(manifest['files'])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
