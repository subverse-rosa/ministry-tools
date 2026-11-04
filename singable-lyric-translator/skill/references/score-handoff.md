# Projection handoff (reviewed MEI → slides)

Use when an approved score is handed to a projection/slides tool. The handoff is the
reviewed MEI itself, one file: no second lyric copy. Projection tools read it (or the
`events` JSON derived from it) and never edit lyrics; corrections return here, get a
new lyric version and a new check.

## Required in the MEI

```xml
<meiHead>
  <fileDesc>
    <titleStmt>
      <title xml:lang="zh">中文歌名</title>
      <title xml:lang="en">English Title</title>
    </titleStmt>
    <pubStmt><availability><useRestrict>Words &amp; Music: … · © … · CCLI …</useRestrict></availability></pubStmt>
  </fileDesc>
  <extMeta>
    <handoff xmlns="urn:singable-lyric-translator:handoff:1"
             lyric-version="1.3" lyric-status="text-approved"
             tonic="Bb3" scale="major" octave-shift="0" key-label="1 = B♭　4/4　♩ = 82"/>
  </extMeta>
</meiHead>
```

| Attribute | Meaning |
| --- | --- |
| `lyric-version` | The ledger's version of the Chinese/English underlay in this file. |
| `lyric-status` | `draft`, `text-approved` (user approved the wording) or `performed` (a real sing-through of these lyrics happened). Export never upgrades it. |
| `tonic`, `scale`, `octave-shift` | Numbered-notation reference, same convention as score production (movable 1; minor uses tonic=1). |
| `key-label` | Optional display text for slides (key, meter, tempo). |
| `staff`, `layer` | Guide voice, default 1/1. |
| `zh-verse`, `en-verse` | Verse numbers of the Chinese and English lines, default 1/2. |

## Sections and sung order

- Every measure belongs to exactly one `<section label="…">`; labels start with
  Verse, Pre-Chorus, Chorus, Bridge, Ending, Tag, Intro, Interlude, Outro or Refrain
  (`Verse 1`, `Chorus`, `Bridge 2`). Labelled sections do not nest.
- Stanzas with different words are separate sections (written out). A section reused
  in the route sings the same words every time.
- With repeats, voltas or a reused chorus, add one
  `<expansion xml:id="perf" type="performance" plist="#v1 #ch #v2 #ch"/>`; plist items
  are labelled sections or `<ending>` elements (an unlabelled ending takes the
  previous item's label). Without an expansion the route is document order, and any
  repeat barline or ending is an error rather than a guess.

## Lyric attacks

On the guide layer: a sung note starts a Chinese syllable unless it continues a tie
(`<tie>` or `@tie`) or follows a syllable with an extender (`con="u"`, melisma). A tied
continuation carrying a new syllable, a sung note with no syllable and no extender,
lyrics on rests, ties between different pitches, and `mRest`/`space` in the guide
layer are reported. English may differ in attack count; it is carried as given.

## Commands

```sh
python scripts/handoff.py check score.mei                     # summary + problems, exit 1 on any problem
python scripts/handoff.py check score.mei --require-approved  # also fail on lyric-status=draft
python scripts/handoff.py events score.mei events.json        # sung-order JSON for slide tools (new file only)
```

`events` JSON (`schema: lyric-handoff/1`): titles, credits, key label, lyric version and
status, source SHA-256, and `sections` in sung order → `measures` → `events` with
`number`/`octave`/`alter` (0 = rest), `duration` and `actual_duration` (quarter notes),
`underlines`/`dot`/`dashes`, `tie_next`, `continuation`, `melisma`, `zh`/`zh_con`,
`en`/`en_con`. Slide tools record `source_sha256` and `lyric_version` to detect stale
decks.

A passing check means the encoding satisfies this contract. It does not certify the
melody against its source, Chinese quality, approval decisions or real singing.
