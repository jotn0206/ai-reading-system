---
name: ai-reading-system
version: 1.8.0
display_name: 一年50本书 · AI阅读执行系统
display_name_en: AI Reading System · 50 Books a Year
description: >
  AI 阅读执行系统——把一本书跑完 8 个环节（新书推荐→粗读→逐章拆解→逻辑链→重点推荐→原子笔记→行动清单→书评），
  全部产出结构化落盘，带金句逐字校验网关与真实页码注入，并生成可发布的书评；可选的在线工作台能把进度挂到公网链接。
  工作台支持沉浸阅读视图与语音朗读（长文本自动分段、当前段落高亮、语速调节、阅读位置记忆），
  移动端有翻页式分页与吸底操作栏。
  首页「留存看板」用间隔重复驱动原子卡复习、用完成漏斗暴露价值流失环节；「行动收件箱」跨全部书汇总待执行行动、今日精选、一键标完成并追踪执行率——解决"读完就忘、行动从不落地"。
  读过的东西能随时翻出来用：八环节产出 + 随读笔记 + Obsidian 卡片统一建本地索引，一条命令检索并导出可复用上下文；
  `gen-dashboard.py` 生成离线看板（进度环 / 八环节漏斗 / 知识结构网络 / 重点分布）；`tts.py` 用神经语音合成 mp3 听书；
  `personalize.py` 从阅读行为学习偏好，反哺选书与环节重点——形成"读→记→查→听→定制"闭环。
  当用户说「拆书」「拆解这本书」「读书笔记」「逐章拆解」「做这本书的阅读计划」「重点章节推荐」「原子笔记」
  「生成书评」「这本书怎么读」「新书入库」「跑阅读系统」「用 AI 一句话拆解一本书」「朗读这本书」「听书」
  「复习」「回顾读过的书」「留存看板」「行动收件箱」「行动执行率」「知识留存」，
  「知识看板」「检索读过的书」「翻以前的笔记」「这条观点出自哪本书」「帮我找相关洞察」「下一本读什么」，
  或提供 epub / PDF / 书名 / 链接希望系统化精读产出，
  或说自己没有这本书的电子书、只能在微信读书里读（走网页版 OCR 抓正文的兜底路线），
  或说「把工作台发布到线上」「在线工作台」「部署阅读工作台」「工作台口令」时使用。
description_zh: >
  把「读一本书」变成结构化产出：8 个环节（新书推荐→粗读→逐章拆解→逻辑链→重点推荐→原子笔记→行动清单→书评）、
  金句逐字校验、真实页码注入、本地可视化工作台，最终生成可发布的书评；可选把工作台发布成带访问口令的公网链接。
  首页留存看板用间隔重复驱动复习、用漏斗暴露流失环节，行动收件箱跨书汇总待办并追踪执行率——让书里的东西真正被记住、被用上。
  没有电子书也能跑：可配合微信读书网页版 OCR 抓正文。适合想系统化精读一本书、并沉淀成读书笔记与内容的人。
  v1.8 新增四大能力：本地知识沉淀与检索（note-add / kb-build / kb-search，跨书与 Obsidian 卡片统一索引）、
  离线可视化看板（gen-dashboard，进度 / 知识结构 / 重点分布一屏看完）、高质量语音朗读（tts.py，神经网络语音合成 mp3，断网降级）、
  个性化闭环（personalize.py，从阅读行为学出主题偏好与薄弱点，反哺选书与环节重点）。
description_en: >
  Turn reading a book into structured output: 8 stages from book intake and overview to chapter-by-chapter
  breakdowns, logic chains, personalized chapter recommendations, Zettelkasten atomic notes, action lists,
  and a final publishable book review. Features verbatim quote verification, real page-number injection,
  and a local visual workbench. Use when the user wants to dissect a book, take structured reading notes,
  or generate a book review. v1.8 adds local knowledge retention with BM25 search across all books and Obsidian
  cards, an offline visual dashboard, high-quality neural TTS audiobook generation, and a personalization engine
  that learns reading preferences to recommend what to read next.
category: education
author: （填写作者署名）
---

# 一年50本书 · AI 阅读执行系统

把"读一本书"变成结构化产出：8 个环节、金句逐字校验、真实页码、可发布书评。本地工作台（index.html）可视化追踪进度，数据存用户自己的目录。

> 包结构：本技能所有文件平铺在根目录，无子目录。脚本、参考文档、工作台模板都在同级。

## 首次使用：初始化工作目录

