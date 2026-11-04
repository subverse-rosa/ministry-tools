---
name: singable-lyric-translator
description: Translate English lyrics into singable Chinese (可唱级歌词翻译), audit lyric drafts, find matching score sources from a song or YouTube link, produce bilingual staff or numbered-notation PDFs when requested, and hand approved scores to slide tools. Preserve meaning, approved wording and melody evidence. Use for 歌词翻译, 倒字, 押韵, 双语五线谱 or 加简谱; not generic poetry rewriting without a melody.
---

# Singable Lyric Translator

**Version:** 1.9.0 (released 2026-10-28)

English → Simplified Chinese singable lyrics. Chinese → English: semantic and structural integrity still apply; only the slot-count module applies among the phonetic fitting checks (say so); Chinese tone/rhyme modules do not.

**This file is complete on its own and is the authoritative behavioral rulebook.** For detailed Chinese rhyme/phonetic examples, consult [Chinese prosody](references/chinese-prosody.md) when checking tone, vowel opening or rhyme. The summaries below are sufficient if that reference is unavailable. If code execution and the helper are available, verify counts with `scripts/check_counts.py`; otherwise count manually. Never claim that a helper was run when it was not. Supporting-file or execution availability does not change semantic/structural requirements.

## Workflow
Classify evidence and mode (M0) → score-first Rhythmic Capacity Mapping (M1, A/any supplied score) → map source architecture → draft the complete song → audit global semantics/structure (M2) → audit local singability and native Chinese (M3) → context pass → resolve genuine conflicts → export with evidence gates and performance status (M4). For a supplied Chinese draft, use targeted repairs. Recheck the global frame after local changes.

## v1.8 source intake and optional score production

**Route the actual request before drafting.** A song/YouTube link can begin source discovery: read [source intake](references/source-intake.md), search available authoritative sources, and compare the specific edition/arrangement. A URL or official publisher alone does not establish Level A, an exact recording match, or permission to adopt rhythm changes. Report what was actually opened/read/listened to. If browsing or audio tools are unavailable, disclose that and continue only within available evidence.

**Engraving is opt-in.** A request for bilingual staff, a notation PDF or adding 简谱 authorizes that delivery; it does not request a fresh translation or approve music/wording changes. Read [score production](references/score-production.md). Preserve approved lyrics and the decision ledger. Choose (1) reviewed MEI/MusicXML → staff / optional numbered guide / Chinese / English, or (2) preserve original PDF system strips and append a mapped numbered guide. Prefer the second for an existing satisfactory bilingual PDF; use the first when new lyric underlay/reflow is needed. Keep original files unchanged. Templates are configurable; the two previously successful styles are defaults, not a mandatory new design.

Accurate notation needs readable melody/rhythm evidence and a reviewed encoding or coordinate map; the user need not personally supply a staff score if a matching reliable source can be found. Chord charts, lyrics, note counts and an unexamined YouTube recording do not establish note durations or underlay. Where source evidence is incomplete, label a provisional transcription and its uncertain bars; do not deliver it as an exact original lead sheet. No automatic OMR/transcription is claimed.

Optional helpers: `scripts/engrave_score.py` uses Verovio and optionally a local Chrome/Edge/Chromium for PDF; `scripts/add_numbers.py` uses pypdf/reportlab and an explicit reviewed map. Their numbered conversion shares `scripts/notation.py`. Read the reference for prerequisites, commands, font setup and limits. Missing dependencies do not block text translation; explain what is missing before claiming a score was generated. Scripts check/render supplied data, never certify source matching, authorized decisions, Chinese quality or real singing. Visually inspect every rendered page and compare pitches, timing, ties/rests, repeats, lyric attacks and credits against the reviewed source before calling a score checked. Engraving success never passes M4.

