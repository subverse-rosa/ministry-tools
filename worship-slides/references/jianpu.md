# Jianpu (简谱) songs

## Song JSON (what `type: jianpu` reads)
```json
{"title": "晨光小径", "en_title": "Morning Path", "key": "1 = B   6/8   ♪ = 150",
 "credit": "Invented example",
 "slides": [{"tag": "VERSE 1", "badge": "Verse 1",
             "systems": [{"cells": [...], "en_line": "Morning light shows us the way"}, {...}]}]}
```
A cell is `{"bar": true}`, `{"dash": true}` (held beat), or a note
`{"pitch": "5", "up": 1, "down": 0, "dur": "8.", "tie": false, "cn": "我", "en": "We"}`:
`dur` ∈ 16, 8, 8., 4, 4., 2; `up/down` = octave dots; `tie` = arc to the next note; `cn: "~"` = melisma
(no new syllable, draws an extension line). `en` per syllable, or a whole `en_line` per system when the score
has no syllable alignment. Up to two systems per slide.

## Case 0 (preferred): approved score from the lyric translator
The singable-lyric-translator skill hands over its reviewed `score.mei` (handoff contract in its
`references/score-handoff.md`). There: `python scripts/handoff.py check score.mei --require-approved`, then
`python scripts/handoff.py events score.mei events.json`. Here: `type: jianpu, handoff: events.json,
score: score.mei`. Pitches, octave, accidentals (`#4`, `b7`), durations, ties, melisma, sections in sung
order and both lyric lines come from the events; this skill only decides line and slide breaks (phrases end
at rests ≥ 1 beat and at every section boundary, then the same DP as below). Tuplets and 32nd notes are
refused (not drawable yet).

## Case 1 (fallback): score PDF with jianpu + CN + EN rows (e.g. The God We Love V6.5)
```
python3 $S/make_song.py score.pdf --dump                      # check extraction
python3 $S/make_song.py score.pdf --title 我们所爱的神 --en-title "The God We Love" \
    --key "1 = B♭   4/4   ♩ = 82–84" --credit "…" -o the-god-we-love.song.json
```
`jianpu_extract.py` reads digits (Times font), underlines (duration), octave and augmentation dots, ties,
barlines, Noto CN lyrics and EN words (hyphen rectangles), and section labels like `VERSE 1 · 主歌一`.
`song_from_score` splits the song into phrases (rests ≥ 1 beat), then cuts over-wide phrases with a DP
over cut points: rest 0, held/tied note 1, pickup 2.5, barline 3, mid-word 20, +0.3 per line, max 12.6 in.

## Case 2: overlay PDF (jianpu stamped over an engraved staff score), repeats, voltas, D.S.
`jianpu_overlay.py` reads only the overlay layer (font `AAAAAA+TimesNewRomanPSMT`, underline width 0.42,
barline width 0.35, stroke-only arcs width 0.4) and ignores the re-stamped staff and lyrics.
```
python3 $S/jianpu_overlay.py score.pdf      # page, y, label, measures
```
Select the required measures from each returned row by page, y-coordinate and measure index. In a
per-song script, assemble the selected measures in sung order, including pickups, alternate endings and
D.S. or coda jumps. Assign the approved text one system per lyric line. Count Chinese syllables against
sounding note slots after excluding rests and melisma continuations. If the counts differ, recheck the
measure selection and line breaks before generating the JSON.

## Checks before building
- Print the slide summary (badge + lyric per system) and read it against the user's lyrics.
- Section tags follow how the song is sung: a "bridge" that is really a fourth verse → `VERSE 4`; final
  repeated choruses → `CHORUS` (badges dedupe to plain "Chorus").
- Render the jianpu slides and zoom in on one: dots above/below, underlines, ties, dashes.