1. 问用户要一个工作目录（缺省建议 `<工作区>/reading-data/`）。
2. 复制工作台模板：`index.html` 直接放进工作目录根目录；`state.js` 放进 `工作目录/data/state.js`（同目录下 index.html 以 `data/state.js` 相对路径加载它，这两者的相对位置不能变）。
3. 让用户用浏览器打开 `index.html` 确认工作台可用（或起本地 http 服务）。
4. 引导用户完成**身份画像**（工作台「🎯 身份画像」按钮，或直接写 `data/state.js` 的 `profile`）：身份角色 / 目标 / 兴趣主题 / 读这些书为了什么。环节5、6、8 都靠它做个性化。

## 核心流程

```mermaid
flowchart LR
    A[WF1 新书入库] --> B[WF2 八环节执行]
    B --> C[WF3 校验收尾]
    C --> V[WF2.5 知识库沉淀·硬网关]
    V --> D[WF4 单链接发布]
    D --> E[书评发布]
    B -.随手. N[WF5 笔记洞察落盘+检索复用]
    V --> K[WF5 知识索引]
    K --> G[WF6 离线看板]
    D --> T[WF6 语音听书 mp3]
    T & N --> P[WF6 个性化画像→反哺环节5/6/8]
```

## 🚨 唯一口径铁律（P0 · 2026-10-08 定，先把"几套"这件事钉死）

> **事故 I 复盘**：本机一度出现两套阅读系统（工作区分属两个盘、技能又有一个仓库副本、线上还残留旧站点），
> 结果是：改了 A 处 B 处不生效、数据分叉、发布源靠猜。**同一个东西只许有一个位置。**

| 角色 | 唯一位置 | 说明 |
|---|---|---|
| 技能本体（装了就生效） | `~/.workbuddy/skills/ai-reading-system/` | 改动一律先改这里 |
| 技能源码仓库（GitHub / 分发包） | `<你的技能仓库>/ai-reading-system/` | 分发用，由同步脚本回灌 |
| 运行工作台 + 全部阅读数据 | `<工作目录>/`（本机记在环境变量 `READING_DATA`） | 书、八环节、笔记、看板、音频都在这里 |
| 知识沉淀 vault | `$READING_VAULT`（本机记在环境变量） | 卡落 `02 Wiki/12_单书笔记`、`02 Wiki/13_原子笔记` |
| 线上工作台 | **唯一一个链接**，源目录只有 `<工作目录>/` | 禁止为单本书另起平台 |
| 工作区记忆 | 当前工作区的 `.workbuddy/memory/` | 别在两个工作区各写一份 |

**改技能的正确顺序（反了会丢改动）**：

```bash
# 1) 改 ~/.workbuddy/skills/ai-reading-system/（本机安装目录是 canonical 源）
# 2) 回灌仓库（保留仓库的市场版 frontmatter，否则 build 的 frontmatter 闸会失败）
python sync-from-local.py --apply
# 3) 六道闸 + 三包 + 回灌本机
python build.py
```

**工作台 index.html 的两个方向**（互逆，别搞反）：
`sync_template.py` = 运行 → 模板（脱敏，对外分发）；`sync-workbench.py` = 模板 → 运行（把你自己的口令/昵称注入回去）。模板加了新功能后：

```bash
python sync-workbench.py --data <工作目录> --apply   # 先备份运行版再覆盖
```

**包内禁止出现**：真实口令、个人线上链接、本机绝对路径（盘符 + 用户名）。本机真实路径只写在工作区记忆里，不进包。

## 🚨 双轨沉淀铁律（P0 · 2026-10-07 事故 G 后新增，违反即事故）

> **事故 G 复盘**：某书跑完八环节并发到线上工作台，却**漏沉淀进 Obsidian 知识库**，用户在 vault 里搜不到。
> 根因：旧工作流只有 WF1-WF4，**没有一步强制 vault 卡生成**，且曾为单本书另起独立平台/目录，导致"线上有、线下无、还出现两个链接"。
> 教训：**线上发布与线下知识库是同一份成果的两个出口，缺一不可；全库只许一个公网链接。**

1. **线下（知识库三处拆分，硬网关，先于线上）**：每本书 WF2 八环节完成 + WF3 校验通过后，**必须**运行 `sync-vault.py` 把成果按 vault 既定规范**拆成三处**（缺一不可，禁止合并或漏建）：
   - **T1 原文分章** → `01 Raw Sources/20_书籍原文/<书名>/`：全本按"第N章"切分独立 `.md` + `<书名>-原文索引.md`。需传 `--raw <下载的全本txt>`；无原文则主页标「⏳ 待补原文」。
   - **T2 单书笔记 + 深化卡** → `02 Wiki/12_单书笔记/<书名>/`：主页 + 1~8 环节卡 + **逐章 `深化卡·第X章.md`**（取自 stage3 各章 `deepCard`）+ 知识图谱。
   - **T3 原子卡单卡** → `02 Wiki/13_原子笔记(Zettelkasten)/<概念卡|观点卡|行动卡>/<id>.md`：每张原子卡独立成卡、按类型归档，与跨书互织。
   **缺任意一处 vault 卡不许进 WF4 发布**。严禁把多张原子卡合并成一个文件、或漏建原文/深化卡（事故 H）。
