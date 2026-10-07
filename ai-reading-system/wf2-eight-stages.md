# WF2 · 八环节执行

> 在工作台跑完 8 个环节，把"读一本书"变成结构化产出。本文件管**每环节做什么、写到哪个字段、done 前过什么质量门**。
> 允许跳读环节，但每个环节标记 done 前必须过质量门。

## 环节总览

```
1 新书推荐 → 2 粗读 → 3 逐章拆解 → 4 全书逻辑链
→ 5 重点推荐(基于身份画像) → 6 原子笔记 → 7 行动清单 → 8 书评与发布
```

## 写数据的规矩（防数据事故）

1. 改 `data/state.js` 前先备份（复制为 `state.js.bak-<时间戳>`）。
2. 写完立即 `node -e "JSON.parse(require('fs').readFileSync('<path>','utf8').replace(/^[\s\S]*?window\.READING_DATA\s*=\s*/,'').replace(/;\s*$/,''))"` 验证 JSON 合法。
3. 字段名以工作台 `index.html` 各 `stageN()` 渲染函数里的 `data-field` 为准——**写库前先 grep 确认**，不要凭记忆。
4. 内容较多时用临时脚本写库（多行字符串比命令行内联稳）。
5. 每完成 1-2 个环节提醒用户在工作台点「导出」，然后 `node save-export.js <导出.json> --state <工作目录>/data/state.js` 落盘。

## 各环节规范与质量门

| 环节 | 产出（字段） | 质量门（done 前逐条核对） |
|---|---|---|
| 1 新书推荐 | `stages.1.data.reason` 等 | 推荐理由说明"为什么是现在读它"，不写套话 |
| 2 粗读 | `stages.2.data.*`：oneLiner（一句话概括）/ coreQuestion / authorBackground / authorWorks / expertReviews（10条）/ hotReviews（10条）/ concepts / graph / contrast / insights / sixDims / suitableFor / notSuitableFor / recommendLevel | 评价与热评**必须真实有来源，不许编造**，查不到宁可少放；知识图谱 = 书籍节点1个 + 概念节点8-15个 + 关系边，节点命名与环节6原子卡一致 |
| 3 逐章拆解 | `stages.3.data.chapters[]`：title / breakdown（拆解）/ quotes（金句1-3）/ cases（案例1-3）/ pages | 金句**逐字**对照原文；案例不编造；页码当场标（PDF 全文有 `[第 N 页]` 标记可查；EPUB 无页码，如实标注"无页码"，收尾管线会如实报告） |
| 4 全书逻辑链 | `stages.4.data.chain[]` | 逻辑图与章节实际结构一致，不是套路模板 |
| 5 重点推荐 | `stages.5.data.note` + 章节重点标记 | **必须结合用户身份画像**（profile 的 roles/goals/interests），生成针对性阅读建议；画像为空则先引导用户填写 |
| 6 原子笔记 | `stages.6.data.cards[]` ≥10张 | 每卡三分类之一（概念/行动/观点），结构完整：卡片名/一句话总结/要点/来源/**我的思考**（结合用户身份与项目，追问用户）。**ID 命名强制 `YYYYMMDD-NNN`**（创建日 8 位 + 3 位序号，全局唯一、带时间元素），禁止书名缩写码（如 JCSX-001、FCL-003）；跨卡关联用该 id |
| 7 行动清单 | `stages.7.data.actions[]` | 每条有层级（layer）+ verify（怎么验证做了） |
| 8 书评与发布 | `stages.8.data.draft` | 初稿用环节2/3/6成果做素材 + 用户个人理解；发布走工作台五道网关，**发布前必须用户确认** |

## 生成内容的三层调整机制（用户不满意时）

1. **就地改**：工作台所有字段可直接编辑。
2. **带反馈重生成**：把原文素材 + 上一版输出 + 用户反馈一起重新生成（例："更口语化、多结合我的工作场景"）。
3. **风格固化**：用户多次给出同类反馈时，把风格要求记入 `profile.purpose` 或工作目录 `STYLE.md`，后续环节默认遵守。

## 执行纪律

1. 随时中断随时续跑：环节状态存在工作台里，不要求一口气跑完。
2. 诚实性优先于完成度：某章确实没有合适金句/案例，就标"本章无"，不硬凑——收尾网关会逐字打回编造的金句。
3. 版权红线：金句引用 ≤ 合理引用范围，逐章拆解以**转述+解读**为主，不大段复制原文。
4. **随手沉淀（WF5）**：用户在环节执行中口述的想法/质疑/要点，立刻 `note-add.py --kind insight|note|question` 落盘（写完自动进检索索引），并告知用户已记录——不要攒到最后。
5. **画像驱动（WF6）**：环节 5/6/8 生成前，若 `data/profile-learned.json` 存在，先读 `topTopics`（主题权重）与 `cardTypeAdvice`（卡片配比建议），作为"结合身份画像"的量化输入；画像比 interests 原始列表更接近用户真实关注点。
