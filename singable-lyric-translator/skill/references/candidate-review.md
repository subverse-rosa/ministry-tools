# Candidate review and user decision ledger — v1.7

Line records require stable ID (e.g. V2-L01), source relation, baseline wording, candidates, count, mapping status, semantic and musical tradeoffs, user decision, and evidence. An accepted wording remains invariant across repeats unless explicitly reopened. Do not infer consent from a recommendation or from the generic instruction to continue.

## Standard pass

Identify only the most material faults; for each provide old → proposed, reason, and whether source score supports the rhythmic claim. Deliver text-only lyrics by default. An explicit score request routes separately to [score production](score-production.md); it does not change approved lyric decisions.

## On-demand Deep Review

1. Global semantics and speech acts.
2. Native Chinese lyricist independently proposes a small number of meaningful alternatives.
3. Musical adapter audits score-grounded allocation and costs; do not manufacture notes.
4. Adversarial critic challenges improvements, including restoring original lines.
5. Consolidator reconciles ledger, locks accepted lines, checks hooks and versions, and stops when no supported improvement exists.

Report separate statuses: text-approved, mapped, score-checked, sing-through-tested. User choice cannot substitute for an actual performed test.

## Text delivery tests

- Full Chinese lyrics with all verse/chorus repeats and final coda.
- Bilingual Chinese-first line alignment, preserving complete confirmed text.
- No invented time codes, SRT/LRC or engraved PDF unless newly authorized as an independent task.
