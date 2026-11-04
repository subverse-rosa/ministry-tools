# Optional bilingual staff and numbered-notation production

Use only for an explicit score/PDF/简谱 request. Ordinary lyric delivery stays
text-only. Preserve text-approved lines and accepted decisions; generating a
score does not approve new wording or rhythm proposals. Standard review remains
the default; Deep Review stays on demand.

## Inputs and route

Both routes need a readable source or reviewed music encoding/map, exact lyric
version, requested layers, credits and a way to render/inspect PDF pages. Missing
music evidence blocks an exact-score claim, not ordinary provisional translation.
The agent may find the score via [source intake](source-intake.md); a user need
not already own a five-line score. A chord sheet alone is insufficient.

| Route | Use | Required preparation | Default style |
| --- | --- | --- | --- |
| A: re-engrave | New bilingual underlay or reflow | Reviewed MEI/MusicXML with all pitches, durations, rests, ties, repeats/endings and explicit lyric syllables | A4; title/credits, staff, optional numbered guide, Chinese, English, copyright/status/page footer. |
| B: preserve PDF | Existing satisfactory staff/lyrics; only adding numbers | Original PDF + reviewed system crop/coordinate map with every guide event and voice | Original vector staff/lyrics strips; numbered bands below; preserve the source's repeat scheme. |

Do not replace a satisfactory existing style merely to use the other renderer.
Route B does not add/replace bilingual lyric underlay. Route A accepts an encoding,
not a PDF; reading/transcribing PDF or audio is a prior review task, not automatic
conversion. It can import MusicXML through Verovio; inspect import warnings and
converted MEI for dropped/changed notation. Keep uncompressed editable encodings.

## Shared music and layout contract

Record source hash/version and the lyric/ledger version. Distinguish source-bar
number, performance route and layout position. Retain repeats/endings or unfold
them explicitly and document the route. Check every occurrence of approved hooks.

Numbered notation needs an explicit reference `tonic` including octave (e.g.
`Bb3`), `scale` (`major` or `minor`) and `octave_shift`. Major uses movable 1;
minor here uses tonic=1, not the alternative relative-major/6 convention. For
the latter supply the relative-major tonic and `major` explicitly. Set/register
label written vs sounding pitch, octave clefs, transposing instruments and capo;
never subtract an octave silently. The helper treats encoded pitch as written
unless `octave_shift` is supplied. Use a single disclosed degree reference per
render; split sections or adapt the reviewed map for changing references.

Chinese is above English. Numbers are an auxiliary melody/selected-voice guide,
not a replacement for complete accompaniment. Label the selected staff/layer;
other voices remain on the staff. Route A uses the highest pitch for chord
events on its selected guide; complete chords remain on the staff. In PDF-preserve mode map simultaneous voices
to separate lanes. Preserve rests, accidentals, dotted lengths and ties including
system/page wraps; a tied continuation is not a fresh lyric attack. Tuplets need
both displayed note value and actual elapsed duration. Unsupported constructs
(microtones, double dots, an all-rest guide system in route A, etc.) must be
resolved in the encoding or rendered with another capable engine and disclosed,
not approximated silently. Review tuplet grouping on staff and numbered guide.

## Route A commands and profile

Optional dependency: `pip install verovio` (tested 6.3.0). SVG/HTML need no browser.
PDF additionally uses an installed Chrome/Edge/Chromium executable via `--browser`.
No engraving binaries or fonts are bundled in the skill. For example, from the
skill directory (choose a fresh output folder):

```sh
python scripts/engrave_score.py references/score-example.mei output/demo --profile references/score-profile.json --numbered
python scripts/engrave_score.py reviewed.musicxml output/song --profile song-profile.json --numbered --browser /path/to/chrome
```

`score-profile.json` is an invented example, not an approved song. Set `title`,
`subtitle`, `credits`, `copyright`, `tonic`, `scale`, `octave_shift`, `staff`,
`layer` and optional `font_file`. Font paths are relative to the profile file;
use a CJK-capable installed/licensed TTF/TTC font. HTML embeds a supplied font;
otherwise it relies on host fonts, which must be visually checked. Use `breaks:
"encoded"` only when the reviewed MEI has intentional system/page breaks; the
default is automatic layout. Chinese/English are verse 1/2 in the source. Numbers
are added as a separate guide without rewriting those verses. The route produces
MEI, page SVGs, HTML, audit/log and, with a browser, PDF. A nonempty warning log
requires assessment before delivery.

## Route B map and command

Optional dependencies: `pip install reportlab pypdf` (tested 4.4.9 / 6.10.0).

```sh
python scripts/add_numbers.py original.pdf reviewed-map.json output/staff-and-numbers.pdf
```

Map schema 1: `source_sha256`, `title`, `copyright`, optional CJK `font_file`,
`tonic`, `scale`, `octave_shift`, `register_label`, `systems`, and `ties` (pairs
of event IDs). Source coordinates are PDF points from the top-left of an
unrotated page with zero media-box origin. Normalize and re-review other pages
before mapping. Each system has one-based `page`, `crop: [left, top, right,
bottom]` enclosing the complete staff/lyrics, `band_height` in output points,
`barlines` (source x positions), `measure_durations` (ID → quarter-note duration),
and `events`. Each event has stable `id`, `measure`, `lane` (default 0), source
`x`, `pitches` (array; empty means rest), `onset` and `duration`. Use integer or
rational-string quarter-note times, not floats. For tuplets add `display_duration`
and `tuplet` label; `duration` remains actual elapsed time. Encode rests explicitly.
Every represented voice must cover its declared measure without gaps/overlap.
Ties must connect equal pitches in the reviewed map. Allocate enough band height
for all voice lanes, accidentals and octave dots.

Title/footer-only source strips may use no events and `band_height: 0`; include
the original credits/copyright or reproduce them faithfully in metadata. Entire
source systems are copied, so logos, chords, lyrics and slurs inside those crops
remain vector content. The helper paginates A4; it does not detect systems, read
glyphs or infer timing. Source hash mismatch or an existing output path fails
instead of overwriting. The audit records supplied-map status, not source truth.

## Review and handoff

Reopen/render every PDF page and inspect staff/guide alignment, accidentals,
octave/duration dots, beams/tuplets, ties/rests, line ends, CJK fonts, lyric
extenders/hyphens, credits, page breaks and clipping. Compare pitch and elapsed
time sequences against the source along the declared repeat route. Compare
lyric attack positions separately. For an approved Adaptive split, report
preserved pitch contour and phrase duration **with the named changed attacks**;
do not call the rhythm identical. An unchanged source file hash alone does not
prove correct output notation or complete source coverage.

For slides/projection, hand over the reviewed MEI per [score handoff](score-handoff.md) after `scripts/handoff.py check` passes. Deliver the requested PDF and editable source/map if wanted, with a concise
source/lyric version, approved changes and actual checks. Never label mechanical
rendering, numerical round-trip checks, a visual read or original-song playback
as real singing of the new lyrics. M4 remains pending until that trial exists.

Engine references: [Verovio](https://book.verovio.org/toolkit-reference/toolkit-methods.html),
[PDF transformations](https://pypdf.readthedocs.io/en/stable/user/cropping-and-transforming.html).
