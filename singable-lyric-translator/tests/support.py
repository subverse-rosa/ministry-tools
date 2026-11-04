"""Shared UTF-8 CLI invocation and workspace scratch directories."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def scratch():
    # Inherit ordinary permissions; restricted Windows environments reject 0700.
    parent = (ROOT/'tests').resolve()
    folder = parent/('scratch-'+uuid.uuid4().hex)
    folder.mkdir()
    try:
        yield folder
    finally:
        if folder.resolve().parent != parent:
            raise ValueError('Scratch cleanup escaped tests directory')
        shutil.rmtree(folder)


def run_count(text, *args, python_utf8=True):
    flags = ['-B','-X','utf8'] if python_utf8 else ['-B']
    env = os.environ.copy()
    if not python_utf8:
        env.update(PYTHONUTF8='0',PYTHONIOENCODING='cp1252')
    return subprocess.run([sys.executable,*flags,str(ROOT/'skill/scripts/check_counts.py'),*args],
                          input=text,capture_output=True,text=True,encoding='utf-8',env=env)