2. **线上（单一链接，唯一源目录）**：在线工作台**只允许一个公网链接**，源目录唯一 = `<工作目录>/`。**禁止为任何单本书新建独立平台 / 独立目录 / 独立链接**。新书或任何内容更新，一律走「重建 dist-online（注入 buildStamp）→ 重新部署到同一链接」。
3. **会话收尾核对（每次必做，漏一项不算完成）**：
   - ① vault `12_单书笔记/<书名>/` 卡片齐全（含主页 + 8 环节 + 知识图谱）？
   - ② 线上链接唯一且为最新（buildStamp 已刷新、老访客会自动重播种）？
   - ③ 两侧书目一致——无书只在某一侧（线上有而 vault 无 = bug；vault 有而线上无 = 未发布）？

## WF1 新书入库 → 读 @wf1-add-book.md

用户给 epub / PDF / 粘贴文本 → 转全文 md → `split_fulltext.js` 切章 → `add-book.js` 入库。
**用户没有电子书但微信读书里有**：走 OCR 兜底路线（配套技能 `weread-ocr-capture`），详见 wf1 §1B——这条路线**没有逐页页码**，只能标章级区间，必须如实告知用户。
铁律：书名三处逐字一致；只处理用户自己提供的书。

### WF2 八环节执行 → 读 @wf2-eight-stages.md

逐环节生成内容、写入 `data/state.js`、过质量门后标 done。
关键纪律：评价/热评不许编造；金句逐字对照原文；环节5/6/8 必须结合用户身份画像；每 1-2 环节提醒用户导出落盘。

### WF3 校验收尾 → 读 @wf3-gateways.md

`pipeline.js <书名> --data <工作目录>`：金句逐字校验（硬网关）→ 案例锚点校验（软网关）→ 真实页码注入 → 单书数据提取。先 `--dry-run` 再真跑。

### WF2.5 知识库沉淀（强制硬网关 · 三处拆分）→ 读 @sync-vault.py

八环节成果不能只躺在阅读系统数据里——必须落成 Obsidian 可检索、可双链的知识卡，且**严格按 vault 三处规范拆分**，这是进 WF4 的前置条件。

```bash
# 标准三处沉淀（传入 --raw 才能切原文分章）
python sync-vault.py --data <工作目录> --book "<书名>" --raw "<下载的全本txt>" [--vault $READING_VAULT]
# 全量（逐本补齐 / 定期重跑保持双轨一致）
python sync-vault.py --data <工作目录> --all
```

脚本从 `data/state.js` 抽每本书八环节数据，自动完成三处：

| 处 | 目标目录 | 产物 |
|---|---|---|
| T1 原文分章 | `01 Raw Sources/20_书籍原文/<书名>/` | 每章一个 `.md`（frontmatter + 结论先行 + 回链主页/拆解/索引）+ `<书名>-原文索引.md` 目录表 |
| T2 单书笔记+深化卡 | `02 Wiki/12_单书笔记/<书名>/` | 主页 + 1~8 环节卡 + **逐章 `深化卡·第X章.md`**（六维拆解表/金句/案例/关联原子卡）+ 知识图谱 |
| T3 原子卡单卡 | `02 Wiki/13_原子笔记(Zettelkasten)/<类型>/` | 每张原子卡独立文件（概念卡/观点卡/行动卡分目录），frontmatter + 要点 + 展开 + 我的思考 + 双向链接 |

格式对齐《财务自由之路》等既有卡（frontmatter + 结论先行 + 双链 + 常见误区栏）。

纪律：
- 只在 WF3 校验通过后运行；环节缺失的阶段卡如实标「⏳ 待执行（WF2 进行中）」，不编造。
- `--raw` 指向下载的全本原文 txt（下载时把本地路径记进 `stage1.data.rawFile`，脚本会自动取）；缺失则 T1 降级为「⏳ 待补原文」占位，不报错。
- vault 路径固定 `$READING_VAULT`（环境变量，本机值见工作区记忆）；改路径须同步改脚本默认值与本文。
- 严禁在 T2 把多张原子卡合并进一个文件、或在 T3 漏建单卡——原子卡必须同时出现在 `12_单书笔记`（概览）与 `13_原子笔记`（独立卡）两处（事故 H）。

