# Teaching Slides

Run development commands from this directory. See the [Ministry Tools index](../README.md) for new release tags and companion skills.

Public v0.2.1 preview for sermon and lecture slides. Uses the host's presentation tools and adds
source preservation, visual decisions, offline reference gallery, scoped feedback and durable
project records. See [Worship Slides](../worship-slides/) for service and song assembly.

## Download and install

- [v0.2.1 preview release](https://github.com/subverse-rosa/ministry-tools/releases/tag/teaching-slides-v0.2.1)
- [Installable skill ZIP](https://github.com/subverse-rosa/ministry-tools/releases/download/teaching-slides-v0.2.1/teaching-slides_v0.2.1.zip)
- [Offline visual library](https://github.com/subverse-rosa/ministry-tools/releases/download/teaching-slides-v0.2.1/visual-library.html)
- [Checksums](https://github.com/subverse-rosa/ministry-tools/releases/download/teaching-slides-v0.2.1/SHA256.txt)

The ZIP contains one `teaching-slides/` folder. Keep its instructions, references, scripts
and assets together and follow the host's skill installation procedure. GitHub's automatic
Source code archive is a repository snapshot, not this installation package. The gallery
is a standalone HTML download; open it locally to browse and compare examples.

## Companion tools

[ROSA](https://github.com/subverse-rosa/rosa-skill) can help develop and review theological
content; teaching-slides preserves the supplied argument and organizes its presentation.
[Singable Lyric Translator](../singable-lyric-translator/)
handles lyric and music decisions. Worship slide assembly is a separate companion workflow.
Each skill can be used independently. Links do not install or automatically invoke another skill.

- `skill/teaching-slides/`: canonical installable source and gallery.
- `tools/release.py`: reproducible packaging and managed installation.
- `tests/`: synthetic behavior checks.
- `projects/`: ignored private sources, maps and feedback.
- `dist/`: ignored generated packages and hashes.

Open `skill/teaching-slides/assets/library/index.html`. It works offline. Search/filter, inspect
source-derived examples and export observations for project import. Browser drafts are not
the maintained ledger. The library is reference material, not a fixed set of permitted designs.

Python 3.10+ helpers need no packages. Actual deck authoring/rendering uses the host's tools.

```text
python -m unittest discover -s tests -v
python skill/teaching-slides/scripts/library.py check
python skill/teaching-slides/scripts/library.py build
python tools/release.py build
python tools/release.py build --export-dir <stack-directory>
python tools/release.py install --target <personal-skills-directory>/teaching-slides
```

The author approved public distribution of the included source-page examples. Working
project snapshots and feedback remain outside Git under `projects/`. Learning and promotion
require deliberate file updates. Validation covers helper behavior, extraction, gallery
integrity and browser interaction; a newly authored deck, field projection and teaching
effectiveness remain untested.

## v0.2 workflow

Adds source revision reports, immutable output/map snapshots, version-bound feedback resolution,
a distinct delivery-readiness check, and multi-example comparison. The library contains
12 patterns and 15 original source-page previews. See `skill/teaching-slides/references/operations.md`.

`project.py check` validates records. `project.py check <project> --for-delivery --output O1`
checks required records/bindings for a specific output. It does not perform semantic or rendered
review. Use `compare`, `revise`, `revision-decision`, `register-output`, `resolve` and `review`
as appropriate. Keep old sources, approved decisions and output snapshots.