**Projection handoff (v1.9).** When an approved song goes to slides/projection, the handoff is the reviewed MEI itself (one file, no second lyric copy): titles, credits, a handoff record with `lyric-version` and `lyric-status`, labelled sections and, for repeats, one performance `<expansion>`. Read [score handoff](references/score-handoff.md) and run `scripts/handoff.py check` until it reports no problems. `lyric-status` follows the ledger (`draft` / `text-approved` / `performed`) and is never raised by exporting; use `--require-approved` before a public handoff. Slide tools read the MEI or the `handoff.py events` JSON and must not edit lyrics: corrections come back here as a new lyric version.

## Step 0 — Classify input (always first)
| Level | User gave | May check | Must NOT claim |
|---|---|---|---|
| **A** | lyrics + traceable melody/rhythm/underlay evidence (readable score or reviewed map; counts may be derived) | checks supported by that evidence | automatic transcription or performed validation |
| **B** | lyrics + syllable counts | slots, core meaning, rhyme | tone–melody or high-note validation → write 未验证旋律 |
| **C** | lyrics only | estimated counts, meaning, rhyme | any beat/note facts → label fit **临时** and end with one line inviting counts/melody |

User supplies a Chinese draft → **audit mode** (below).
No melody to fit (plain poetic rewrite) → do not use this workflow: no cards, no labels.

## v1.7 modes, capacity and evidence gates

**Mode is independent of input level.** Default **Adaptive analysis** when a readable score or reviewed map exists; this is permission to compare proposed reallocations, **not authorization to adopt them**. Without rhythm evidence, draft provisionally and make no score-fit claim. **Strict** applies when the user forbids changing the original lyric underlay: preserve the established lyric underlay, onsets, durations, ties, rests and phrase boundaries. **Adaptive**: retain pitches, total phrase duration and hard boundaries; propose explicit local re-underlay, splitting a sustained note into repeated same-pitch attacks, or merging consecutive untied same-pitch notes. Each change needs a before/after allocation and an accepted ledger entry before adoption. Do not break a tie, consume a rest or cross a breath boundary. **Recomposition**: only on explicit user request for melody/rhythm changes beyond Adaptive; label 改编/重新作曲, version the new melody separately and do not claim unchanged-tune translation. Choosing a mode does not accept individual changes. No mode waives semantic/structural integrity.

**Score first, before drafting.** Inspect any supplied score before treating English syllable counts as capacity. A readable score may establish A without supplied counts if melody, underlay and relevant rhythm can be mapped; unreadable/partial notation does not automatically promote B/C. Record page/system/bar/voice, beat unit and meter. Distinguish source syllables, pitched events, original lyric attacks and proposed Chinese attacks. Map exact onset/duration (pickup, dots, tuplets, ties), rests/breaths, strong beats, pitch/contour, original underlay, melisma and uncertainty. A tie continues one sound; a slur alone does not prove one syllable. Neither note count, source syllable count nor total beats is a Chinese character budget.

Compute **baseline capacity** from evidenced lyric attacks. In Strict it is the target. In Adaptive show baseline → proposed capacity and every supported change. Do not invent a universal characters-per-beat ratio or maximum capacity. Missing evidence leaves M1 pending: ask for the needed passage/count/rhythm fact and, if useful, continue a B/C provisional text draft, never claim score fit. Expose and resolve discrepancies between supplied counts and score before locking targets.

The count rules below apply to the **adopted target allocation**. They do not freeze English syllable counts as an immutable Chinese budget: a supported, accepted Adaptive allocation replaces the target explicitly. Original counts and baseline stay in the ledger; an unexplained count change is still P0. At B/C, Adaptive can only be proposed until rhythm evidence supports it. In all modes a natural Chinese reading is required for M3; the priority ladder is not permission to pass broken syntax or meaningless filler.

**Native Chinese pass:** read Chinese without English; check complete syntax, natural collocations, referents, word boundaries at rests, semantic chunks at phrase boundaries, register, diction, filler/inversion forced by count and repeated hooks. Equal counts cannot excuse unnatural Chinese. Review contextual pronunciation of polyphonic characters, 儿化, light syllables, numerals, Latin words and non-Han sung material; character counting is not phonetic proof. Rephrase faithfully, then recheck count and global architecture. “Native checked” does not imply a human singer reviewed it.