### WF4 在线工作台发布（单链接 · 唯一源目录）→ 读 @wf4-online-workbench.md

**单链接铁律**：全库只维护**一个**公网链接，源目录唯一 `<工作目录>/`。任何书（含新书）都并入这一个工作台，**绝不为单本书另起平台 / 独立目录 / 独立链接**（事故 G 正由此而起）。部署步骤同下；dist-online 每次重建即刷新 `buildStamp`，老访客自动重播种。

```bash
# 0. 部署前想清楚：口令门占位符要不要换（index.html 里 var PASS= 只改一处）

# 1. 从源码生成发布包（index.html 一律取源码，绝不手工改发布包）
node publish-online.js --data <工作目录> [--out <发布包目录>] [--title "<书名片段>"]

# 2. 真实浏览器回归（7 项，含口令门 7 个场景）
python test-gate.py --site <发布包目录>

# 2.5 版本戳回归（2 项：旧缓存能被重播种 + 戳没变时不白刷访客缓存）
python test-stamp.py --site <发布包目录>

# 3. 部署（静态托管，无后端无账号）：把发布包目录整个上传到**唯一**链接
```

`--title` 只检查某一本书的环节完整性（默认检查全部，环节不满 8 个会拦截发布）。

**数据更新后必跑第 2.5 步**：只更新 state.js 再发布，老访客浏览器里可能仍显示旧数据（原因见「事故 F」）。`publish-online.js` 每次会打印一个新的 `buildStamp`，前端凭它自动重播种——所以**发布包必须用 `publish-online.js` 生成，不能手工拷 state.js**。

### WF5 本地知识操作系统（沉淀 → 检索 → 看板）→ 读 @wf5-knowledge-os.md

八环节产出 + 随读随记的笔记/要点/洞察 + vault 卡，统一进一份 BM25 索引，随取随用：

```bash
P=<受管python>   # 脚本全部用受管 Python 跑，见 Resources 顶部说明

# 用户口述想法 → 立刻落盘（写入后自动重建索引）
$P note-add.py --data <dir> --book "书名" --kind insight --text "..." --tags 决策 --stage 3
# 全量建索引（--vault 把 Obsidian 卡一起收进来，跨系统互通）
$P kb-build.py --data <dir> --vault $READING_VAULT
# 检索复用（--md 导出可直接粘贴的写作上下文）
$P kb-search.py --data <dir> "止损" --type card,note
# 离线可视化看板：进度 / 八环节漏斗 / 知识结构网络 / 重点分布 / 行动复习
$P gen-dashboard.py --data <dir> [--open]
```

纪律：用户口述一个想法就 `note-add` 一次，别攒；写作/选题/回答"我之前记过什么"一律先检索再翻文件；每本书收尾后重新生成看板。

### WF6 语音听书 + 个性化闭环 → 读 @wf6-listen-personalize.md

```bash
# 高质量语音：edge-tts 神经网络（在线，缺依赖自动换受管 venv，断网降级 SAPI）
$P tts.py --check                                              # 先体检
$P tts.py --data <dir> --book "书名" --src fulltext --chapters 1-5 --rate "+15%"
$P tts.py --data <dir> --book "书名" --src stage --sid 6       # 听自己的八环节产出（复习）
# 个性化：行为 → 画像 → 反哺环节5/6/8 与选书
$P personalize.py --data <dir>               # 生成画像+报告（每本书收尾后）
$P personalize.py --data <dir> --apply       # 学到的主题并回 profile.interests（每月至多一次，改 state.js 前自动备份）
```

用户问「下一本读什么」「我该怎么安排阅读」→ 先跑 personalize，用 `nextUp`（未读完 × 主题契合）与 `topicGaps`（主题缺口）回答。`--apply` 后提醒用户工作台「导出」同步。

## 发布包红线（publish-online.js 自动卡）

| 检查 | 不通过就 exit 1 |
|---|---|
| state.js 是合法 JSON | 是 |
| 口令门三要素齐全（`#gate` + `data-locked` + `__gateUnlock`） | 是 |
| `index.html` 无 `data/fulltext` 引用 | 是 |
| state.js 内无 ≥500 字连续中文（防书全文内嵌） | 是 |
| 每本检查到的书环节数 = 8 | 是（除 `--title` 指定单本外） |

## 口令门（访问口令）设计

```html
<!-- 默认不显示；只有 html[data-locked] 时才显示 → 解锁只需摘掉该属性 -->
html[data-locked] > body > *:not(#gate){display:none !important}
html[data-locked] #gate{display:flex}
```

