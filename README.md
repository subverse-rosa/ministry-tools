# Ministry Tools

Three independently installable Agent Skills for bilingual church and teaching workflows.

| Skill | Use it for | Install |
| --- | --- | --- |
| [Singable Lyric Translator](singable-lyric-translator/) | Translate lyrics and prepare approved scores | [Download v1.9.0](https://github.com/subverse-rosa/ministry-tools/releases/tag/singable-lyric-translator-v1.9.0) |
| [Teaching Slides](teaching-slides/) | Develop and review sermon or lecture decks | [Download v0.2.1 preview](https://github.com/subverse-rosa/ministry-tools/releases/tag/teaching-slides-v0.2.1) |
| [Worship Slides](worship-slides/) | Build a service deck, including lyrics and numbered notation | [Download v0.4.2](https://github.com/subverse-rosa/ministry-tools/releases/tag/worship-slides-v0.4.2) |

The translator can export a reviewed MEI score and `lyric-handoff/1` events for Worship Slides. Teaching Slides can start from a manuscript or outline, including one prepared with [ROSA](https://github.com/subverse-rosa/rosa-skill). Each skill can also be used on its own.

## Development and releases

Run each skill's commands from its own directory. The root workflows select checks based on the changed paths. Changes to the translator or Worship Slides also exercise the score handoff with an invented example.

Publish separately using a tag such as `teaching-slides-v0.2.1`. Attach the skill-specific installable ZIP and checksum to the matching release. Use the individual release page when linking a download. Each skill's historical releases and tags stay in its original repository.

For Worship Slides, run this from the repository root with the intended release tag and filename.

```sh
git archive --format=zip --prefix=worship-slides/ -o ../worship-slides_vX.Y.Z.zip worship-slides-vX.Y.Z:worship-slides
```

## Source snapshots

- Translator imported from [c55f1d2](https://github.com/subverse-rosa/singable-lyric-translator/commit/c55f1d2fa27cd85910e60c5bcfd3b754acfddfdc).
- Teaching Slides imported from [ba1f92a](https://github.com/subverse-rosa/teaching-slides/commit/ba1f92aa1dbcc279325e09065a4e4d5c16314a01).
- Worship Slides imported from v0.4.0. The public examples use invented material.
