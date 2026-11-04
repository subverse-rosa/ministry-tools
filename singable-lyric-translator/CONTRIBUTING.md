# Contributing

## Maintainer workflow

For routine solo maintenance, edit the local checkout, run the relevant checks,
review the diff and commit locally. These changes can be pushed directly to
`main`; a PR is optional. Use a branch for isolated work and a PR when a
separate review is useful or requested. Publishing a GitHub Release remains
a separate maintainer decision.

## External contributions

Open an issue for feedback, or propose a change on a branch or fork and open a
pull request against `main`. Explain the problem, resulting behavior and
relevant verification. The maintainer reviews and merges contributions.
A green check is evidence about the tools, not approval of a lyric or rhythm
adjustment.

## Repository layout

- `skill/`: installable instructions, references, runtime helpers and optional score tools.
- `tests/`: automated regressions, public synthetic fixtures and manual cases.
- `tools/`: development-only validation, packaging and local archiving.
- `dist/`: Git-ignored exports of the current release and temporary preview builds.
- The root [lyric workflow](../.github/workflows/lyric.yml) runs checks for this project.
- `release.json`: source version, release date and runtime file allowlist.
- The root ZIP and `SHA256.txt`: the published download, retained until an
  intentional release refresh.

`skill/` is the canonical runtime source. Refresh installed copies from the
reviewed package after a runtime release; GitHub does not update installed
skills automatically. Documentation-only changes do not require reinstalling
the runtime. Do not commit private chat histories, user scores or generated
song deliveries. Use invented or appropriately licensed test fixtures.

## Checks and builds

Python 3.10+ and the standard library are sufficient. CI uses Python 3.12 on
Windows and Linux. Run either the validation mode or the isolated build:

```sh
python -B -X utf8 tools/build_release.py --check
python -B -X utf8 tools/build_release.py --output-dir dist/preview
```

These are alternative entrypoints; a build already runs the checks. Both verify
the allowlist, version stamp, JSON, Python syntax, references, tracked ZIP
checksum and test suite. An isolated build exports a named-folder ZIP, a ZIP
with `SKILL.md` at its root, a standalone `SKILL.md`, a manifest and a copy of
the latest upload ZIP. It leaves the tracked ZIP and checksum untouched.

The standalone file is an exact instruction copy for inspection or hosts that
handle its references separately. It does not embed the referenced files and
is not equivalent to installing the complete package. Export profile names do
not establish platform upload acceptance.

Published same-version bytes must match the source. For a runtime change, bump
the source version and visible `SKILL.md` stamp together, with the appropriate
release date. The builder permits the previous published ZIP to remain while
the newer source is reviewed. Infrastructure-only changes do not require a
runtime version bump.

Versioned artifacts in an output folder are immutable: a differing artifact at
the same path is rejected before writing any versioned file. Use a fresh preview
folder when changing build evidence. The manifest records what was tested and
explicitly records model/platform/singer checks that have not been performed.

## Publishing a release

After reviewing the source and validation, the maintainer can run:

```sh
python -B -X utf8 tools/build_release.py
```

This exports versioned files to `dist/`, refreshes the root upload ZIP and writes
its SHA-256 checksum. Review and commit the intended published files before
tagging as `singable-lyric-translator-vX.Y.Z` and creating a GitHub Release. CI never commits, tags, publishes or
merges a release automatically. Documentation-only housekeeping can be
committed without rebuilding the ZIP, moving its tag or bumping the runtime
version.

Keep only the active release exports in `dist/` after archiving older releases.
Preview builds may use a fresh temporary output folder. Store recovery snapshots
and superseded source copies in the local library archive; use clearly named
branches or worktrees for active development.

`tools/archive_release.py VERSION` is an optional local administration command
for earlier builds from this directory. It needs the version’s tag and complete local
`dist/` artifacts, copies them to the local archive, verifies the copies,
then removes the originals. It refuses the current version. It is not run by CI
or by the builder; a fresh clone need not contain older artifacts.

## Optional local replay

If you retain the original E01-E17 replies privately, pass their folder explicitly:

```sh
python -B -X utf8 tools/build_release.py --check --history-dir /path/to/private/replies
```

All 17 files must be present. The expected statuses are public metadata; their
reply contents remain local. The default CI uses three invented checker replies
and never depends on this folder. See [tests/README.md](tests/README.md) for the
distinction between checker results and behavioral acceptance.
