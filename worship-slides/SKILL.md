---
name: worship-slides
description: Builds the weekly Sunday-service PowerPoint (主日崇拜 PPT) from the church's weekly template plus this week's flow, scripture (新译本), creeds, hymn decks and jianpu (简谱) scores, in one of several LED-friendly colour profiles. Use when the user asks to make or update 主日崇拜 slides, 崇拜PPT, worship slides, lyric or 简谱 slides, responsive-reading (启应) slides, or to change the service colour profile (色系).
metadata:
  version: "0.4.2"
---

# 主日崇拜 slides

Turn the church's weekly template `.pptx` and this week's content into a finished deck. Everything is driven
by one `service.yaml`; `scripts/build_service.py` does the slide work. Read slides (读) are dimmed parchment;
sung slides and section covers (唱 / 封面) use the chosen dark profile; announcement and image pages stay exactly
as the template has them.

This skill is self-contained and agent-neutral (Claude, Codex, or any agent that can run a shell).
`$S` below means the `scripts/` folder beside this SKILL.md; resolve it to an absolute path first.
Before the first build run `python3 $S/check_env.py`: it lists missing Python packages
(`pip install -r requirements.txt`, add `--break-system-packages` on managed Pythons) and whether LibreOffice
is available for previews. Without LibreOffice, build anyway and tell the user previews were skipped.

## Workflow

1. **Collect the inputs.** The user usually gives them in chat, in pieces:
   - the weekly template `.pptx` (e.g. `主日崇拜模板.pptx`): base deck with covers, 讲员PPT
     placeholder, offering QR, announcements;
   - the service flow (often a screenshot): order of 环节, who reads what (主席 / 会众 / 齐);
   - scripture references (新译本 unless told otherwise), creed / catechism texts;
   - songs: imported hymn `.pptx`, jianpu PDFs, or plain bilingual lyrics; the sermon cover image;
   - the colour profile (default `oxblood-library`; see `assets/palettes.html`).
   Ask only for what is missing. Never invent scripture, creed or lyric text.

2. **Map the template.** Run `python3 $S/inspect_template.py template.pptx` and render thumbnails
   (`soffice --headless --convert-to pdf`, then `pdftoppm -r 20`). Note which slide numbers are covers to reuse,
   blanks, photo pages and announcement pages. Numbers shift week to week; check every time. A 环节 with no
   cover in the template gets a generated one (`type: cover`).

3. **Get the texts.** Scripture: follow `references/scripture.md` (CNVS, short book names, verify with the user).
   Put role labels on items exactly as the flow says (主席 / 会众 / 齐, or whatever the flow uses, e.g. 牧师);
   a 宣召 read by the chair alone has no labels.

4. **Prepare songs** (`references/jianpu.md`). Music and lyrics are decided before slides, not here:
   - **preferred:** an approved score from the singable-lyric-translator skill (its reviewed `score.mei`
     plus `handoff.py events` JSON) → `type: jianpu, handoff: …, score: …`. Take notes and lyrics as given;
     drafts are refused; a stale export is refused. Wrong lyrics go back to the translator, never edited here;
   - hymn deck `.pptx` → `type: hymn` (gets a title page, recoloured, text untouched);
   - fallback, songs not yet through the translator: jianpu PDF with CN + EN under the notes → `make_song.py`
     → `type: jianpu, song: …` (the user checks every slide);
   - jianpu overlay PDF / repeats to unfold → follow the measure-selection workflow in `references/jianpu.md`;
   - lyrics only → song JSON with sections → `type: lyrics`.
   Print the slide-by-slide summary the tools give and check every line break lands on a phrase.

5. **Write `service.yaml`** in a working folder next to the assets (format: `references/service-spec.md`;
   see the runnable mini-service in `examples/handoff/service.yaml`). Show the user the flow as a short
   list (环节 → source → slide count) before building when anything was ambiguous.

6. **Build and check.**
   `python3 $S/build_service.py service.yaml "<DDMMYYYY> 主日崇拜PPT - <堂>.pptx" [--profile …]`
   Render to PDF and look at a contact sheet of every slide: overflow on reading pages, phrase breaks on song
   pages, cover text, announcement pages identical to the template. LibreOffice has no KaiTi, so preview glyph
   spacing and stanza-number overlap can look wrong; judge those only from the real PowerPoint, and never report
   them as defects without checking the slide XML.

   A single song as its own deck (for the song library) needs no template: a yaml with just `profile` and one
   `jianpu` step gives a small plain 16:9 file.

7. **Deliver** the deck where the user keeps outputs (ask once if unknown; never overwrite a file the user has
   open or an earlier version: add v2, v3 …). Keep `service.yaml`, song JSON and any per-song script in a
   `_build` subfolder beside the deck so next week starts from them. Mention what
   still needs a human: 公祷事项 text, 讲员PPT, last-minute announcements.

## Song library

Folder convention, one folder per song: `<歌名>/music/` (owned by the translator: `score.mei`, events JSON,
score PDF) and `<歌名>/slides/` (owned here: the song deck and its yaml); see `references/song-library.md`.
Decks built from a handoff carry provenance (score hash, lyric version) as a custom document property.
`python3 $S/check_delivery.py <folder>` checks layout and rebuilds every yaml against its delivered deck (`references/delivery.md`);
`python3 $S/check_library.py <folder>` reports each song as current / STALE / EXPORT-OLD / EDITED / MISSING;
run it after lyric revisions and rebuild only what it flags. `python3 $S/selftest.py` checks the whole path
with an invented song.

## Rules that are already decided

Full list with reasons: `references/design-rules.md`. The ones that are easy to break:

- The old template's font sizes are a floor: reading body 44pt, KaiTi never below 36, Cambria never below 26
  (header source line 30pt and page numbers 22pt are agreed exceptions).
- Reading pages: header band on top = 环节 (40pt bold accent) `　｜　` whole-passage reference (30pt, short book
  names, `（新译本）` suffix); no footer; fill each page as far as the floor allows; never split a verse.
- 【主席】【会众】【齐】 labels in the same colour and weight as the body; a new speaker gets a little space above.
- Songs, song title pages, hymns and reading pages cut (no transition); covers, blanks and image pages fade.
  Slides marked `keep_transition` (序乐, offering QR with its 5 s auto-advance) keep the template's own.
- Section badges are simple English: Verse 1/2/3, Chorus, Bridge, Ending, Tag. A sung verse that the score
  calls a bridge but is really a fourth verse is `VERSE 4`.
- Don't edit text on template cover slides or imported hymns (wording, punctuation); only restyle them.
- The delivered deck must be exactly what `build_service.py` makes from the delivered yaml/JSON. Do not
  post-edit generated slides or copy `styles.json` into a song folder; if the skill cannot express something
  (a layout rule, a colour fix), stop, say so, and change the skill instead.
- Colours and fonts end up as theme slots (`+mn-ea` KaiTi, `+mn-lt` Cambria), so the user can re-skin in
  PowerPoint. Edit `assets/styles.json`, never hard-code colours.

## Colour profiles

`assets/styles.json` is the single source of truth. After adding or changing a profile, regenerate the
reference page: `python3 $S/make_palette_page.py assets/styles.json assets/palettes.html`. A new dark profile
needs `verse_bg`, `chorus_bg`, `zh`, `en`, `accent` (optional `bridge_bg`, `cover_top`, `name_zh`, `name_en`,
`use`). Check contrast on the page: CN ≥ 12:1, EN ≥ 7:1, accent ≥ 5:1 against `verse_bg`. The panels are LED,
so prefer deep grounds, no glow or outline effects, strokes ≥ 1.5pt.
