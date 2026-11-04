# Changes

## 1.9.0 - 2026-10-28

- Add the projection handoff: a reviewed MEI with titles, credits, a namespaced
  handoff record (lyric version/status, numbered reference), labelled sections and an
  optional performance `<expansion>` is the single file handed to slide tools.
- Add `scripts/handoff.py` (standard library): `check` validates metadata, sung route,
  lyric attacks, ties and approval status; `events` writes sung-order numbered events
  with Chinese/English syllables as JSON, refusing existing paths and failing encodings.
- Export never raises `lyric-status`; slide tools must not edit lyrics.

Contract checks do not establish melody/source identity, Chinese quality or real singing.

## 1.8.0 - 2026-10-26

- Add source intake from song/YouTube links: authoritative source discovery,
  edition matching, provenance and explicit unverified/conflicting evidence.
- Add opt-in bilingual staff/numbered-notation production with two routes:
  reviewed MEI/MusicXML re-engraving and original PDF system-strip preservation.
  Include configurable layout/profile, shared degree/duration conversion,
  rendering helpers and invented examples. No automatic transcription claim.
- Move development validation/build tools into the public repository, consolidate
  repeated count checks, make private historical replays optional, and add
  Windows/Linux CI plus a separate optional-renderer integration job.
- Retain Adaptive analysis, approval of individual rhythm changes, accepted-lyric
  invariants, native Chinese checks, on-demand Deep Review and honest M0-M4 status.

Package construction and rendering tests do not establish fresh model behavior,
cross-platform installation acceptance, real-score accuracy or real singing.

## 1.7.2

Previous published runtime and ZIP remain available in the v1.7.2 GitHub Release.
