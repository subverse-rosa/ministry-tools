# Delivery spec

What a delivered deck, a song folder and a yaml must satisfy. One page; `check_delivery.py` checks it.

## A delivered deck
- Built by `build_service.py` from the delivered yaml and the JSON / score / hymn files it names.
  Rebuilding from those inputs reproduces the deck slide for slide (`check_delivery.py <yaml> <deck>`).
- No post-editing of generated slides and no hand-made slides added to a skill-built deck.
  A deck made elsewhere is a different thing: label it as such and do not present it as skill output.
- Provenance is present for every handoff-built song (`worship-slides` custom property).
- Name: `<歌名>（简谱）.pptx` for a song, `<DDMMYYYY> 主日崇拜PPT - <堂>.pptx` for a service.

## A song folder (library convention, `song-library.md`)
- Top level: the deck, the score PDF, and `说明.txt` (one short paragraph for shared users: what the
  files are, which deck to show, who to ask). Nothing else.
- `制作资料（勿改）/` holds the production files: `music/` (score.mei, events JSON), `slides/` (the yaml),
  `records/` (review or provenance notes), `data/` (song JSON), `lyrics/`, `source/` (the original score).
- No `styles.json` anywhere in a song folder: colours come from the skill's `assets/styles.json`.
- Superseded decks and packages go to `_archive/` (moved, never deleted).

## A yaml
- Lives in `slides/` beside its deck. Relative paths resolve from the yaml's folder.
- Uses the profile name only; no copied palette.

## Checks
- `check_delivery.py <yaml> <deck>`: rebuild and compare (exit 1 on any difference).
- `check_delivery.py <folder>`: layout, styles copies, and every `slides/*.yaml` rebuilt and compared.
- `check_library.py <folder>`: handoff currency (current / STALE / EXPORT-OLD / EDITED / MISSING).