- `file://` / `localhost` / `127.0.0.1` 打开时 `__gateOn=false`，**本地自己看不设门**，免得碍自己。
- 解锁只做 `removeAttribute('data-locked')`，`#gate` 显隐交给 CSS 兜底——不依赖后续 JS，稳。
- 忘记口令兜底：网址末尾加 `#<口令>` 回车。
- **静态站口令只防随手翻，不是真鉴权** —— 口令明文在源码里，看得见源码的人就能看见口令。要真鉴权得上带后端的方案。

改口令只动 `var PASS=` 一处，然后重跑上面三步。

## 事故 E：输入口令无法登录（2026-09-27 复盘）

现象：口令输对了点「进入」没反应；右下「锁定」点了也没用；只有点按钮（内联 onclick）偶尔能进。

根因两处叠加：

1. **口令门当初是手工塞进发布包 `dist-online/index.html` 的，源码根本没有。** 手工改发布包不可继承——下次从源码重建，改动全丢。
2. **head 内的 script 直接摸 body 才存在的 `#gate-input`**，`addEventListener` 抛 TypeError → **回车提交整段失效**；同一 script 块里后面的 `__gateLock` 也没定义（右下锁定按钮同坏），只有内联 onclick 侥幸可用。

正确做法：口令门正式写进源码 → 事件绑定全部进 `DOMContentLoaded` → 每次发布从源码重建发布包。

> **教训：凡发布包里的手工改动，必须回灌进源码，否则下次重建就丢。**

## 事故 F：线上数据更新了，访客还看旧数据（2026-10-01 复盘）

现象：线上 state.js 已经是 8 本书，用干净浏览器打开确实是 8 本；但**已经访问过的访客刷新后仍只看到 7 本**，新入库的那本怎么都不出现。

根因：工作台是「localStorage 优先」的离线优先设计——`load()` 只要在 localStorage 找到数据就直接用，只在两种情况重读 `data/state.js`：① `version < DATA_VERSION`；② 某本书缺深化卡/六维等字段。**state.js 单方面更新，这两个条件都不满足**，于是老访客的缓存永远不会刷新。

修法（构建戳机制）：

1. `publish-online.js` 生成发布包时，往 state.js 里注入 `buildStamp`——内容是 `sha1(books + profile)` 前 12 位，**纯内容哈希、不含时间**（内容没变就不打扰访客在线上做的勾选/批注）。
2. `index.html` 启动时比对：`remoteStamp && state.buildStamp !== remoteStamp` → 整体重播种，并 toast 一句「已同步为最新数据」。
3. **本地源码 state.js 不带该字段**（`remoteStamp = ''`）→ 本地行为完全不变，不会误伤本地未导出的编辑。

> **教训：离线优先的缓存策略，必须配一个"服务端内容指纹"。** 只靠版本号（人工 bump）一定会忘；只靠时间戳会误伤访客操作。内容哈希是唯一既自动又不打扰的解法。
>
> 排查手法：用**干净浏览器上下文**打开线上链接数一遍，能立刻区分"服务器数据不对"和"访客本地缓存旧"。`test-stamp.py` 也支持这种模拟——它构造"上次发布的旧缓存"注入 localStorage，验证刷新后能否拿到最新数据。

## 事故 G：八环节完成却漏沉淀进知识库，且出现两个链接（2026-10-07 复盘）

现象：用户问"知识库里怎么没有《韭菜修行记》"，才发现这本书跑完八环节、发到了线上工作台，却**在 Obsidian vault 里搜不到**；且因为中途为它另起过独立平台/目录，给用户造成"会不会有两个链接、更乱"的困扰。

根因两层：

1. **工作流缺一步**：旧 SKILL 只有 WF1-WF4，**没有强制 vault 卡生成的环节**，执行时只把书落到了阅读系统数据目录（`reading-data/`），没按用户 vault 的"单书笔记卡片体系"建卡。这直接违反用户铁律"每完成实质工作必须沉淀进 vault"。
2. **曾为单本书另起平台**：本次会话早期把韭菜塞进独立的 `dwjotn/reading-data/`（与既有主系统 `jotnbook/reading-system/` 并存），虽然最终合并回单一链接，但过程暴露了"多源/多链接"的脆弱性。

修法（已落地）：

1. **新增 P0 双轨沉淀铁律 + WF2.5 知识库沉淀**：八环节完成 + WF3 校验 → 必须 `sync-vault.py` 落成 vault 卡 → 才许 WF4 发布。vault 卡缺失 = 流程未完，不允许"线上有、线下无"。
2. **单链接铁律**：全库只维护一个公网链接，源目录唯一 `<工作目录>/`；禁止为单本书另起平台/目录/链接。旧 `jotnbook/reading-system/` 副本已归档退役，不再作为发布源。
3. **会话收尾三核对**：vault 卡齐全？线上唯一且最新？两侧书目一致？
4. **可复用脚本**：`sync-vault.py` 从 `state.js` 一键生成 10 张 vault 卡，任何书都可批量补齐，避免再漏。

