---
name: teaching-slides
description: Create, adapt or review sermon and lecture slides from manuscripts, outlines and reference decks. Preserve the author's argument, find useful visual relationships, and use an adaptable reference library with scoped feedback. Use for 讲道PPT、课程投影、神学讲座 and teaching-slide design; worship service assembly, congregational readings and song notation belong to worship-slides.
metadata:
  version: 0.2.1
---

# Teaching Slides

Make the author's teaching easier to follow on screen. This skill supplies content and
design decisions, project records and a visual library. Use the host's presentation tools
to author and render the deck. It does not implement a separate PPT renderer.

## Route the operation

- **Review:** inspect the manuscript and actual rendered deck; report material findings
  without editing sources.
- **Create or revise:** read [workflow](references/workflow.md), inventory sources and resolve
  conflicts affecting the output. Work on a copy.
- **Extract/browse references:** read [visual decisions](references/visual-decisions.md).
  `assets/library/index.html` is the offline reference gallery.
- **Learn from use:** read [feedback](references/feedback.md). Save feedback and scope before
  changing a project, series, library entry or default.
- **Maintain/install:** read [maintenance](references/maintenance.md).

Read only relevant references. `$S` means this skill's `scripts` directory; resolve it to an
absolute path. Helpers require Python 3.10+ and its standard library. Rendering is a host capability.

## Content and authorial decisions

Preserve the argument, qualifications, approved wording, emphasis and attribution.
Distinguish exact quotations, excerpts, paraphrases and the speaker's own exposition.
Use the specified Bible translation and verify quotations when presenting them as exact.
Do not silently supply a new translation or attribute unverified wording to an author.

An existing deck may contain later edits than its manuscript. Reconcile meaningful changes
before regeneration. Keep source-to-slide mappings and decisions in a project record:
`python $S/project.py init <project-directory> --source <manuscript.docx> --source <deck.pptx>`.
See [project records](references/project-records.md) for mapping and feedback commands.
For revised sources or outputs, read [revision and delivery operations](references/operations.md).
Compare before replacing anything. Retain versions and review candidate matches; never
automatically transfer confirmed wording or decisions.

## Visual judgment

At outline/storyboard time, actively inspect each major argument for useful comparison,
sequence, causality, foundation, hierarchy, correspondence, evidence or abstraction.
Choose the treatment for its contribution to understanding. A focused text page or a deliberate
pause can be strongest. There is no diagram quota, layout-family quota or requirement to vary every page.

Search [the catalog](assets/library/catalog.json), then inspect relevant previews. Adapt,
combine or invent an expression when content benefits. Support the meaning of arrows, order,
containment and hierarchy with the source. Record important choices briefly, not every step.

Keep pattern, style and series separate: patterns express relationships and spatial form;
styles choose type, color and spacing; series carry course identity, navigation and recurring
content choices. [Parchment burgundy](assets/styles/parchment-burgundy.json) is an optional
starting style. [Assurance of Salvation](assets/series/assurance-of-salvation.json) is a source
series example, not a global default. Sermon/lecture fonts are independent of worship-slides.
The user's request and confirmed project choices take precedence over library examples.

## Review and learning

Check source coverage, relationship accuracy, hierarchy, text fit, punctuation wrapping,
font preservation and exported appearance. Inspect all delivered pages at overview level
and dense/changed pages at full size. Test native editability when requested. Distinguish
XML checks, renderer inspection, native PowerPoint, projection and actual teaching feedback.
A preview does not prove room readability or successful teaching.

Keep confirmed choices in the decision ledger. Feedback has page, project, series or library
scope. A positive comment is feedback, not permission to impose a universal rule. New examples
enter as references; evidence and scope determine reuse. Learning requires deliberate file
updates; model memory is not assumed.

`python $S/library.py build` regenerates the gallery; `python $S/library.py check` validates
records and links. Gallery drafts must be exported/imported to become maintained records;
the browser never modifies an installed skill automatically.

Deliver requested artifacts and material usage limitations. A finished teaching deck can be
imported into worship assembly while preserving its own style.

The gallery supports switching examples and side-by-side comparison. Feedback identifies
its selected example and optional output version. Use `resolve` to record applied, declined
or deferred feedback and its basis; applied items link the resulting registered output.

Before delivery, register the actual PPTX, record content/rendered reviews actually performed,
and run `project.py check <project> --for-delivery --output <id>`. Ordinary check validates
records, not readiness. Delivery checking verifies bindings and recorded reviews; it neither
performs those reviews nor proves semantic/visual quality.
