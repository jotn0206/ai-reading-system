# AI 阅读执行系统 · 架构文档（ARCHITECTURE）

> 本文是「统一入口」文档：说明当前结构、为什么感觉散、目标统一架构，以及两种交付形态如何共用一套代码。
> 对应技能版本 **v1.8.0**。使用说明见 `README.md`，事故与决策见 `复盘-一年50本AI阅读执行系统.md`。

---

## 1. 当前结构（实测）

```
reading-system-skill/            # 【canonical 源码仓库】(git) —— 本仓库
├── ai-reading-system/           # 技能本体，包内必须平铺(无子目录, build.py 硬校验)
│   ├── SKILL.md  index.html  state.js  *.js  *.py  wf*.md  icon.png
├── build.py  push-gh.py  sync-*.py  make_icon.py  sync_template.py
└── dist/                        # 构建产物(.skill / -marketplace.zip / -root.zip)，不入库

reading-system/                  # 【个人运行目录】(不入库) —— 数据 + 已同步工作台
├── index.html  chapters/  chapters_manifest.json
├── data/state.js                # 单一事实源(洋葱姐画像)，8 环节结构化产出
├── data/{audio,fulltext,kb,notes,profile-learned.json}
└── dist-online/                 # 静态发布包(index.html + state.js[buildStamp]) = 「线上站点」

reading-system-ppt/  tools/  bookrank/   # 【相邻工程，零代码耦合】见各自 RELATED.md
```

**关键事实**
- `reading-system-skill/` 是**唯一口径源**；`reading-system/` 是它的数据 + 运行副本（`sync-workbench.py` 注入口令后生成）。
- `dist-online/` 就是"线上站点"——并不存在独立的 `reading-system-site/` 目录（命名错觉）。
- 当前形态：**单用户、本地文件型**，无服务端/数据库/API。`state.js` 只一个 `profile`，`index.html` 只一个前端明文口令。

---

## 2. 为什么感觉散（诊断）

根因不是核心崩了，而是：① 目录错位（site 不存在）；② 数据裂缝（曾混入 `data/state-muxmj4d1u3oj.json` 第二份斌哥画像 + 韭菜修行记第二份表示，已归档至 `reading-system/_legacy/`）；③ 笔记双存储（`state.js` stage6 卡片 + `data/notes/*.jsonl`）；④ 无架构文档/配置中心（仅靠 README + 环境变量）；⑤ 版本漂移（已修复：git HEAD 对齐 v1.8.0）；⑥ 相邻工程同居强化"散"观感。

---

## 3. 目标统一架构

**一句话**：一个 canonical 代码仓库，两种部署形态（本地技能 / 线上托管），清晰模块边界，单一数据接口。

```
ai-reading-system/                        # 技能本体（未来目标分层；当前仍平铺以过 build.py）
├── core/        # 8 环节纯逻辑 WF1-WF8（ingest/skim/chapter/logic/recommend/notes/actions/review），无 IO
├── storage/
│   ├── local_store.py   # 当前: 读写 state.js（单用户）
│   └── db_store.py      # 未来: 读写 DB（多用户）— 同一接口，可切换
├── web/         # 工作台 SPA 单一源 → build.js 产出 dist-online/
├── vault/       # Obsidian 双轨沉淀 sync-vault.py
├── cli/         # 入口: init / run <stage> / build / publish / gen-ledger
├── deploy/      # 线上模式: server/ + Dockerfile + 静态托管配置
├── config/      # config.env.example + seed/（1 本公版示例书, 全 8 环节样例）
└── SKILL.md
```

**模块职责**
- `core`：8 环节纯逻辑，单/多用户共用。
- `storage`：数据层抽象。`local_store` 已就绪；`db_store` 为多用户预留，**同一接口**使「技能版」与「线上版」共用 core。
- `web`：工作台 SPA 单一源，消除"站点不存在"困惑。
- `cli`：所有动作入口，替代散落脚本 + 文档约定。
- `deploy`：线上模式专属，技能模式不需要。

---

## 4. 两种交付形态（同一产品）

| 形态 | 数据层 | 鉴权 | 部署 | 状态 |
|---|---|---|---|---|
| **A. 本地技能**（自托管单用户） | `local_store`→state.js | 前端口令(可选) | 本机/WorkBuddy 预览 | ✅ 当前 |
| **B. 线上托管**（多用户） | `db_store`→DB | 账号+会话 | 静态前端 + API + DB | 🔜 规划中(P3) |

> 用户决策（2026-10-09）：先打磨 **A（技能 1:1 复刻 = 同代码+空状态+1 示例种子书）**，线上多用户(B) 推后。

---

## 5. 分层路线

- **P0 清理**（已完成）：版本对齐 v1.8.0、归档双画像文件、补本架构文档与配置模板、标清相邻工程。
- **P1 代码统一**：重构为 `core/storage/web/vault/cli/deploy`；web 单一源。
- **P2 技能 1:1**（已完成 2026-10-09，v1.8.2）：`init.py` 脚手架 + 公版 seed 示例书（`seed-state.js`，小王子全跑通 + 沉思录进行中）。复刻入口改为 **SKILL.md agent 编排**——用户只对话、agent 跑 init，用户不手动敲代码；`python init.py --seed` 是引擎，还原作者当时形态（系统 + 种子，不带走个人数据）。
- **P3 线上多用户**：`db_store` + 真鉴权 + `deploy/server` + 静态托管。
- **P4 打磨**：多租户配额、onboarding、demo 种子。