**Decision ledger:** stable ID, phrase/location, issue, source/uncertainty, before → after, mode, alternatives, semantic/musical cost, recommendation, status (proposed/accepted/rejected/superseded), decision owner and reason. Retain accepted wording, terminology, hooks and rhythm changes. Reopen only for new evidence or user request; record why and the supersession link. Recommendations and silence are not acceptance. Existing “好”/proceed rules cover only recommendations actually presented. Audit suggestions remain suggestions until application is authorized. Three cards per reply; ledger and P0 blocker disclosure are not limited to three.

**M0–M4 are cumulative evidence gates, scoped per phrase/section.** Status = passed / pending / blocked / not_applicable, with evidence, reviewer/method and unresolved items. Missing evidence is pending; contradictory or failed evidence is blocked. No later gate passes while a required earlier gate is unresolved. A phrase-level pass never covers the whole song. Separate applicable text checks from pending music subchecks at B/C; provisional drafting/export is allowed without inventing a gate pass.

| Gate | Required evidence and honest claim |
|---|---|
| M0 — intake | Source/version, scope, A/B/C, mode, terminology, score/audio/count availability and limitations. |
| M1 — rhythm | A: traceable reviewed capacity map, resolved counts/phrase regions, accepted changes. B: supplied counts only, melody pending. C: estimates only, rhythm pending. |
| M2 — meaning/architecture | Referents, actions, negation, modality, quotation, hooks and parallelism audited across declared scope; no unresolved P0. |
| M3 — lyric craft | Counts/phrase placement, native Chinese, rhyme and contextual diction audited; tone/vowel/beat checks only where A evidence supports them. Script results prove only count/map consistency. |
| M4 — performed validation/release | Actual sing-through/listening evidence: performer/reviewer, lyric/map version, coverage, findings and resolved blockers/decisions. Without it export 文本审校稿/临时拟合，未经试唱验证. A recording of the original is not a sing-through of the new lyrics. User-approved text may be 文本定稿, never automatically music validated. |

Read [rhythmic-capacity.md](references/rhythmic-capacity.md) for the map schema, examples and evidence report. Optional `scripts/check_rhythm.py` checks a manually entered map; it does not read scores/audio or judge Chinese, tone, tempo feasibility or performance. The essential rules above apply without supporting files or execution.


## v1.7 translation craft and review control

**Native composition before literal compression:** after semantic architecture and rhythmic capacity mapping, independently draft natural Chinese sentences and a hymn/poetic register appropriate to the song. First read the Chinese without viewing English. Reject ungrammatical particles omitted only for count, calqued word order, concatenated nouns/verbs with unclear relations, and euphemisms that blur the source. Do not flag established doctrinal/liturgical expressions as unnatural just because they are non-colloquial. Prefer first-listen intelligibility; preserve legitimate ambiguity or poetic compression when justified.

**Candidate comparison (no false precision):** for genuinely competing faithful renderings, log source relations, native fluency, poetic voice, strong/weak slots, tone and vowel, repetition consistency, and adaptation cost. Give the musical evidence location when citing an accent or high note; otherwise label `unverified`. Candidates with count mismatch remain eligible for a *proposed* Adaptive mapping, never a verified one by assumption.

**Review mode:** normal reviews are targeted (preserve approved lines). The five-perspective Deep Review is **on demand only**: (1) semantics/architecture, (2) native lyricist/poetic voice, (3) score-grounded adaptation, (4) adversarial challenger who may restore the original, (5) consolidator comparing accepted decisions and evidence. Do not pretend separate agents performed independent reviews unless they actually did. Stop when no justified improvement remains. Record revisions with stable verse/line IDs; a user's approved lyric is text-approved, not sung-approved.

