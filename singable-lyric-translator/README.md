# Singable Lyric Translator

Run development commands from this directory. See the [Ministry Tools index](../README.md) for new release tags and companion skills.

Translate English lyrics into natural, singable Chinese while preserving meaning,
repeated hooks and song structure. A companion project to
[ROSA](https://github.com/subverse-rosa/rosa-skill), also usable independently.

## Package

- Current version and package date: [release.json](release.json).
- [Historical releases](https://github.com/subverse-rosa/singable-lyric-translator/releases/latest)
- [Download package](singable-lyric-translator_latest.zip)
- [SHA-256 checksum](SHA256.txt)
- [Read the skill instructions](skill/SKILL.md)

The ZIP contains the runtime files listed in `release.json`, sourced from
`skill/`. They include source intake, optional score production and the
reviewed-score handoff to slide tools. Development checks and build tools
remain in the repository and are excluded from installation packages.

## Install

For a host that supports this ZIP layout, upload the complete ZIP. For file-based
installation, create a folder named `singable-lyric-translator` and extract all ZIP
contents into it, keeping `SKILL.md`, `references/` and `scripts/` together. Follow
your host's installation procedure; platform acceptance has not been verified here.

On Windows, check the downloaded ZIP with:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath .\singable-lyric-translator_latest.zip
```

Compare the result with `SHA256.txt`. GitHub's automatic Source code archive is a
repository snapshot; use the named package above for installation.

## Workflow and evidence

Adaptive analysis is the default when rhythm evidence is available. Proposed
rhythmic reallocations require explicit user approval before adoption. Deep Review
is on demand; ordinary review targets material improvements.

Automated checks cover the count/rhythm helpers, evidence-status reporting, rule
declarations and release packaging. GitHub Actions runs the same entrypoint on
Windows and Linux for pushes to `main` and for pull requests. The test inventory
and its limits are documented in [tests/COVERAGE.md](tests/COVERAGE.md).

Historical local checker replays retain their mixed statuses: 12 AUTO_PASS,
2 AUTO_FAIL for unmarked explanatory prose, and 3 requiring manual review.
Those private replies are not required by CI or included here. Automated checks
do not certify model behavior, real-score transcription, platform installation
or actual singer performance.

## Source links and score output

You can start with a song/YouTube link. The skill searches available authoritative
sources, checks the edition/arrangement and records unresolved differences. It
does not bundle a browsing service or claim automatic audio transcription.

Score production runs only when requested. It supports reviewed MEI/MusicXML
for bilingual staff with an optional numbered guide, or preserves an existing
PDF's staff/lyrics while adding a reviewed numbered guide. Readable music evidence
and reviewed underlay/coordinates are required; a chord chart alone is insufficient.
The [score guide](skill/references/score-production.md) explains inputs, templates,
fonts, commands and limits. Optional renderer packages are listed in
`tools/score-requirements.txt`; they are not needed for text translation.
An approved song is handed to slide tools as the reviewed MEI itself; the
[score handoff](skill/references/score-handoff.md) defines the record and
`skill/scripts/handoff.py` checks it with the standard library only.

## Development

Use Python 3.10 or newer; these checks need only the standard library:

```sh
python -B -X utf8 tools/build_release.py --check
```

To test packaging without replacing the tracked download:

```sh
python -B -X utf8 tools/build_release.py --output-dir dist/preview
```

Both commands validate source and run the same tests once. CI uses an output
folder outside the checkout. The runtime retains Adaptive approval gates and
on-demand Deep Review. Routine solo maintenance can be committed locally and
pushed directly to `main`; use a branch or PR when a separate review is useful.
See [CONTRIBUTING.md](CONTRIBUTING.md) for maintenance, external contributions,
release exports and optional local-history checks.

## Working with ROSA

ROSA can assist with theological and contextual review of worship lyrics. This
skill focuses on translation, native Chinese craft and musical allocation. Install
each separately; a link between repositories does not automatically install or run
the companion skill.
