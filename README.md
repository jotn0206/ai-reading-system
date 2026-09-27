# 一年50本书 · AI阅读执行系统

把"读一本书"变成结构化产出的 WorkBuddy 技能：8 个环节（新书推荐 → 粗读 → 逐章拆解 → 全书逻辑链 → 重点推荐 → 原子笔记 → 行动清单 → 书评），金句逐字校验网关、真实页码注入、本地可视化工作台，最终产出可发布的书评。

**核心理念**：产品出工具，不碰内容——书籍由用户自己提供（epub/PDF/粘贴文本），AI 只做加工，版权责任清晰。

## 它解决什么问题

- 读过的书留不下结构化笔记 → 8 环节全流程产出（拆解/图谱/原子卡/行动清单）
- AI 拆书金句爱编造 → 金句逐字回原文校验（硬网关），未命中直接打回
- 页码是拍脑袋 → 从带页码标记的全文自动定位注入真实页码（EPUB 如实标注"无页码"，不编造）
- 读书产出和"我"无关 → 环节5/6/8 基于你的身份画像（角色/目标/兴趣）做个性化推荐与书评

## 安装（三选一）

### 方式 A：WorkBuddy 技能市场（推荐，审核通过后可用）

WorkBuddy 左侧菜单【专家·技能·连接器】→【技能】→ 搜索「一年50本书」→ 点 + 安装。

### 方式 B：导入技能包

1. 下载 [ai-reading-system.skill](dist/ai-reading-system.skill)（zip 格式，直接下载保存）
2. WorkBuddy 对话里说：「帮我安装技能，文件在 <下载路径>/ai-reading-system.skill」按提示导入；或把解压出的 `ai-reading-system/` 文件夹复制到 `~/.workbuddy/skills/`（Windows: `C:\Users\<你>\.workbuddy\skills\`），重启会话生效

### 方式 C：从 GitHub 克隆

```bash
git clone https://github.com/jotn0206/ai-reading-system.git
mkdir -p ~/.workbuddy/skills
cp -r ai-reading-system ~/.workbuddy/skills/
# Windows (Git Bash):
# cp -r ai-reading-system /c/Users/<你>/.workbuddy/skills/
```

重启 WorkBuddy 会话，技能即生效。

## 使用方法

安装后，在 WorkBuddy 对话里直接说意图：

```
帮我拆解《置身事内》，epub 在 D:/books/置身事内.epub
```

```
对《财务自由之路》做重点章节推荐，我的身份画像是房产内容创作者
```

```
这本书的环节3做完了，跑一下校验收尾
```

首次使用 Agent 会引导你：

1. 选一个工作目录（数据全存这里：工作台 + 书籍数据 + 章节笔记）
2. 填身份画像（驱动个性化推荐）
3. 提供书籍文件（epub 最顺，PDF 需带页码提取，或直接粘贴文本）

然后 8 个环节逐个推进：AI 生成草稿 → 你在工作台批注/勾选 → 过质量门标 done → 最后 `pipeline.js` 一键校验 + 页码注入 + 书评成稿。

**对生成内容不满意？** 三层调整：工作台就地改 / 带反馈重新生成（"更口语、多结合我的工作"）/ 沉淀成风格偏好后续默认遵守。

**数据安全**：所有数据存你本地（`data/state.js`），支持导出 JSON 备份；换电脑拷目录即可迁移。

## 打包与发布（维护者）

### 打包 .skill 分发包

```bash
python package_skill.py ai-reading-system dist
# 产出 dist/ai-reading-system.skill（zip 格式）
```

### 提交 WorkBuddy 技能市场

1. 访问 WorkBuddy 开放平台 open.workbuddy.cn，完成开发者注册/入驻
2. 准备材料（已备齐，见 SKILL.md frontmatter）：
   - 名称：一年50本书 · AI阅读执行系统（display_name）
   - 中文简介 description_zh / 英文简介 description_en / 分类 category / 版本 / 作者
   - 图标 512×512 PNG（待补）
3. 上传技能包 ZIP（≤3MB，**两级目录结构**：包内所有文件平铺在 `{skill-name}/` 下一层，不能有子目录嵌套）
4. 提交审核（官方审核约 1-3 个工作日：安全性/稳定性/合规性）
5. 审核通过后在技能列表选择上架，用户即可搜索安装

卡在包解析：对照官方文档 open.workbuddy.cn/docs/skill 检查结构，或邮件 openworkbuddy@tencent.com。

### 版本迭代流程

1. 改 `ai-reading-system/` 根目录下的任意文件（SKILL.md / 脚本 / wf 文档 / 工作台模板）
2. `python build.py` 重新出双包并同步本机技能（或 `python package_skill.py ai-reading-system dist`）
3. 同步一份到 `~/.workbuddy/skills/ai-reading-system/` 本机自用
4. git commit + push；市场版本号 +1 重新提审

## 目录结构

```
ai-reading-system/          # 包内所有文件平铺在这一层，无子目录
├── SKILL.md                # 技能定义（触发词 + 主流程 + 市场元数据）
├── wf1-add-book.md         # 新书入库（epub/PDF/粘贴 → 全文 → 切章 → 入库）
├── wf2-eight-stages.md     # 八环节生成规范、质量门、三层调整机制
├── wf3-gateways.md         # 校验网关原理、数据维护与事故恢复
├── add-book.js             # 书目入库（自动备份、防重名）
├── epub2fulltext.py        # EPUB → 全文 markdown
├── pdf2fulltext.py         # PDF → 全文 markdown（书签切章 + 真实页码标记）
├── split_fulltext.js       # 全文切章
├── pipeline.js             # 校验网关 + 页码注入 + 数据提取
├── save-export.js          # 工作台导出 JSON 回填
├── index.html              # 工作台模板（复制到用户目录即可打开）
└── state.js                # 工作台空数据模板（放用户目录的 data/ 下）
```

> 工作台约定的用户目录结构仍是两层：`index.html` 在根、`data/state.js` 在 `data/` 下——这是运行时约束，不是包结构约束。

## 版权与免责

- 本技能不分发任何书籍内容；书籍文件由使用者自行提供
- 金句引用限于合理引用范围；逐章拆解以转述与解读为主
- 生成的评价/热评要求真实有来源，禁止编造