> **教训：线上发布与线下知识库是同一份成果的两个出口，缺一不可；多源多链接必然失同步。把"沉淀进 vault"写成工作流的硬网关，而不是靠人记得。**

## 事故 H：vault 沉淀只生成合并卡，三处规范漏拆（2026-10-07 复盘）

现象：用户发现《韭菜修行记》跑完八环节、发到线上、也"有"了 vault 卡，**但**——① `01 Raw Sources/20_书籍原文/` 下完全没有分章节原文；② `13_原子笔记(Zettelkasten)/` 下没有独立原子卡（12 张全塞在一个合并文件里）；③ `12_单书笔记/韭菜修行记/` 下没有 `深化卡·第X章.md`。对比《财务自由之路》的正确范本，三处该拆的都没拆。

根因：`sync-vault.py` v1 只把 `state.js` 的八环节**合并成单书笔记下的 10 个文件**，根本没有实现 vault 的三处拆分约定：
1. **T1 原文分章漏建**——v1 只读 `state.js`（其中 `stage1.chapters` 只有 12 个章标题、不含正文），从不去切下载的全本 txt，所以 `01 Raw Sources/20_书籍原文/<书名>/` 整目录缺失。
2. **T3 原子卡未单建**——v1 把 12 张卡合并进 `6·核心卡片（12张原子笔记）.md`，没按类型拆成 `13_原子笔记/<类型>/<id>.md` 独立卡。
3. **T2 深化卡漏抽**——深化内容其实藏在 `stage3.chapters[].deepCard`，v1 只生成合并的 `3·逐章拆解.md`，没把 `deepCard` 抽成独立的 `深化卡·第X章.md`。

修法（已落地，v2 脚本）：
1. **`sync-vault.py` 重写为三处拆分**：`--raw` 切全本原文 → T1；抽 `stage3.deepCard` → T2 逐章深化卡；按 `cardType` 拆 `stage6.cards` → T3 独立原子卡；主页自动补「精读原文/深化卡片/原子笔记分类」三处回链。
2. **下载即登记原文路径**：`download` / WF1 入库时把本地 txt 路径写进 `stage1.data.rawFile`，脚本自动取用，无需每次手传 `--raw`。
3. **验收清单加三处核对**（见下）：原文分章目录存在？原子卡在 `13_原子笔记` 按类型独立成卡？深化卡在 `12_单书笔记` 独立成卡？

> **原子卡 ID 约定（2026-10-07 补订，已执行）**：所有原子卡 ID 一律 `YYYYMMDD-NNN`（创建日 8 位 + 3 位序号，全局唯一、带时间元素），与 `13_原子笔记(Zettelkasten)/` 库内其他书一致。`sync-vault.py` 的 `parse_links` 正则已收紧为 `\d{8}-[0-9]{1,3}`、`build_atomic` 经 `norm_card_id` 校验——**书名缩写码（JCSX-001、FCL-003 等）不再识别也不再生成**。《韭菜修行记》原 12 张 `JCSX-NNN` 卡已于本次迁移为 `20261007-NNN`：真相源 `state.js`/每书 json、单书笔记概览与深化卡、线上 `dist-online` 镜像、12 张独立 T3 卡一并改名，旧 `JCSX-NNN.md` 移入 `.trash/jcsx-dupes/` 待清理。

> **教训：vault 沉淀不是"生成几个 md 就行"，它有三处约定俗成的落点（原文章节 / 单书笔记+深化卡 / 原子卡单卡）。脚本必须逐一对齐范本，绝不能用"合并文件"偷懒替代"拆分落点"。**

## 踩坑（test-gate.py）
- **Playwright 的 chromium 常常没下载** → `executable_path` 指本机 Chrome（`C:\Program Files\Google\Chrome\Application\chrome.exe`），不存在则回退 Edge；也可用环境变量 `CHROME_PATH`。
- **`b.new_page()` 每个页都是独立 context，localStorage 不共享** → 必须 `ctx = b.new_context(); pg = ctx.new_page()`，否则「二次访问免输口令」这条永远测不出来。
- **`__gateLock()` 会 `location.reload()`**，紧跟的 `evaluate` 会撞上导航销毁 → `evaluate` 后 `sleep(700ms)` 再 `wait_for_load_state('load')`。
- 本地起 http 服务时，源码判断 `local=true` 不设门，测不出真实行为 → 测试副本里把 local 判断替换成 `var local=false`，模拟线上。
- **版本戳测试（test-stamp.py）必须用 `ctx.add_init_script` 注入 localStorage**，注入才发生在页面脚本执行之前；用 `page.evaluate` 或 `goto` 之后再写就晚了，重播种逻辑早已跑完，测出来永远是"通过"。