**Decision authority:** no silent change to previously approved choices or repeated hooks. New evidence may prompt a clearly labeled reopening request. `recommendation`, `proposed`, `accepted`, `rejected`, and `superseded` are distinct; the word “go” accepts only presented scope, not all unmentioned alternatives. A/B options are shown only where differences matter, with concrete reason and evidence level.

**Lyric-only delivery:** provide a complete Chinese text or bilingual line-by-line text when requested, observing the exact verse/chorus/bridge sequence and repeated text. Avoid inventing English originals. SRT/LRC, engraved score, and PDF output are outside this skill's default delivery. Clearly mark optional unverified rhythmic instructions; do not print an M4 pass without actual new-lyric sing-through evidence.

**Pre-delivery self-check (run before each delivery and in every review loop):** ensure (a) a nine-slot score does not automatically reject a ten-character native candidate under Adaptive; (b) an extra syllable without a mapped onset cannot pass M1; (c) ungrammatical same-count Chinese does not pass craft review; (d) approved hook and collective narrative voice do not silently change; (e) original audio does not pass M4; (f) no card offers an option the evidence cannot support; (g) wording the user accepted was not silently changed or re-flagged. See [native lyric craft](references/native-lyric-craft.md) and [candidate review](references/candidate-review.md) for optional deep analysis.

## Level A slot map (before any tone or vowel check)
For each line list slot → pitch, strong/weak beat, long/short, rests. First complete M1 capacity mapping below. A tie continues one sound; melisma is one slot only when underlay establishes one syllable over those notes. A slur alone does not establish a syllable boundary. Checkpoints: long strong slots, the section's peak note, line-final long notes, and the first slot after a rest. If the melody was read from an image or PDF, say so (音高由谱面图像读取，未经听觉验证) and recount every line against any supplied counts before relying on the map. A rest or breath must not split a two-character word (基｜督): re-voice so the word sits on one side; if no faithful fix exists, list it as 💡.

## Source architecture pass — before line drafting
Map the whole source before Stage 1: repeated hooks/refrains, parallel grammatical frames, recurring quotations/imperatives/responses, contrast sets, semantic progression and paired relations (crisis → refuge; command → response). Record who speaks, who acts on whom, negation, causation and modality. Identify repeated melodic regions only from supplied evidence; at B/C, textual architecture is checkable but melodic placement remains unverified/provisional.

Choose one reusable Chinese frame globally, then fill its variable slots. Identical source text + identical melody → identical Chinese. Parallel source text over parallel/identical melody → parallel Chinese syntax and slot structure, preserving the different meanings. Same melody alone does not require identical words. Review every occurrence after changing a hook.

**Hook efficiency:** prefer a natural, recognisable, semantically stable hook that uses enough slots for the referent and main action while leaving room for the variable contrast. Do not shorten by weakening the action or changing the referent. Compression priority: **referent → main action → variable contrast/condition → discourse form → optional subject/function word**. Repeated first-person 我 may be omitted when context preserves the speaker and this improves melodic structure; retain it when omission makes the speaker ambiguous, especially inside quotations.

**Phrase-level semantic slot mapping:** map source units to target regions, not merely a total count. Record hook/condition, quotation/reporting clause, command/response boundaries and their target slot spans. With a supplied 4+4 boundary, a four-slot hook plus four-slot condition preserves the architecture; a five-slot hook plus three-slot condition can have eight characters yet displace meaning. 4+4 is an example, not a universal meter. At B/C infer only a provisional textual segmentation, never claim verified beats.

**Discourse form:** preserve direct quotation, imperative, question, response and speaker attribution where the source repeats them. Punctuation alone is insufficient: the Chinese must still perform the same speech act. Do not convert repeated commands into narration or merge different speakers to save slots.

**Semantic relation integrity (P0, all input levels):** reject negation reversal, agent/patient reversal, speaker reversal, major causation or modality changes, and theological over-translation. Preserve scope and strength (cannot ≠ can; may ≠ must; result ≠ cause). A devotional context does not license adding conversion, regeneration, atonement or doctrinal certainty absent from the source: refreshed does not automatically mean reborn; run to Christ does not automatically mean conversion. Keep core terms and relations together, rather than merely mentioning the right nouns.

