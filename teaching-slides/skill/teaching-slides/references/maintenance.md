# Source and installation

Canonical runtime source: repository `skill/teaching-slides`. Installed copies are deployment
targets. Private manuscripts, decks, project records and feedback belong under ignored
`projects/`. The author approved public distribution of the bundled source-page examples on 2026-11-03.
Other project files remain local unless separately selected for distribution.

`release.json` records version/distribution status. `tools/release.py` validates the library and
builds a ZIP plus file hashes from source. It installs fresh copies or updates a previously
managed installation with a backup, refusing unmanaged edits. Verify byte equality before
reporting synchronization. Installed edits should be reconciled into source first.

Update the appropriate rule/reference/preset/helper, run focused behavior checks and the
skill validator, inspect relevant artifacts, update version when applicable, regenerate the
gallery, package and install. Commit with configured identity. Respect solo development:
no automatic PR. Public publishing is a separate requested operation.

The initial pilot contains reference previews, not an editable layout engine. It has no
completed newly authored deck, target-room projection or teaching-use validation. Source
content and every export have not been independently approved. Keep unresolved authority
and source defects visible in private project records.