## 验收清单
- [ ] WF2.5 三处沉淀已跑，且**三处齐全**（事故 H 红线）：
  - [ ] **T1**：`01 Raw Sources/20_书籍原文/<书名>/` 存在，含按章切分的 `.md` + `<书名>-原文索引.md`（无 `--raw` 则主页标「⏳ 待补原文」）
  - [ ] **T2**：`02 Wiki/12_单书笔记/<书名>/` 含主页 + 8 环节卡 + 知识图谱 + **逐章 `深化卡·第X章.md`**（从 `stage3.deepCard` 抽）
  - [ ] **T3**：`02 Wiki/13_原子笔记(Zettelkasten)/<类型>/` 下，每张原子卡**独立成卡**（概念卡/观点卡/行动卡分目录），未合并进单文件
- [ ] `12_单书笔记/<书名>/` 主页三处回链正确：精读原文→原文索引、原子笔记分类→13_原子笔记库、深化卡片小节列出
- [ ] `publish-online.js` 自检全绿（JSON / 口令门 / 八环节 / 版权红线），并打印出 `buildStamp`
- [ ] 发布包 `data/state.js` 里确实带 `buildStamp` 字段（手工拷 state.js 会缺，缺了老访客就看不到更新）
- [ ] `test-gate.py` 7 项全过
- [ ] `test-stamp.py` 2 项全过（数据更新场景必跑）
- [ ] 线上打开确认：口令框先出、输错有提示、输对进正文、右下有「锁定」；改动过数据时会出现「已同步为最新数据」提示
- [ ] **全库只有一个公网链接**（源目录 `<工作目录>/`），无单书独立平台/链接
- [ ] 版权红线复检：包内无 `data/fulltext/`、state.js 无长段原文
- [ ] **WF5**：本次会话用户口述的笔记/洞察已 `note-add` 落盘；`kb-search` 能检索到；`dashboard.html` 已重新生成且数字与 state.js 一致
- [ ] **WF6**：合成的 mp3 先 `--limit 3` 试听确认音质；`personalize` 已跑且报告数字合理；`--apply` 后 state.js JSON 校验通过、无重复兴趣词

## 用户体验约定
- 对话驱动：用户说意图（"帮我拆《思考，快与慢》"），agent 跑命令、生成内容、写数据，用户在工作台看结果、做勾选和批注。
- 内容不满意时：就地改 / 带反馈重生成 / 固化风格偏好，三层机制见 wf2。
- 版权红线：系统不分发书籍内容；金句引用限于合理范围；拆解以转述+解读为主。

## 留存：让书里的东西记得住、用得上（v1.6 / v1.7）

只写不读是读书系统最大的隐性失败——跑完 8 环节就进仓库，两周后归零。工作台首页提供两个闭环入口（`migrateRetain()` 运行时自动补字段，老数据打开即迁移）：

- **📊 留存看板**：① 完成漏斗——8 环节逐环 `done/总数` 与完成率，红区标出真正产生价值却最易流失的环节（原子笔记 / 行动清单 / 书评发布）；② 复习队列——原子卡按 Leitner 间隔（1/2/4/7/15/30 天）自动排期，「✓ 已复习」按记忆强度推进并留 `history`。
- **✅ 行动收件箱**：跨全部书汇总未完成行动，按 `due` 排期取今日精选 3 条，首页一键「✓ 执行」；逾期红标、剩余天数徽标。行动字段 `due`（默认 +14 天）/ `effort`（2min/15min/habit）/ `doneAt`（执行时间戳，作为执行真相源，`done` 由它派生，杜绝双源不一致）。

**给使用者的建议节奏**：每周固定清一次复习队列（当天到期卡）+ 每天清 3 条行动精选；把执行率当北极星，而不是"读了多少本"。

## Resources

> **运行说明**：所有 Python 脚本统一用受管 Python 跑：`<受管Python>`；其中 `tts.py` 需要 edge-tts（已装于受管 venv `<受管venv>`，脚本会自动换解释器重跑）。`lib_reading.py` 是共享库（state.js 读写/环节文本抽取/切块/笔记读写），被其余脚本 import，勿单独运行。

