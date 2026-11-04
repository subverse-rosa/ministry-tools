# Song library

One folder per song. Shared users see only the top level; production files sit in one subfolder.
Details and checks: `delivery.md`.

```
诗歌/
  有一个福音/
    有一个福音（简谱）.pptx        public deck (the one to show)
    有一个福音（乐谱）.pdf         public score
    说明.txt                      one paragraph for shared users
    制作资料（勿改）/
      music/                    ← singable-lyric-translator
        score.mei                 reviewed encoding (notes, zh/en lyrics, sections, sung order, version/status)
        events.json               `handoff.py events score.mei events.json` (re-export after every score change)
      slides/                   ← worship-slides
        song.yaml                 profile + `{type: jianpu, handoff: ../music/events.json, score: ../music/score.mei}`
      records/                  optional review or provenance notes
  _archive/                     superseded decks and packages (moved, never deleted)
```

Songs that never went through the translator (hymn decks, PDF-extracted songs) keep their public files
and a production folder with the source PDF in `source/`; the check lists their decks as "no handoff".

## Revising lyrics
1. Translator: change `score.mei`, raise `lyric-version`, keep `lyric-status` honest, `handoff.py check`,
   re-export `events.json`, regenerate the score PDF.
2. Here: `python3 scripts/check_library.py 诗歌` →
   - `current`: nothing to do;
   - `EXPORT-OLD`: score changed but `events.json` was not re-exported (step 1 incomplete);
   - `STALE`: rebuild the deck with `build_service.py`, new name; move the old deck to `_archive/`;
   - `EDITED`: someone typed into the deck; the fix goes into `score.mei`, then rebuild;
   - `MISSING`: a recorded file moved; rebuild from the current paths.
3. `python3 scripts/check_delivery.py 诗歌` confirms the layout and rebuilds every yaml.

`_archive/` folders are skipped by both checks. The checks only read files.