**Two-pass audit:** (1) global architecture and semantic relations across the whole song; (2) local slot fit, phrase placement, tone clash, mouth opening and rhyme. Audit a supplied draft with targeted repairs, not a wholesale retranslation. Recheck the global frame after local repairs. QA order: **semantic integrity → structural integrity → slot fit → tone clash → mouth opening → rhyme**. Clear source-pattern loss is P0 structural integrity; an unexplained mismatch with the **adopted** target allocation is P0; a baseline mismatch in Adaptive remains an unmapped proposal (estimated C counts remain provisional). Tone clash is P0 only under the existing Level A credible-mishearing gate; mouth opening and chorus rhyme remain P1.

Correct clear semantic errors directly and list them under 已自动处理; a reversed meaning is never an acceptable A/B option. Use cards only for genuinely unresolved faithful alternatives or a disclosed fitting tradeoff. The three-card budget never permits unresolved P0 errors to disappear: repair them or explicitly mark the draft provisional and list the remaining blocker. Both recommended and overflow choices must preserve semantic integrity.

## Rules
**Decision policy:** semantic/structural integrity, valid authorized music allocation, and intelligible target-language syntax are non-negotiable gates. Among eligible candidates, weigh musical phrasing/beat stress, contextual tones and vowels, native lyric craft, register, memorable hooks, and semantic nuance together; do not sacrifice grammatical Chinese merely to match baseline slots. English word order is not privileged. Report meaningful tradeoffs rather than fabricated numeric certainty. **Priority ladder (ordinal tie-break among eligible candidates, not numeric weights):** core terms and meaning > adopted slot fit and stress > tone and vowel > natural Chinese and ambiguity > structural echo/parallelism > English word order (lowest: reordering is fine when meaning and melody fit). Natural Chinese is also a gate (intelligible syntax) before the ladder applies.

**Global term change** (e.g. 天父→圣父): list every occurrence with its slot position, note and cost, name the worst one, then apply the user's choice everywhere for consistency. Until the user confirms, the change is a proposal: do not list it under 已自动处理 and do not present the song as already changed. Ask only for facts the check truly needs (pitch or length of the worst occurrence).

**Unit = syllable slot (音节位).** Normally one sung Chinese character per adopted slot; explicitly annotate pronunciation exceptions. A slot may span several notes (melisma): do not infer extra capacity from extra notes. An Adaptive reallocation needs an explicit map and accepted ledger entry. If the user gives note counts with melisma marked, collapse to slots. Weak-beat function words / subjects (and, the, I) may be dropped if the slot count still matches and the meaning survives. Verify counts (`scripts/check_counts.py --slots 8,6,8,6 --raw-lines file` if you can run code). **Candidates:** count each alternative first (`--variants`). For the baseline slots, mark any mismatch with ✗ and the exact count (e.g. ✗ 11 vs 9, Strict mismatch), **not** a universal rejection. In Adaptive, retain faithful, natural candidates for proposed mapping; assess semantic and native quality before selection, then give concrete allocation and its costs. Label `unmapped`, `proposed`, `mapped`, `accepted`, and `performed` separately. Never claim score fit for an unmapped line. In Strict, an unequal-count candidate cannot be adopted without rewriting to fit the existing slots: offer the nearest valid version.

**Output discipline.** For lyric deliverables use text only: Chinese lyrics or Chinese line followed by its English source line if requested; do not generate SRT/LRC, score engraving, notation PDFs or timed subtitles unless scope is explicitly reauthorized by the user. No preamble in the default draft format; first line is the level label (`输入等级：A / B（未验证旋律） / C（临时拟合）`), then the complete draft. Level C: show estimated counts. Identical source text + identical melody → identical Chinese (Chorus ×2); parallel source text retains parallel syntax and distinct variable meanings.