- `add-book.js` — 书目入库（--state 指定数据文件）
- `epub2fulltext.py` — EPUB → 全文 md
- `pdf2fulltext.py` — PDF → 全文 md（书签驱动切章 + 真实页码标记）
- `split_fulltext.js` — 全文切章
- 没有电子书时：配套技能 `weread-ocr-capture` 抓微信读书网页版正文（截图 + OCR；无逐页页码）
- `pipeline.js` — 校验+页码+提取 一键收尾（--data 指定工作目录）
- `save-export.js` — 工作台导出 JSON 回填 state.js
- `publish-online.js` — 从源码生成在线工作台发布包（--data/--out/--title，带版权红线自检 + 注入 buildStamp 内容指纹）
- `sync-vault.py` — **三处沉淀（WF2.5 硬网关）**：从 `data/state.js` 一键把每本书拆成三处 Obsidian 卡片——T1 原文分章(`01 Raw Sources/20_书籍原文/<书名>/`)、T2 单书笔记+深化卡(`02 Wiki/12_单书笔记/<书名>/`)、T3 原子卡单卡(`02 Wiki/13_原子笔记(Zettelkasten)/<类型>/`)。用法：`--data <工作目录> --book "<书名>" --raw "<全本txt>"`（或 `--all` 全量；`--vault` 默认 `$READING_VAULT`（环境变量，本机值见工作区记忆））。`--raw` 缺失则 T1 降级为「⏳ 待补原文」。
- `note-add.py` — **笔记/要点/洞察落盘（WF5）**：追加到 `data/notes/<书名>.jsonl`（id 自动 `YYYYMMDD-NNN`），写完自动重建索引；`--list/--q/--del` 管理，`--file/--stdin` 批量导入
- `kb-build.py` — **本地知识索引（WF5）**：state.js 八环节 + notes + vault 卡（`--vault`，`--include-raw` 收原文）统一建 BM25 索引 → `data/kb/kb-index.json`
- `kb-search.py` — **知识检索复用（WF5）**：BM25（标题加权、中文 bigram、零依赖），`--type/--book/--stage` 过滤，`--md` 导出写作上下文，`--recent` 看最新
- `gen-dashboard.py` — **离线可视化看板（WF5）**：单文件 HTML → `data/kb/dashboard.html`（KPI/年度环/八环节漏斗/书目矩阵/知识结构网络/标签与卡片分布/行动复习），无 CDN 依赖
- `tts.py` — **高质量语音朗读（WF6）**：edge-tts 神经网络 mp3（自动换受管 venv、断网降级 SAPI）；`--src fulltext|stage|text`，分块合成 + manifest 续跑 + 朗读稿 + m3u + `--merge` ffmpeg 合并整本；`--check` 体检、`--list-voices` 查语音
- `personalize.py` — **个性化画像（WF6）**：从完成深度/复习/行动执行/思考文本学习主题权重与健康度 → `data/profile-learned.json`；给 `nextUp`（下一本）、`focusChapters`（重点定制）、`topicGaps`；`--apply` 把主题并回 `profile.interests`（自动备份 state.js）
- `test-gate.py` — 口令门真实浏览器 7 项回归
- `test-stamp.py` — 发布版本戳 2 项回归（旧缓存重播种 / 戳一致不白刷）
- `test-mobile.py` — 移动端双视口 35 项回归（含翻页式分页：无纵向滚动 / 页数 / 翻页 / 末页禁用 / 桌面零分页）
- `test-reader.py` — 阅读体验 30 项回归（TTS 分段/跳段/语速/高亮、阅读视图进度/字号/位置记忆、环节8流程卡、吸底操作栏）
- `gen-ledger.py` — 从 `data/state.js` 生成「1年50本进度台账」Markdown（数字全脚本统计，含待续清单 + 数据质量自检）。在**工作台根目录**下运行，路径全走环境变量：`READING_ROOT`（工作台根，默认当前目录）/ `LEDGER_OUT`（台账输出，默认写在工作台根）/ `VAULT_NOTE_DIR`（笔记沉淀目录，用于「已沉淀」标记，留空则该列全为 —）/ `LEDGER_WORKBENCH`（台账头部的在线工作台链接，留空则不写）/ `TARGET`（年度目标，默认 50）
- `index.html` + `state.js` — 工作台模板（复制即用；PASS 是占位口令，部署前改一处）
- @wf1-add-book.md — 新书入库详解
- @wf2-eight-stages.md — 八环节生成规范与质量门
- @wf3-gateways.md — 校验网关、数据维护与事故恢复
- @wf4-online-workbench.md — 在线工作台发布三步、口令门设计与事故 E/F/G 复盘
- @wf5-knowledge-os.md — 本地知识操作系统：笔记落盘、索引、检索复用、离线看板
- @wf6-listen-personalize.md — 语音听书（tts.py）与个性化闭环（personalize.py）
