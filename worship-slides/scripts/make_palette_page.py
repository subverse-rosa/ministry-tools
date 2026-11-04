"""Generate the palette reference page from styles.json (single source of truth)."""
import json, sys, html

styles = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
P = styles["profiles"]

META = {k: (v.get("name_zh", k), v.get("name_en", ""), v.get("use", "")) for k, v in P.items()}
ORDER = styles.get("palette_order", [])
ORDER += [k for k, v in P.items() if k not in ORDER and v.get("service", True)]   # new profiles show up automatically
READ = P["rosa-parchment"]


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def cr(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def swatch(name, hexv, role):
    return (f'<button class="sw" type="button" data-hex="{hexv}" aria-label="复制 {name} {hexv}">'
            f'<span class="chip" style="background:{hexv}"></span>'
            f'<span class="sw-t"><b>{name}</b><span class="role">{role}</span><code>{hexv}</code></span></button>')


def slide(bg, zh, en, acc, badge, badge_style, lines, title="晨光小径"):
    if badge_style == "solid":
        b = f'<span class="badge" style="background:{acc};color:{bg}">{badge}</span>'
    elif badge_style == "soft":
        b = f'<span class="badge" style="background:{en};color:{bg}">{badge}</span>'
    else:
        b = f'<span class="badge" style="border:2px solid {acc};color:{acc}">{badge}</span>'
    ls = "".join(f'<p class="l-zh" style="color:{zh}">{a}</p><p class="l-en" style="color:{en}">{e}</p>' for a, e in lines)
    return (f'<div class="slide" style="background:{bg}"><div class="s-head">{b}'
            f'<span class="s-title" style="color:{acc}">{title}</span></div>'
            f'<div class="s-rule" style="background:{acc}"></div><div class="s-body">{ls}</div></div>')


def cover(top, bottom, zh, acc, text="开始祷告"):
    return (f'<div class="slide cover" style="background:linear-gradient(180deg,{top},{bottom})">'
            f'<span class="c-title" style="color:{zh}">{text}</span></div>')


cards = []
for key in ORDER:
    v = P[key]
    zh_name, en_name, use = META[key]
    vb, cb = v["verse_bg"], v["chorus_bg"]
    bb = v.get("bridge_bg", vb)
    en_c = v.get("en_chorus", v["en"])
    acc_c = v.get("accent_chorus", v["accent"])
    ratios = f'中文 {cr(v["zh"], vb):.1f}:1 · 英文 {cr(v["en"], vb):.1f}:1 · 点缀 {cr(v["accent"], vb):.1f}:1'
    sw = "".join([
        swatch("主歌底", vb, "Verse"), swatch("副歌底", cb, "Chorus"),
        swatch("Bridge 底", bb, "Bridge") if "bridge_bg" in v else "",
        swatch("中文", v["zh"], "歌词"), swatch("英文", v["en"], "歌词"), swatch("点缀", v["accent"], "标题 · 标签"),
    ])
    verse = slide(vb, v["zh"], v["en"], v["accent"], "Verse 1", "outline",
                  [("晨光照亮眼前小路", "Morning light shows us the way"), ("我们并肩同行", "We walk side by side")])
    chorus = slide(cb, v["zh"], en_c, acc_c, "Chorus", "solid",
                   [("携手走过静静山谷", "Hand in hand across the valley"), ("一路听见清晨鸟鸣", "Hear the morning birds along the way")])
    cov = cover(cb, vb, v["zh"], v["accent"])
    cards.append(f'''
<section class="pal" id="{key}">
  <header class="pal-h">
    <div><h2>{zh_name}<span class="en">{en_name}</span></h2><p class="use">{use}</p></div>
    <p class="ratio">{ratios}</p>
  </header>
  <div class="previews">{cov}{verse}{chorus}</div>
  <div class="sws">{sw}</div>
</section>''')

r = READ
reading = (f'<div class="slide read" style="background:#D7C7A9"><div class="r-band" style="background:#2A1012">'
           f'<span style="color:#D6AD5D;font-weight:700">启应</span><span style="color:#F6EAD7">　｜　示例文本</span></div>'
           f'<div class="r-body" style="color:#211F1A"><p>【主席】<sup>1</sup>让我们同心祷告。</p>'
           f'<p>【会众】<sup>2</sup>愿我们以感恩的心彼此服事。</p><p>【齐】<sup>3</sup>愿我们同心前行。</p></div></div>')
read_sw = "".join([swatch("读的底色", "#D7C7A9", "经文 · 启应"), swatch("正文", "#211F1A", "全部读的文字"),
                   swatch("节数", "#5F513D", "上标"), swatch("顶部栏", "#2A1012", "随所选色系的深色")])

page = f'''<title>崇拜投影色系</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Cormorant+Garamond:ital,wght@1,500;1,600&family=IBM+Plex+Mono:wght@400&display=swap">
<style>
/* Layout: a swatch book — one band per colour system, three miniature 16:9 slides + tap-to-copy chips */
:root {{
  --bg: #F3EEE6; --surface: #FBF8F3; --ink: #231E1A; --muted: #6B5F55; --line: #DDD3C6; --gold: #8C6420;
  --f-zh: "Noto Serif SC", "Songti SC", "SimSun", serif;
  --f-en: "Cormorant Garamond", Georgia, serif;
  --f-mono: "IBM Plex Mono", ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #17120F; --surface: #211A16; --ink: #F1E9DD; --muted: #B3A595; --line: #3A2F28; --gold: #D6AD5D; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --bg: #17120F; --surface: #211A16; --ink: #F1E9DD; --muted: #B3A595; --line: #3A2F28; --gold: #D6AD5D; color-scheme: dark }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--f-zh); line-height: 1.6;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding-block: 40px 64px; display: flex; flex-direction: column; gap: 40px; }}
.intro h1 {{ font-size: clamp(28px, 4vw, 40px); margin: 0 0 8px; text-wrap: balance; letter-spacing: .02em; }}
.intro p {{ margin: 0; color: var(--muted); max-width: 65ch; }}
.rules {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 20px; }}
.rule {{ border-top: 2px solid var(--gold); padding-top: 8px; font-size: 14px; }}
.rule b {{ display: block; font-size: 15px; }}
.pal {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 24px; display: flex; flex-direction: column; gap: 18px; }}
.pal-h {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: end; gap: 8px 24px; }}
.pal-h h2 {{ margin: 0; font-size: 24px; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
.pal-h .en {{ font-family: var(--f-en); font-style: italic; font-weight: 500; font-size: 20px; color: var(--muted); }}
.use {{ margin: 2px 0 0; color: var(--muted); font-size: 14px; }}
.ratio {{ margin: 0; font-family: var(--f-mono); font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }}
.previews {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
@media (max-width: 760px) {{ .previews {{ grid-template-columns: 1fr; }} }}
.slide {{ aspect-ratio: 16 / 9; max-width: 100%; border-radius: 3px; overflow: hidden; container-type: inline-size;
  display: flex; flex-direction: column; box-shadow: 0 1px 0 rgba(0,0,0,.08); }}
.s-head {{ display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; padding: 3.5cqw 3.5cqw 1.5cqw; }}
.badge {{ justify-self: start; font-family: var(--f-en); font-weight: 600; font-size: 3.4cqw; padding: .3cqw 1.8cqw; border-radius: 99px; }}
.s-title {{ font-weight: 700; font-size: 4.4cqw; letter-spacing: .05em; }}
.s-rule {{ height: 1px; margin: 0 3.5cqw; opacity: .7; }}
.s-body {{ flex: 1; display: flex; flex-direction: column; justify-content: center; text-align: center; gap: .6cqw; }}
.l-zh {{ margin: 0; font-size: 6.6cqw; line-height: 1.15; }}
.l-en {{ margin: 0 0 1.6cqw; font-family: var(--f-en); font-style: italic; font-weight: 600; font-size: 3.4cqw; }}
.cover {{ align-items: center; justify-content: center; }}
.c-title {{ font-size: 11cqw; letter-spacing: .08em; }}
.read .r-band {{ padding: 2.4cqw 3.5cqw; font-size: 3.8cqw; display: flex; align-items: baseline; flex-wrap: wrap; }}
.read .r-body {{ padding: 3cqw 4cqw; font-size: 4.4cqw; line-height: 1.5; display: flex; flex-direction: column; justify-content: center; flex: 1; }}
.read .r-body p {{ margin: 0 0 1.2cqw; }}
.read sup {{ color: #5F513D; font-size: .6em; }}
.sws {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }}
.sw {{ all: unset; cursor: pointer; display: flex; gap: 10px; align-items: center; padding: 8px; border: 1px solid var(--line); border-radius: 4px; min-width: 0; }}
.sw:hover {{ border-color: var(--gold); }}
.sw:focus-visible {{ outline: 2px solid var(--gold); outline-offset: 2px; }}
.chip {{ width: 34px; height: 34px; border-radius: 3px; flex: none; box-shadow: inset 0 0 0 1px rgba(127,127,127,.35); }}
.sw-t {{ display: flex; flex-direction: column; min-width: 0; font-size: 13px; line-height: 1.3; }}
.sw-t .role {{ color: var(--muted); font-size: 12px; }}
.sw-t code {{ font-family: var(--f-mono); font-size: 12px; }}
.readrow {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 18px; align-items: start; }}
@media (max-width: 760px) {{ .readrow {{ grid-template-columns: 1fr; }} }}
.note {{ font-size: 13px; color: var(--muted); margin: 0; }}
.toast {{ position: fixed; left: 50%; bottom: calc(20px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%);
  background: var(--ink); color: var(--bg); padding: 8px 14px; border-radius: 4px; font-size: 13px; }}
@media (prefers-reduced-motion: no-preference) {{ .sw {{ transition: border-color .15s; }} }}
</style>
<div class="wrap">
  <div class="intro">
    <h1>崇拜投影色系</h1>
    <p>主日崇拜 PPT 的配色规则与七套色系。读的部分固定用羊皮纸，唱的部分和环节封面从下面六套深色里选一套。点色块可复制色号。</p>
    <div class="rules">
      <div class="rule"><b>读 · 羊皮纸</b>宣召、认罪、福音确据、要理问答、确认信仰、读经</div>
      <div class="rule"><b>唱 · 所选色系</b>诗歌、简谱；Verse 最深，Chorus 亮一阶，Bridge 另一色</div>
      <div class="rule"><b>封面 · 所选色系渐层</b>环节封面、空白过场页</div>
      <div class="rule"><b>字体</b>PowerPoint：中文楷体、英文 Cambria。网页预览以思源宋体代替楷体</div>
    </div>
  </div>
  <section class="pal" id="parchment">
    <header class="pal-h"><div><h2>羊皮纸<span class="en">Parchment · 读</span></h2>
      <p class="use">所有读的页面共用，不随色系变化；顶部栏用所选色系的最深色</p></div>
      <p class="ratio">正文 {cr("#211F1A", "#D7C7A9"):.1f}:1 · 节数 {cr("#5F513D", "#D7C7A9"):.1f}:1</p></header>
    <div class="readrow">{reading}<div class="sws">{read_sw}</div></div>
  </section>
{"".join(cards)}
  <p class="note">色号来自 skill 的 styles.json，这一页由它自动生成；色系有变动时重新生成即可。</p>
</div>
<div class="toast" id="toast" role="status" hidden></div>
<script>
const toast = document.getElementById('toast');
let tid;
function show(msg) {{ toast.textContent = msg; toast.hidden = false; clearTimeout(tid); tid = setTimeout(() => toast.hidden = true, 1600); }}
document.querySelectorAll('.sw').forEach(b => b.addEventListener('click', () => {{
  const hex = b.dataset.hex;
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(hex).then(() => show('已复制 ' + hex), () => show(hex));
  }} else {{ show(hex); }}
}}));
</script>
'''
open(out, "w", encoding="utf-8", newline="\n").write(page.rstrip() + "\n")
print("ok", out)