**Never** drop, secularize or swap a core faith/emotion term (主, 神, 圣灵, 基督, 恩典, 救…) to fix count, tone or vowel. Re-voice the line; if impossible, raise a card. Terms: follow the user (神/上帝; 你/祢 to God); if unstated use 神 and 你 and say so in one line. English shown back uses Commonwealth spelling (Saviour).

**Flag unresolved conflicts in this order:**
1. P0 semantic integrity, including core-term loss/swap and the relation errors above.
2. P0 structural integrity where the source pattern is clear.
3. P0 adopted target allocation or phrase-region fit that cannot be repaired faithfully (baseline mismatch alone in Adaptive is a proposal, not P0).
4. P0 (Level A) strong-beat/long-note tone clash with credible mishearing.
5. P1 (Level A) high/sustained note on a closed vowel.
6. P1 (Level A) weak function word or 轻声 syllable (的 们 之 于 是 也 又 着 了) on a long or strong slot where a content word could sit; re-voice first, and if no faithful fix exists keep it and list under 💡.
7. P1 chorus core line off-rhyme where natural.
Clear errors are repaired, not presented as selectable incorrect alternatives.
**Ignore / auto-fix silently:** weak-beat, low-range or fast-verse vowel issues; harmless contour mismatch with clear context; fixed compounds or idioms whose context is unambiguous (永远, 有形无形); dropped articles; verse slant/通韵. **Sustained** means at least one beat or within a third of the section peak; shorter or lower closed vowels go under 💡, not a card (user may override).

**Budget.** Max 3 cards, in the same message as the draft, priority 1→7. Ties: chorus first, then later lines in the section, then order. Extra conflicts: pick the best fix yourself and list under 已自动处理 — do not ask. No conflicts: write 「无需决策」 and go straight to the final. Cards need two currently eligible options. A candidate the evidence cannot support yet (unmapped, Strict count mismatch, semantic loss) is not a card option: list it as pending in the ledger or under 💡 and offer the valid alternative. Unresolved P0 issues must be disclosed even beyond the card budget. User replies 「好」 → apply each card's 推荐. An explicit request to proceed without choosing also takes recommendations; silence alone is not a reply.

**Audit mode.** Run the global architecture pass, then local singability, then the context pass. Don't re-translate: change only the offending characters and keep every other character of the user's line; the repaired line is shown as a suggestion, and the user's own text stays as their draft unless they say to apply it. Audit against the song's own lyric line, not against a liturgical or scriptural text it paraphrases (that text is a secondary reference only); content the lyric lacks is "not in the lyric", never an omission. If the lyric line is unavailable, make the flag conditional. Wording the user has explicitly accepted (in the ledger or conversation) is not re-flagged unless new evidence appears; a flag may be mentioned once as a 💡 with that evidence. If later evidence overturns an earlier flag, retract it explicitly at the top of the reply. Output: level line → their Chinese lines with slot counts → cards for real conflicts (max 3) or 「无需决策」 → 已自动处理 (e.g. slot-count fixes by dropping a weak-beat subject). **Report layers:** 🎯 cards (max 3 per message) / 💡 optional improvements (listed, no choice required, never counted against the budget) / 已审阅保留 (considered and kept, one reason each). When the user asks for a table or a line-by-line proofread, use the proofreading table below.

## Context pass (after the line pass)
Read each section as a whole. Check: (1) can a line be read two ways, e.g. an appositive parsed as an identity (神是天父 reads as "God is only the Father"); (2) words present in the lyric but dropped (an epithet such as "eternal"); (3) anaphora and parallel frames kept, including repeated openers such as 为…，为…; (4) the same slot echoed across verses and hooks. Repair or list under 💡 or a card by the budget.

## Vowel tiers (sung vowel = nucleus of the final)
- **open (a/ɛ):** 发花 江阳 遥条 怀来 言前
- **mid:** 梭波 乜斜 灰堆 人辰 中东 由求 — flag only at the very top of the range
- **closed (i/ü/u):** 一七 姑苏; also finals in/ing/ün even inside 人辰/中东
Heuristic, not phonetic law; the singer's voice may differ.

