# Rhythmic Capacity Mapping — v1.7.0

Read after the essential rules in SKILL.md when a score/map is available. This is a human/agent review protocol with an optional consistency checker, not automatic score transcription.

## Map before writing lyrics

1. Identify the score edition, page/system/bar, voice, meter, tempo if known, and beat unit. Locate the exact source lyric underlay. Preserve pickups and repeats/alternate endings as separate evidence where different.
2. Transcribe the relevant phrase manually into exact beat coordinates. Include every rest, dotted duration, tuplet fraction, tied continuation, breath and phrase boundary. Use negative beats for pickups if useful. Strong/weak labels and pitch/contour require score evidence; never infer them from word stress alone.
3. Read syllable underlay independently of notation grouping: a slur may span several syllables; a tied note has no fresh attack; an evidenced melisma can cover several pitches with one syllable. Mark unclear OCR or underlay pending. Reconcile English syllable counts with the source underlay; a pronunciation difference is not silently a new target budget.
4. Establish baseline attacks and semantic regions (hook, condition, quotation, command/response). Default to Adaptive *analysis* with reliable score/map; Strict only when exact underlay is explicitly required. Adopting a change always requires an accepted decision. Adaptive proposes a specific alternative allocation, with duration, tempo/diction risk and phrase-boundary cost. No universal extra-character allowance follows from “two beats available”.
5. Draft only after the applicable map is ready, or explicitly draft provisionally at B/C. Align Chinese words and meaning units to regions; then run native Chinese, semantics, counts and local singing checks. Actual feasibility needs a sing-through.

## Optional JSON helper

Run `python scripts/check_rhythm.py references/capacity-example.json`. No third-party packages. The example is an invented same-pitch phrase, not a real song analysis.

Top-level fields: `schema_version: 1`, `map_version`, `mode` (Strict/Adaptive/Recomposition), `beat_unit`, `phrases`, `ledger`. Recomposition also requires a nonempty `authorization` referencing an explicit user request and `original_map_version` distinct from `map_version`; events describe the new version, not evidence that the original melody was preserved.

Each phrase has a unique `id`, traceable `source`, `meter`, explicit `uncertainty` (use "none identified" if reviewed), `events`, `boundaries`, `baseline_slots`, `target_slots`; optional `supplied_count` and `expected_target`. Beat values are integers or rational strings such as `"3/2"` or `"-1/2"`, never binary floats. Coordinates are local to each phrase. Event spans are ordered, contiguous and positive; encode all silence as rest events. Pitched events have `kind: "note"`, a consistently spelled `pitch` token (e.g. C4), `stress: "strong"/"weak"`, and optional boolean `tie_from_previous`. Rest events have `kind: "rest"`. All spans use `start`, `end` with end excluded.

Slots are spans of one syllable, covering all pitched time and no rests, without crossing a listed hard boundary. Baseline slots must start at note attacks. Target slots can divide sustained untied notes in Adaptive. A tie chain cannot be subdivided. A merge in Adaptive can remove original attacks only across consecutive same-pitch notes; different-pitch re-underlay belongs to a separately reviewed Recomposition proposal under this conservative protocol. If a source melisma already contains different pitches, retaining it is fine. Pitches are opaque tokens, not parsed intervals; consistent spelling is required.

For every adopted non-Strict change, add an accepted ledger entry whose `baseline_slots` and `target_slots` exactly match that phrase's arrays. Keep drafts/proposals separately until accepted. `before`/`after` explain the change; the arrays make its allocation checkable. An accepted record is a **declaration**, not proof of human authorization: the agent must trace it to the conversation. The helper checks spans, coverage, counts, tie constraints, mode and matching decision records. It does not check a score image, pitch accuracy, tempo, syllable diction, word boundaries, meaning, Chinese naturalness or a performance, and cannot pass any M gate.

`check_counts.py` remains backward compatible: `--slots 8,6,8,6 draft.txt`, `--stdin`, `--variants candidates.txt`. Default filtering skips labels and English-only echoes while retaining Chinese one-character and mixed lines. Use `--raw-lines` for plain lyric files to bypass label heuristics. These are CJK character counts, not full pronunciation counts. Latin/numerals/non-Han are ignored; annotate their actual sung pronunciations manually. Exit 0 for variants only means the comparison ran; individual candidates can still fail. Count equality is not singability.

## Decision ledger template

| ID / phrase | Source, uncertainty | Mode; before → after | Alternatives and costs | Recommendation | Status; owner/reason |
|---|---|---|---|---|---|
| D01 / V1.1 | p1/bar1; underlay reviewed | Adaptive; 1 attack → 2 | Keep melisma: less text; split: faster diction | Split, subject to sing-through | proposed; awaiting user |

JSON entries use `id`, `phrase`, `source`, `uncertainty`, `mode`, `before`, `after`, `alternatives`, `semantic_cost`, `musical_cost`, `recommendation`, `status`, `decision_owner`, `reason`, plus allocation arrays for adopted rhythm changes. Textual decisions use the same ledger without needing musical arrays. `superseded` entries need `superseded_by`; never erase accepted history. Record evidence that justified reopening. Exact text, term and hook decisions remain binding until superseded.

## Evidence report template

| Gate / scope / version | Status | Evidence; reviewer/method | Unresolved / next action |
|---|---|---|---|
| M0 | passed/pending/blocked/not_applicable | source, input level, mode, terms | missing input |
| M1 | … | location, manually reviewed map, count comparison, ledger IDs | unresolved rhythm |
| M2 | … | semantic relations + structure audit | P0 blockers |
| M3 | … | native Chinese read, counts, local tone/vowel checks where evidenced | provisional music subchecks |
| M4 | … | actual new-lyric sing-through: person, version, coverage, findings | 未经试唱验证 if absent |

A passed text subcheck may be reported while its cumulative gate is pending due to M1. B/C drafts need not wait for unavailable music, but M1/M3 music subchecks and M4 remain pending. Do not mark missing music as not_applicable merely to pass a singable-translation gate. For Chinese → English, Chinese tone/rhyme checks genuinely are not_applicable; language-neutral meaning/structure and count checks remain.

## Focused review scenarios

- Four written notes under one evidenced syllable: Strict capacity 1; never automatically 4. Adaptive splitting requires a specific accepted proposal and no tie violation.
- Eight English syllables with a supplied score showing an uncertain pickup: M1 pending; ask about the pickup. Do not invent eight Chinese attacks.
- One long untied note divided into two attacks: Adaptive may model it; tie chain divided the same way is blocked. Internal consistency says nothing about tempo feasibility.
- Equal character count but “将我希望于你” as a forced calque: native pass must flag it and seek natural wording; preserve the referent/action when changing syntax.
- No new-lyric recording or sing-through: M4 pending even if all text checks pass. Export honestly as a text-reviewed draft.

## Musical adaptation costs (v1.6)

For each proposed change, cite the score location, exact old/new attacks and durations, original vs target count, word-boundary alignment, stressed words, long-note preservation, diction density, melody identity and an evidence level. Distinguish possible mathematical subdivision from a singer-approved result. An unverified beat/strong-note claim is labeled pending, not scored.
