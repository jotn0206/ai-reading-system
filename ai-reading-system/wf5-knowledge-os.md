# WF5 · 本地知识操作系统（沉淀 → 索引 → 检索复用 → 看板）

> 目标：读过的每个环节、每条笔记、每个要点与洞察都**持久化、可检索、可复用**。
> 数据分三层，各司其职：
>
> | 层 | 位置 | 角色 |
> |---|---|---|
> | 结构化成果 | `data/state.js` | 八环节正文（真相源，工作台读写） |
> | 流水笔记 | `data/notes/<书名>.jsonl` | 读书时随手产生的笔记/要点/洞察/疑问（只追加，永不覆盖） |
> | 检索索引 | `data/kb/kb-index.json` | 三方内容的统一倒排索引（BM25，零依赖） |

## 1. 笔记与洞察落盘（note-add.py）

**时机（agent 主动提议，别等用户开口）**：
- 环节执行中用户口述了一个想法 → 立刻 `note-add` 落盘（`--kind insight`），并告诉用户已记录；
- 用户说"这条对我有用 / 记一下" → `--kind note`；
- 用户质疑某个观点 → `--kind question`（下本书选题时可回收）；
- 读原文时划出的要点 → `--kind quote`（必须逐字，与金句同一诚信标准）。

```bash
P=<受管python>  # <受管Python>

$P note-add.py --data <dir> --book "思考，快与慢" --kind insight \
   --text "锚定效应在房产报价里的用法" --tags 决策,房产 --stage 3 --chapter "第11章" --source "P118"

echo "用户口述的一句" | $P note-add.py --data <dir> --book "原则" --stdin
$P note-add.py --data <dir> --book "原则" --file ./随想.md      # 批量：按 ## 或空行分段
$P note-add.py --data <dir> --book "原则" --list [--kind insight] [--q 关键词]
$P note-add.py --data <dir> --book "原则" --del 20261008-003
```

笔记写入后**自动重建索引**，立刻可检索。字段：`id(YYYYMMDD-NNN)/ts/kind/stage/chapter/text/tags/links/source/weight`。

## 2. 建索引（kb-build.py）

```bash
$P kb-build.py --data <dir>                    # state.js 八环节 + notes
$P kb-build.py --data <dir> --vault $READING_VAULT  # 连 Obsidian 卡片一起收（推荐：跨系统互通）
$P kb-build.py --data <dir> --stats            # 只看统计
```

覆盖：每环节产出、逐章拆解、每张原子卡、每条行动、重点章、全部笔记、vault 卡（12_单书笔记 + 13_原子笔记；`--include-raw` 再收原文分章，索引会变大，默认关）。

## 3. 检索复用（kb-search.py）

**典型场景**：
- 写作前找素材："上一本投资书里关于止损的卡片有哪些" → 检索结果直接喂给文章草稿；
- 跨书联结："哪些书都讲过复利" → 原子卡互链、选题；
- 回答用户："我之前是不是记过 XX？" → 一秒定位到笔记还是卡片。

```bash
$P kb-search.py --data <dir> "止损" --type card,note        # 只看卡片和笔记
$P kb-search.py --data <dir> "复利" --book 财务自由之路
$P kb-search.py --data <dir> "写公众号选题" --md > ctx.md    # 导出可粘贴的写作上下文
$P kb-search.py --data <dir> --recent 20                    # 最近新增
```

打分 = BM25（标题加权）+ 中文 bigram 分词，无需 jieba。没命中先 `--rebuild`。

**检索纪律（与 vault 同款）**：先检索再读原文，不要为找一条卡整目录翻文件。

## 4. 可视化看板（gen-dashboard.py）

```bash
$P gen-dashboard.py --data <dir> [--target 50] [--open]
# 产物：<dir>/data/kb/dashboard.html —— 离线单文件，双击即开，无 CDN 依赖
```

看板六块：KPI 概览（在读/跑透/年度进度环/原子卡/笔记/行动执行率/今日复习）、年度进度+月度柱、**八环节完成漏斗**（红区=最易流失的价值环节）、每本书 8 格进度矩阵、**知识结构网络**（标签+概念共现力导向图，点节点看相关卡）、重点分布（标签 TOP / 卡片类型 / 行动与复习状态）。

**时机**：每本书收尾后、或用户问"我读到哪了"时生成并提醒打开。

## 验收清单
- [ ] 用户口述的想法都已 `note-add` 落盘（抽查 2 条对得上时间）
- [ ] `kb-index.json` 文档数随笔记增加而增长（note-add 自动重建）
- [ ] `kb-search` 能同时命中 state.js 卡片与 notes 流水（跨层检索通）
- [ ] `dashboard.html` 生成成功且数字与 state.js 一致（抽查漏斗与书目矩阵）
