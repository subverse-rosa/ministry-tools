# Scripture text

- Version: 圣经新译本 (CNVS) unless the user names another. Source:
  `https://www.biblegateway.com/passage/?search=<书名><章>:<节>&version=CNVS` with whatever web access the agent has.
- If fetching fails or is rate-limited (BibleGateway returns 429 at times), say so and ask the user to paste
  the passage. Do not try other ways around the block and never reconstruct verses from memory.
- Clean the text: drop footnote markers and cross-reference letters, drop section headings, remove the
  spacing that CNVS puts before 神 (`　神` → `神`), keep the version's punctuation.
- Always show the user the text (or the differences from what they pasted) to confirm before building.
- One item per verse; split a verse only where the flow splits it between speakers (`7a` / `7b`).

## Short book names (header references)
创 出 利 民 申 书 士 得 撒上 撒下 王上 王下 代上 代下 拉 尼 斯 伯 诗 箴 传 歌 赛 耶 哀 结 但 何 珥 摩
俄 拿 弥 鸿 哈 番 该 亚 玛 ｜ 太 可 路 约 徒 罗 林前 林后 加 弗 腓 西 帖前 帖后 提前 提后 多 门 来 雅
彼前 彼后 约一 约二 约三 犹 启

## Fixed texts
Use the church’s approved copy of a named confession or catechism. If its wording has not been supplied
or approved in the project, ask the user for the exact text.
