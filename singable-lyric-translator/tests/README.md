# Tests and evidence

Run all automatic checks through `python -B -X utf8 tools/build_release.py --check`
from the repository root. To focus on one area while developing, use unittest
discovery, for example:

```sh
python -B -X utf8 -m unittest discover -s tests -p test_rhythm.py -v
```

## What is automatic

The Python suite exercises the actual count/rhythm helpers, checker exit codes,
evidence reporting and release builder. Architecture fixtures validate explicit
hook boundaries and annotated relationships; they do not infer meaning from
arbitrary lyrics. Rule-inventory lint checks that 44 declarations remain in the
instructions, allowing ordinary Markdown formatting changes. It does not prove
an agent follows them.

The build also replays three invented replies through `run_checks.py`: one
AUTO_PASS, one AUTO_FAIL and one MANUAL_REVIEW_REQUIRED. It checks the count
example and the synthetic rhythm map. A CI build exports packages into a clean
temporary directory and confirms the checkout was not modified.

The optional score-renderer CI job installs `tools/score-requirements.txt` and
runs `tools/smoke_scores.py` on invented material. It checks both rendering paths
and a wrong-source rejection; actual browser-PDF rendering and visual QA remain
separate checks. No original user scores or lyrics are uploaded as fixtures.

The public examples and hook passages in `fixtures/` are invented test material,
not completed translations or replies from a real acceptance session. The
runtime rhythm example is illustrative and has no score/audio transcription.

## What still needs a reviewer

`cases.json` contains 44 manual behavioral scenarios, not 44 executed model
evaluations. Record the agent's actual response before reviewing a scenario.
`run_checks.py E17 reply.txt --json` applies only a case's available mechanical
checks; use `-` instead of a filename to read a reply from standard input.

- AUTO_PASS (exit 0): available mechanical checks passed. Manual assertions
  remain `not_tested`; `behavioral_validation` remains `not_tested`.
- AUTO_FAIL (exit 1): an available mechanical check failed.
- MANUAL_REVIEW_REQUIRED (exit 2): no automatic checks were available.

Unmarked Chinese commentary can be counted as an extra lyric line and fail a
count check. This conservative limitation remains visible in the historical
E03/E04 expected failures; the migration does not loosen counting to hide it.
Machine results cannot certify natural Chinese, theological fidelity, score
accuracy, singer comfort or independent acceptance. Keep actual score mapping,
approved user decisions and real singing evidence separate.

Private historical reply files are optional inputs to `--history-dir` and are
not stored in this repository. Their expected 12/2/3 status split is a replay
expectation, not a claim that 17 behavioral tests passed.
