# WF1 · 新书入库

> 目标：把一本书变成系统能跑的数据。产出：全文 md（`data/fulltext/<书名>.md`）、章节笔记（`chapters/<书名>/`）、书目进入工作台。
> 铁律：**书名在全文文件、state.js、章节目录三处必须逐字一致**（不带书名号），否则收尾管线找不到文件。

## 工作目录约定

技能使用者的工作目录（首次使用时初始化）：

```
<工作目录>/
├── index.html            # 工作台（从 assets/workbench 复制）
├── data/
│   ├── state.js          # 唯一数据源（从 assets/workbench/data 复制）
│   └── fulltext/<书名>.md # 全文
├── chapters/<书名>/       # 切章产物
└── chapters_manifest.json
```

首次初始化：把技能 `templates/workbench/` 下全部内容复制到用户指定目录即可。让用户用浏览器打开 index.html（或本地 http 服务）确认工作台可用。

## 步骤

### 1. 来源 → 全文 md（按来源三选一）

- **EPUB（首选）**：`python scripts/epub2fulltext.py <book.epub> <书名> <工作目录>/data/fulltext`
- **PDF**：用 PDF 提取工具转全文，**必须保留页码**，统一为行内标记 `[第 N 页]`（收尾管线靠它注入真实页码）。转写后抽查 3-5 段与 PDF 对照，防 OCR 错字——错字会让校验网关误杀金句。
- **粘贴文本/已有 md**：直接落盘为 `data/fulltext/<书名>.md`，确认一级章节用 `## ` 标题。

### 2. 切章

```bash
node scripts/split_fulltext.js "<工作目录>/data/fulltext/<书名>.md" "<书名>" --out "<工作目录>/chapters/<书名>"
```

产出每章一个 md（00-前言 / 01起正文 / 99-附录）+ `chapters_manifest.json` 清单。把章节数和字数报给用户。

### 3. 书目进工作台

```bash
node scripts/add-book.js "<书名>" "<作者>" EPUB "<标签,逗号分隔>" "📖" --state "<工作目录>/data/state.js"
```

（脚本写前自动备份；同名书拒绝重复添加。）

### 4. 验收清单

- [ ] `data/fulltext/<书名>.md` 存在，PDF 来源则页码标记抽查 ≥5 处正确
- [ ] 章节笔记篇数 = manifest 条数
- [ ] 工作台刷新后能看到新书
- [ ] 询问用户是否配置**身份画像**（环节5依赖）：姓名/身份角色/目标/兴趣主题。没配就去工作台「🎯 身份画像」引导填写

完成后进入 WF2 八环节执行。

## 踩坑

- `[第 N 页]` 标记被断行拆开会导致页码定位失败——入库前归一化。
- 版权：只处理**用户自己提供**的书籍文件，系统不分发任何书籍内容。
