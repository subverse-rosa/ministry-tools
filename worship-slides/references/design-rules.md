# Design rules (agreed with the user, Oct 2026)

## Display
- The church projects on an **LED panel**, not a projector. Deep grounds, no text glow / outline / heavy
  shadow (they read as haze), lines ≥ 1.5pt, jianpu underlines and ties 2pt. Parchment is dimmed (#D7C7A9) so
  a full white-ish page does not glare. Parchment brightness, jianpu strokes and gradients
  were accepted on the LED panel (Oct 2026, provisional); adjust `styles.json` if problems show up later.

## Two colour worlds
- **读 (reading)**: parchment ground, ink #211F1A, verse numbers #5F513D, header band in the profile's
  `verse_bg` with accent + cream text. Same for every profile.
- **唱 / 封面 (singing, covers, blanks)**: the chosen dark profile. Verse = `verse_bg`, chorus/ending/tag =
  `chorus_bg`, bridge = `bridge_bg`. Covers get a vertical gradient `cover_top` → `verse_bg`.
- The switch between the two worlds is itself the cue for the congregation that the mode has changed.
- The profile is not limited to a season (oxblood is not only for communion/Good Friday).

## Fonts and sizes
- PowerPoint: KaiTi (zh) + Cambria (en), set as theme fonts. Google Slides (future): Noto Serif SC +
  Cormorant Garamond. Fonts belong to the export target, not to the colour profile.
- The old template's sizes are the floor; only go smaller with the user's agreement.
  - reading body 44pt; header 环节 40pt bold; header reference 30pt (not read aloud, so below 36 is fine);
    page numbers 22pt; credits 16pt.
  - lyric slides: CN 60pt, EN 32pt bold italic; jianpu digits 40pt; song title on pages 40pt bold, key 26pt.
  - covers keep their template size (138pt titles); KaiTi has no real bold, so cover titles ≥ 96pt are unbolded.
  - 序乐 (template slide 1) 76 → 68pt so six lines fit at 83% line spacing.

## Reading pages
- 环节 + source go in the top band; no footer; the whole passage's reference on every page; book names short
  (诗, 林前, 罗, 弗, 尼 …); `（新译本）` suffix for scripture.
- Fill each page as far as the size allows (context beats one-speaker-per-page); never split a verse; even the
  pages out so there are no near-empty last pages.
- 【主席】【会众】【齐】 in brackets, same colour, font and weight as body text. No colour coding of roles
  (the user edits these later; one colour keeps that simple).
- Creeds (齐) centred, tight line gap. Catechism: 主席 asks, 齐 answers.

## Songs
- Header: section badge left (Verse = outline, Chorus = solid accent, Bridge = soft), song title centred,
  key right. Badge labels in plain English; numbers only where they disambiguate.
- Jianpu lines break at musical phrases (rests, held notes, pickups), never mid-word; two systems per slide.
- First and last song slide carry the credit line (CCLI etc.); every song slide has `n/N` counted within
  that song only, also in medleys, so songs stay removable and reusable.
- A song's closing line that continues the last chorus is a continuation, not a Tag: no badge.
- Hymn decks from outside: text, punctuation and stanza numbers untouched (external material); only recolour.

## Transitions
- Songs, song title pages, hymns, readings: no transition (instant cut, operator-friendly).
- Covers, blanks, image pages: 0.75 s fade.
- Template slides whose own transition matters keep it (序乐 reveal; offering QR keeps its 5 s auto-advance).
- 阿们颂 is sung, so it cuts too (`transition: cut` on its template step).

## Editing friendliness
- All colours become theme slots (dk1 ink, lt1 cream, dk2 verse_bg, lt2 parchment, accent1 chorus_bg,
  accent2 bridge_bg, accent3 accent, accent4 verse-number grey, accent5 cover_top, accent6 en), fonts become
  theme fonts. Changing the theme in PowerPoint re-skins the deck.
- `keep` pages (posters, QR) have their theme colours pinned first, so re-skinning never changes them.

## Content conventions
- 宣召 is read by the chair alone (no labels). 认罪 is responsive. The flow decides who reads what each week.
- 公祷事项 is updated by hand by the user; keep the template text unless given new items.
- Announcements (报告) stay as the template has them.
