# worship-slides（主日崇拜 PPT）

Agent Skill（SKILL.md 标准格式），Claude、Codex 等能读 skill、能跑 shell 的 agent 都可以用。

从 [v0.4.2 发布页](https://github.com/subverse-rosa/ministry-tools/releases/tag/worship-slides-v0.4.2)
下载 `worship-slides_v0.4.2.zip`，解压得到一个 `worship-slides/` 文件夹。校验值见同一页的 `SHA256.txt`。

安装：把整个 `worship-slides/` 文件夹放进该 agent 的 skills 目录（路径以各工具文档为准），例如
- Claude Code：`~/.claude/skills/worship-slides/`（或项目里的 `.claude/skills/`）
- Codex：`~/.codex/skills/worship-slides/`
- 其他 agent：把 SKILL.md 当作说明交给它，并让它能访问这个文件夹。

依赖：`pip install -r requirements.txt`；预览用 LibreOffice（可选）。先跑 `python3 scripts/check_env.py`。

内容：
- `SKILL.md` 流程与规则；`references/` 详细规格、设计规则、简谱、经文
- `scripts/` 生成 PPT 的程序；`assets/styles.json` 色系（唯一来源），`assets/palettes.html` 色系对照页
- `examples/handoff/service.yaml` 合成礼拜流程，可直接构建，无需教会模板。
- `examples/handoff/` 从歌词翻译 skill 交接的示例歌（自编），`scripts/selftest.py` 用它自测
- `scripts/check_library.py` 诗歌库检查：哪些 PPT 过期、被手改

## 试跑示例

在本目录运行以下命令，可验证交接流程并生成合成示例。

```sh
python scripts/selftest.py
python scripts/build_service.py examples/handoff/service.yaml demo.pptx
python scripts/check_delivery.py examples/handoff/service.yaml demo.pptx
```
