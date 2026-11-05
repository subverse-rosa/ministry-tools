# Changelog

## 0.4.2 — 2026-11-06
- Use a generic template example and a shorter installation guide.
- Keep repository maintenance files out of the skill ZIP.

## 0.4.1 — 2026-11-05
- First public installable release from Ministry Tools.
- Bundle a runnable sample service, score handoff and palette previews with invented material.
- Stamp 0.4.1 in the provenance of newly built decks.

## 0.4.0 — 2026-10-29
- One delivery spec: `references/delivery.md` (what a delivered deck, song folder and yaml must be).
- `check_delivery.py`: rebuilds a deck from its delivered yaml/JSON and compares slide count, per-slide
  text and per-slide XML with the delivered file; for a library folder also checks the public/production
  layout, stray files and copies of `styles.json`. Read-only on delivered files.
- `references/song-library.md`: one folder per song; public deck and score at top level, production
  files in `制作资料（勿改）/` (music/, slides/, records/, data/, lyrics/, source/).
- Build version stamped as 0.4.0 in deck provenance.

## 0.3.1 — 2026-10-29
- Lyric songs: `section_continuations` (a closing line continuing the last chorus: no badge, same
  background, centred) and `title_page: false` (medleys). Page numbers stay per song.
- navy-bilingual contrast fix adopted from a reviewed deck: chorus_bg #1B2C4F, en #9DC3D4,
  accent #A9C2E8 (chorus: CN 12.7, EN 7.4, accent 7.6 : 1; all thresholds now met).
- Rule: delivered decks must be reproducible from the delivered yaml/JSON; no post-editing, no
  per-song copies of styles.json.

## 0.3.0 — 2026-10-28
- Approved scores from the singable-lyric-translator (v1.9 handoff: `handoff.py events` JSON) are the
  preferred song source: `type: jianpu, handoff: …, score: …`. Drafts and stale exports are refused;
  accidentals (#/b), 16th-dotted notes and per-pass sections are drawn; phrases also break at sections.
- Provenance (score hash, lyric version, slide range) stored in each deck as a custom document property.
- `check_library.py`: reports every song deck as current / STALE / EXPORT-OLD / EDITED / MISSING.
- `template` is optional: song-only decks are plain 16:9 files (≈40 KB instead of ≈2.4 MB).
- `selftest.py` with an invented example song; `references/song-library.md` folder convention.
- Regression-checked slide output for PDF-extracted songs.

## 0.2.1 — 2026-10-28
- Per-step `transition: cut | fade` override.
- LED panel check accepted (provisional); design rules updated.

## 0.2.0 — 2026-10-26
- New step `type: cover`: generates a 环节 cover in the profile style when the template has none to reuse.
- Role labels other than 主席 / 会众 / 齐 (e.g. 牧师, 领, 众) are now shown as given instead of being dropped.

## 0.1.0 — 2026-10-22
- First version: whole-service builder (service.yaml → pptx), reading auto-pack, jianpu extraction,
  hymn import, seven colour profiles and a palette page.
