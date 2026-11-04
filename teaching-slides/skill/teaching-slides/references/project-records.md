# Durable project records

Keep private projects outside the distributed skill. Python 3.10+ helpers use only the standard
library. Inputs: DOCX, PPTX, MD, TXT. Retained copies preserve names in metadata.

```text
python scripts/project.py init <project-directory> --source <manuscript.docx> --source <reference.pptx>
python scripts/project.py check <project-directory>
python scripts/project.py feedback <project-directory> --input <exported-feedback.json>
```

`init` refuses existing projects. It retains hashed sources, extracts segment records, and
creates mapping/decision/feedback/review space. DOCX extraction retains paragraph style and
explicit run properties, including false bold/italic. Inherited styles are preserved in the
retained DOCX, not flattened. PPT extraction retains text, shape IDs, run properties and
geometry, not rendered appearance.

Set `content_authority` and `content_policy` as actual decisions emerge; initial null values
mean unresolved. Source entries link `records/<source-id>.json`; IDs are stable for that snapshot.

Each `slide_map` entry includes `slide_id`, `source_segments`, `treatment`, `relationship`,
`pattern_ids`, and a brief `decision`. Treatment: `verbatim`, `excerpt`, `summary`, `original`.
For original content, explain the addition and use an empty source list when appropriate.
Record substantive omissions in `omissions` with `source_segments` and `reason`. Repeated
overview pages can share sources. Coverage is a mapping count, not semantic-fidelity proof.

Decision entries need `id`, `scope`, `target`, `status`, `wording`, `basis`. Use `confirmed`
only for actual user instructions or already-authorized choices. `supersedes` lists previous
IDs; preserve those records. `reviews` record method, output hash, findings and limits.

Feedback imports validate IDs, scope/context, reject malformed batches, deduplicate identical
IDs and reject changed content under an existing ID. Imports atomically append pending
observations only. Resolve through a recorded decision and targeted edit.
Gallery observations carry a project ID. A mixed export imports only observations for the
target project and reports those skipped for other projects. A batch-level project ID,
when supplied, must also match. Retain the export to import its other observations separately.

`check` verifies contained paths, hashes, extraction records, mapping references and decision
links. Unmapped segments and pending feedback are reported honestly without claiming completion.
Source reconciliation and rendered review still require judgment.

PPT extraction also includes table text, substantive speaker notes and a structural XML hash.
Existing v0.1 snapshots stay unchanged/readable. For v0.2 delivery, authority is a dictionary
with `source_ids` and an actual decision `basis`. See [operations](operations.md) for policy
values, revisions, output/review registration, feedback disposition and delivery checks.
