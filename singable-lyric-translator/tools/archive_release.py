#!/usr/bin/env python3
"""Archive a previous release outside the development repository.

    python tools/archive_release.py 1.3.1

Moves that version's dist/ artifacts (standard.zip, gemini.zip, manifest.json, standalone/) into
the archive, adds a source snapshot made from the skill’s version tag (no .git, no dist), verifies every
file by SHA-256, then removes the originals from dist/. Refuses the current release (release.json),
a missing tag, or an archive folder that already exists. Archive entries are never edited later.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def tree_hashes(path):
    path = Path(path)
    if path.is_file():
        return {'': sha(path)}
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}

def ensure_archivable(version, cfg):
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Version must be MAJOR.MINOR.PATCH')
    if version == cfg['version']:
        raise ValueError(f'{version} is the current release in release.json; archive it after the next release is built')

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('version')
    args = parser.parse_args()
    try:
        cfg = json.loads((ROOT/'release.json').read_text(encoding='utf-8'))
        ensure_archivable(args.version, cfg)
        name, ver = cfg['name'], args.version
        base = f'{name}_v{ver}'
        prefix = subprocess.check_output(
            ['git', 'rev-parse', '--show-prefix'], cwd=ROOT, text=True
        ).strip().rstrip('/')
        tag = f'{name}-v{ver}' if prefix else f'v{ver}'
        tree = f'{tag}:{prefix}' if prefix else tag
        repo = Path(subprocess.check_output(
            ['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True, encoding='utf-8'
        ).strip())
        archive_root = repo.parent / '_archive'
        if prefix:
            archive_root /= name
        dest = archive_root / f'v{ver}'
        if dest.exists():
            raise ValueError(f'Archive already exists: {dest}')
        if subprocess.run(['git', 'rev-parse', '-q', '--verify', f'refs/tags/{tag}'], cwd=ROOT, capture_output=True).returncode != 0:
            raise ValueError(f'Git tag {tag} not found; cannot make a source snapshot')
        items = [base+'_standard.zip', base+'_gemini.zip', base+'_manifest.json', base+'_standalone']
        missing = [i for i in items if not (ROOT/'dist'/i).exists()]
        if missing:
            raise ValueError(f'Missing in dist/: {missing}')
        before = {i: tree_hashes(ROOT/'dist'/i) for i in items}
        dest.mkdir(parents=True)
        for i in items:
            src = ROOT/'dist'/i
            shutil.copytree(src, dest/i) if src.is_dir() else shutil.copy2(src, dest/i)
        source = dest/(base+'_source.zip')
        with source.open('xb') as out:
            subprocess.run(['git', 'archive', '--format=zip', f'--prefix={name}/', tree],
                           cwd=repo, stdout=out, check=True)
        for i in items:
            if tree_hashes(dest/i) != before[i]:
                raise ValueError(f'Copy verification failed for {i}; originals left in dist/')
        for i in items:
            src = ROOT/'dist'/i
            shutil.rmtree(src) if src.is_dir() else src.unlink()
        print(f'Archived v{ver} -> {dest}')
        for p in sorted(dest.iterdir()):
            print('  ', p.name)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
