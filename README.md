# Ministry Tools

Three independently installable Agent Skills for bilingual church and teaching workflows.

| Skill | Use it for | Install |
| --- | --- | --- |
| [Singable Lyric Translator](singable-lyric-translator/) | Translate lyrics and prepare approved scores | [Existing releases](https://github.com/subverse-rosa/singable-lyric-translator/releases) |
| [Teaching Slides](teaching-slides/) | Develop and review sermon or lecture decks | [Existing preview release](https://github.com/subverse-rosa/teaching-slides/releases/tag/v0.2.0) |
| [Worship Slides](worship-slides/) | Build a service deck, including lyrics and numbered notation | [Install from the skill directory](worship-slides/) |

The translator can export a reviewed MEI score and `lyric-handoff/1` events for Worship Slides. Teaching Slides can start from a manuscript or outline, including one prepared with [ROSA](https://github.com/subverse-rosa/rosa-skill). Each skill can also be used on its own.

## Development and releases

Run each skill's commands from its own directory. The root workflows select checks based on the changed paths. Changes to the translator or Worship Slides also exercise the score handoff with an invented example.

Publish separately using a tag such as `teaching-slides-v0.2.1`. Attach the skill-specific installable ZIP and checksum to the matching release. Use the individual release page when linking a download. Each skill's historical releases and tags stay in its original repository.

## Source snapshots

- Translator imported from [c55f1d2](https://github.com/subverse-rosa/singable-lyric-translator/commit/c55f1d2fa27cd85910e60c5bcfd3b754acfddfdc).
- Teaching Slides imported from [ba1f92a](https://github.com/subverse-rosa/teaching-slides/commit/ba1f92aa1dbcc279325e09065a4e4d5c16314a01).
- Worship Slides imported from local v0.4.0 commit `18f969d1b6aa54c544d4b8e3c4c4837bb0c1545e`. The public examples use invented material. The original weekly service and song source material are maintained separately.