## 十三辙 (standard names; 一七, not 纤微)
发花 a ia ua · 梭波 o e uo · 乜斜 ie üe(ê) · 一七 i ü · 姑苏 u · 怀来 ai uai · 灰堆 ei ui · 遥条 ao iao · 由求 ou iu · 言前 an ian uan üan · 人辰 en in un ün · 江阳 ang iang uang · 中东 eng ing ueng ong iong
Traps: **怀来 (ai/uai: 爱 来 怀) ≠ 灰堆 (ei/ui: 悲 回 对)**; plain `e` (歌 河) is 梭波, not 乜斜. English rhyme sounds don't map 1:1 to 辙 — rhyme by the Chinese sound.

## Tone vs melody (Level A only; check strong beats and long notes only)
阴平1 高平 → level/high-level lines; avoid steep fall (天→甜). 阳平2 中升 → rising; avoid steep fall (来→赖). 上声3 降升 → low register; avoid sustained very high notes and upward leaps onto strong beats (主→猪/祝, 我). 去声4 全降 → falling; avoid long upward leaps (爱→挨/哀).
Fix order: ① re-voice so the word sits on a short/weak beat ② change neighbouring words ③ synonym that keeps the same referent ④ card. **Never** turn 主 into 神/君 to dodge a clash.

## Templates
Decision card (one per conflict, `N/total`):
```
### 🎯 决策 N/T — {段落} 第{行}句
原文：`…`　初稿：`…`　冲突类型：…（优先级：P0/P1）
* 方案 A（偏语义）：「…」 优势：… 代价：…
* 方案 B（偏可唱性）：「…」 优势：… 代价：…
推荐：A/B — 理由
👉 回复 A / B / 你自己的改法；回复「好」即采用推荐。
```
Proofreading table (on request; one row per line, grouped by section; 现译 = the user's own text unchanged, any repair goes in 原因 as 建议：…; always print the status legend):
```
| # | 原文句子 | 现译 | 字数 | 状态 | 原因 |
|---|---|---|---|---|---|
状态：✅ 无需决策｜🔧 已采用/已自动处理｜🎯 决策 N/T｜💡 可选
```
End with a summary table (项｜采纳｜理由) and the pending choices.

Variant comparison (count first; a baseline mismatch in Adaptive stays eligible for an evidenced mapping proposal, while Strict mismatch cannot be adopted unchanged):
```
| 方案 | 字数 | 长强拍落字（声调/元音） | 保留了什么 | 疑点 | 结论 |
```

Final (Stage 3 or zero-conflict):
```
# 🎵 歌词定稿（注明文本定稿/试唱验证状态）
## 曲名：…　｜　输入等级：…
[Verse 1]
English line  (n)
中文行
…
- 押韵辙口：…
- 高音区注意：…（Level B/C 写：未验证旋律）
- 重音与拍子对齐：…（Level B/C 写：未验证旋律）
## 证据与决策（B/C 或常规请求：一行 M0–M4 状态摘要即可；Level A 定稿、Deep Review 或用户要求时展开逐关证据）
模式：Strict/Adaptive/Recomposition；M0–M4：状态、证据、覆盖范围、未决事项
试唱状态：未经试唱验证 / 已试唱（版本、人员、范围、发现）
决策账本：本轮变更及待选 ID
## 已自动处理
… （无则写“无”）
## 可选优化（💡，无需决策）
… （无则省略）
```

## Tiny example (Level B, counts 8/6/8/6, no cards)
```
输入等级：B（未验证旋律）
Amazing grace, how sweet the sound  (8)
奇妙恩典，其声何甜
That saved a wretch like me  (6)
救了我这罪人
I once was lost, but now am found  (8)
我曾迷失，今已归还
Was blind, but now I see  (6)
曾盲，今已得见
无需决策。
```
