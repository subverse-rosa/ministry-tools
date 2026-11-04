# Migration coverage ledger

The infrastructure migration initially kept the eight v1.7.2 runtime files,
ZIP and checksum unchanged. It consolidated the local master's 55 test
methods into 50, then adds five distribution/isolation regressions: 55 methods
in total. v1.8 then adds 13 notation-input/conversion regressions, bringing the
suite to 68; v1.9 adds 8 projection-handoff regressions (76). The count is an inventory, not an acceptance score.

| Original area | Public location | Treatment |
| --- | --- | --- |
| 17 rhythm regressions in `test_helpers.py` | `test_rhythm.py` (17) | Retained, including rational timing, ties/rests, boundaries, pitch, approval and Strict/Adaptive distinctions. |
| Count cases in `test_helpers.py`, `test_release.py`, `test_evidence_status.py` | `test_counts.py` (11) | Consolidated by behavior: bilingual filtering, one-character and mixed lines, extra lines, UTF-8 pipes, variants, malformed slots and missing files. |
| Checker evidence tests | `test_evidence_status.py` (5) | Retained: no-checks needs review, no false assertion certification, extra lines and nonpass CLI status. |
| Architecture contracts | `test_architecture.py` (5) | Retained with invented hook text: 4+4 segmentation, six parallel hooks, annotated relations and speaker roles. |
| Seven workflow substring tests plus rule-inventory test | `test_contracts.py` (3), `fixtures/rule_inventory.json` | Merged into 44 declaration checks, explicit default/retired-rejection checks and a formatting-tolerance regression. Exact example wording is not a quality test. |
| Nine release/archiver tests | `test_release.py` (14) | Nine retained; five added for published ZIP/source agreement, bad/missing checksum, version progression, output isolation and protected source folders. |
| v1.9 projection handoff | `test_handoff.py` (8) | Invented `handoff-example.mei`: metadata record, performance route with reused chorus, repeats without a route, unknown plist target, unlabelled measures, tied-continuation and missing syllables, status values, approval gate, JSON export refusing existing paths and failing encodings. |
| v1.8 notation helpers | `test_notation.py` (13) | Keys, accidentals, octave conventions, exact/display timing, key-signature carry/reset, tuplets and PDF-map voice/tie invariants. |

The former rule inventory contained **44** entries; its old `45` comment was
incorrect. IDs R01-R44 make the public inventory explicit. Removed brittle
assertions checked the literal wording of three native-Chinese examples.
Corresponding guidance remains unchanged in the runtime; its quality must be
tested with fresh candidate reviews, not equality to those example phrases.

## Fixtures and validation boundaries

- `cases.json`: 44 scenarios retained, E01-E44. The E18/E19 hook passage was
  replaced by invented material preserving the six-line and 4+4 test contracts.
  These scenarios still require fresh agent outputs and human assessment.
- `architecture.json`: annotated roles/relations and invented hook lines. Passing
  means the annotations satisfy the fixture contract, not inferred semantic fidelity.
- `example_level_b.md`: invented bilingual 8/6/8/6 counter example.
- `checker_replays.json`: three synthetic replies covering each checker status.
- `historical_checker_expectations.json`: status metadata only. The original
  17 reply files are optional local inputs and are not published.

The primary CI matrix performs a build with no private history or third-party Python packages.
It does not run the 44 scenarios against a model, transcribe a real score,
certify an installation platform or conduct a singer trial. Source intake and
PDF/numbered-notation workflow instructions are not themselves behaviorally certified.

An additional CI job installs the optional renderers and exercises both paths
with invented material: bilingual staff/numbered SVG/HTML and preserved-PDF
output, plus rejection of a mismatched source hash. A local Windows browser
also produced the bilingual PDF; both example PDFs were visually inspected.
These are small integration examples, not coverage of arbitrary real-world
scores, source-search accuracy or a real singer trial.
