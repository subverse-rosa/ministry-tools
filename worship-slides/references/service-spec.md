# service.yaml

All file paths are relative to the yaml. Top level:

| key | meaning |
|---|---|
| `template` | the weekly template `.pptx`. Optional: without it the deck is a plain 16:9 file (song-only decks); `template` steps then fail |
| `layout_slide` | template slide whose layout new slides use (a plain one; 6 in the 2026 template). Omit to use a layout named Blank / 空白 |
| `profile` | colour profile key from `assets/styles.json` (`--profile` on the command line overrides) |
| `service` | list of steps, in order. Each step adds one or more slides |

## Step types

### `template` — reuse template slides
```yaml
- {type: template, slide: 32}                         # restyle to the profile (default style: dark)
- {type: template, slide: 32, text: 开始祷告, size: 138}  # copy a cover and swap its title
- {type: template, slide: 20, style: blank}           # plain dark ground (separator)
- {type: template, slide: 40-43, style: keep}         # untouched: photos, posters, QR, announcements
- {type: template, slide: 1, resize: {76: 68}, keep_transition: true}
```
- `slide`: number, range `40-43`, or list `"40,42"`. A slide used twice is copied automatically.
- `style: dark` removes full-bleed photos, applies the profile gradient, strips glow/outline, turns template
  yellow (English) into the profile `en` colour and everything else cream. Text is not changed.
- `style: keep` also pins the slide's theme colours, so the page looks exactly as in the template.
- `resize` maps point sizes (`76 → 68`) for a cover whose text no longer fits.
- `keep_transition: true` keeps the template's own transition (序乐 reveal, QR auto-advance).
- Any step may set `transition: cut` or `transition: fade` to override the default (sung and read slides cut,
  everything else fades), e.g. 阿们颂 is a template cover but is sung, so it cuts.

### `reading` — scripture, responsive reading, creeds, catechism, prayer items
```yaml
- type: reading
  header: 认罪               # 环节 name in the band
  suffix: （新译本）          # appended to the auto reference
  source: 海德堡要理问答 第一问  # replaces the auto reference ("" = none)
  align: left                # or center (creeds)
  gap: 0.35                  # paragraph gap in em (creed lines: 0.1)
  size: 44                   # body size; do not go below 44 without asking
  items:
    - {role: 主席, ref: "诗 95:7b", text: （放入已确认的经文）}
    - {role: 会众, ref: "林前 10:3", text: （放入已确认的经文）}
    - {role: 齐, src: 比利时信条 第 23 条, text: …}   # non-scripture source shows in the reference
    - {bold: true, text: 1.为祷告：}
```
- `ref` = `<short book> <chapter>:<verse>` (verse may carry a/b). The verse number is shown as a superscript;
  override with `num`. The header reference is built from all items (`诗 95:7b-11；林前 10:3-6`) and is the
  same on every page.
- `role`: usually 主席 / 会众 / 齐 (齐声 is shown as 齐); any other label (牧师, 领, 众 …) is shown exactly as
  given. The label shows at the top of each page and wherever the speaker changes.
- Pages are filled as far as the size allows and then evened out; a verse never splits across pages. A header
  too long for one line wraps to a taller band automatically.

### `hymn` — an existing hymn deck (`.pptx`)
```yaml
- {type: hymn, file: holy.pptx}                    # title page read from its first slide
- {type: hymn, file: s.pptx, title: 我知所信是谁, number: 赞美诗 123, credit: …, title_page: true}
```

### `jianpu` / `lyrics` — generated song slides
```yaml
- {type: jianpu, handoff: ../music/events.json, score: ../music/score.mei}   # approved score (preferred)
- {type: jianpu, handoff: rehearsal.events.json, allow_draft: true}           # rehearsal only
- {type: jianpu, song: there-is-one-gospel.song.json}
- {type: lyrics, song: one-gospel.lyrics.json}
```
`lyrics` JSON: `{"title", "en_title", "credit", "tags": ["VERSE 1", "CHORUS", …],
"sections": [["1.", [["中文行", "English line"], … up to 4]], …]}` — one slide per section. Optional:
- `"section_continuations": [{"section_index": 8, "continues_section": 7}]` (0-based): that section is the
  tail of the one before it (a song's final line after the last chorus): same background, no badge of its
  own, lines centred; badge numbering skips it.
- `"title_page": false`, or `title_page: false` on the step: no title page (e.g. the second song of a
  medley); the credit then goes on the song's first and last slides.
Page numbers always count one song only (`n/N` of that song), so a song can be removed from or reused in
another deck without renumbering.
`jianpu` JSON comes from `make_song.py` or a per-song script (see `jianpu.md`).
`handoff` is the lyric translator's `handoff.py events` output (`schema: lyric-handoff/1`). With `score`, the
build refuses an events file exported from an older score. `lyric-status: draft` is refused unless
`allow_draft: true`. The song's provenance is stored in the deck for `check_library.py`.

### `cover` — a 环节 cover generated in the profile style
```yaml
- {type: cover, text: 圣餐}
- {type: cover, text: 儿童信息, subtitle: Children's Message}
- {type: cover, text: 洗礼与坚信礼, size: 120}
```
Same look as a restyled template cover: profile gradient, centred cream title with a faint shadow. Size is
138pt (the template's cover size) and shrinks automatically for long titles (6 CJK characters fit at 138pt;
never below 72). Use it when the template has no cover for that 环节; otherwise reusing the template cover
(`type: template` with `text:`) keeps the church's own layout.

### `image` / `blank`
```yaml
- {type: image, file: cover.png}     # full-bleed, e.g. the sermon cover from the speaker
- {type: blank}                      # new dark separator slide
```
