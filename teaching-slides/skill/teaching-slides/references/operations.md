# Revision, feedback and delivery

Use `scripts/project.py` with Python 3.10+. Keep private projects outside the installed skill.
The helper records decisions/evidence; it never edits a PPTX or performs content/visual review.
Use existing instructions as the basis when applicable. These commands do not require new
approval for an already-authorized edit.

## Retain a revision

```text
python scripts/project.py compare old.docx revised.docx --report changes.md
python scripts/project.py revise <project> --source S01 --file revised.docx
python scripts/project.py revision-decision <project> --revision V0001 --outcome adopt --reason "Use revised draft" --basis "Author revision instruction"
```

Compare the same supported type: DOCX, PPTX, MD or TXT. Reports identify text edits, insertions,
removals, unique-text moves, structure/format changes, speaker-note changes and changed
style/media parts. Native table text is included; note page-number/date/footer placeholders
are excluded. Inherited Word styles remain in source files and appear as changed context parts.

Exact text is an anchor. Equal-length replacement groups are positional candidates. Repeated
or split/merged paragraphs can remain ambiguous. Structure/XML change is not proof of a visual
change; text matching does not establish semantic equivalence. No mapping or wording is
transferred automatically.

`revise` keeps old/new hashed snapshots and reports, creating a pending revision. Resolve with
`adopt` or `keep-existing`. Adopt replaces the old ID in an already-selected
`content_authority.source_ids`; unresolved authority stays unresolved. Review mappings against
the new snapshot explicitly. IDs remain valid only for their source snapshot.

## Register an output and actual reviews

Set `content_authority` to `{"source_ids":["S01"],"basis":"Actual source decision"}`. Select
authoritative teaching sources, not all style references. `content_policy` accepts
`full_content_on_slides`, `summary_with_notes`, or `user_defined` with `content_policy_basis`.
Full coverage needs mapping or explicit justified omission of each active source segment.
Counts do not prove fidelity. Put one `slide_map` entry per output page in output order,
retaining durable project slide IDs for the same intended pages.

```text
python scripts/project.py register-output <project> --file output.pptx --id O1
python scripts/project.py review <project> --output O1 --method content_review --status passed --coverage full --basis "Actual coverage and wording review" --reviewer "Reviewer"
python scripts/project.py review <project> --output O1 --method visual_review --status passed --coverage full --basis "Actual rendered page inspection" --reviewer "Reviewer"
```

Registration copies a PPTX and binds output/source hashes, slide count and the content/map
snapshot. A later manual edit needs new registration. Registration is not review. Reviews
do not automatically transfer to a different output ID, even if it has identical bytes.

Record only reviews actually performed. Choose `issues` or `unverified` and `partial` where
appropriate; describe the actual evidence. Optional methods `native_powerpoint`, `projection`
and `teaching_use` capture different evidence. Identify user reports as reports. Review records
are attestations, not automatic verification of quality.

## Resolve feedback

```text
python scripts/project.py feedback <project> --input observations.json
python scripts/project.py resolve <project> --feedback <id> --outcome applied --output O2 --reason "Changed in O2" --basis "Recorded author feedback"
```

Gallery observations identify the selected example. Optional `output_id` binds to a registered
artifact hash; a conflicting supplied hash is rejected. `delivery_blocking: true` flags a
material issue instead of ordinary advice. Scope/target default to the observation; override
with explicit `--scope`/`--target` when the decision changes its reach.

Outcomes: `applied`, `declined`, `deferred`. Applied requires the resulting registered output;
the helper records disposition without editing slides. The original observation stays intact.
Each disposition appends history and a decision. Later dispositions explicitly supersede
earlier resolution decisions while retaining them. Reimport remains idempotent. Deferred
material feedback still blocks delivery. A library suggestion is not automatically promoted
to a default or a reusable pattern.

## Check delivery separately

```text
python scripts/project.py check <project>
python scripts/project.py check <project> --for-delivery --output O2
```

Ordinary check validates records during incomplete work. Delivery additionally needs resolved
authority/policy, valid output/map snapshots, current source/content bindings, one mapping per
output page, appropriate coverage, disposition of pending revisions, no unresolved material
feedback, and full passed content/visual records for this exact output. Ordinary pending
suggestions are warnings. CLI exits nonzero if not ready.

Results separate `record_valid`, `ready`, blockers and warnings. Ready means bindings and
required records are consistent with reported reviews. It does not independently verify
meaning, rendered quality, theology or quotations. Projection and teaching use are separately
reported and are not universal delivery prerequisites.
