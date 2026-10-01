# WF4 · 在线工作台发布（可选）

> 想让工作台有个公网链接随时手机看？走三步。不部署也能用——WF1-3 完全本地化，本工作流纯粹是"锦上添花"。

## 三步标准动线

```bash
# 0. 部署前想清楚：口令门占位符要不要换
#    index.html 里 var PASS='AIREAD2026' ← 只改这一处

# 1. 从源码生成发布包（index.html 一律取源码，绝不手工改发布包）
node publish-online.js --data <工作目录> [--out <发布包目录>] [--title "<书名片段>"]

# 2. 真实浏览器回归（7 项，含口令门 7 个场景）
python test-gate.py --site <发布包目录>

# 2.5 版本戳回归（2 项：旧缓存能被重播种 + 戳没变时不白刷访客缓存）
python test-stamp.py --site <发布包目录>

# 3. 部署（静态托管，无后端无账号）
#    把发布包目录整个目录上传即可
```

`--title` 只检查某一本书的环节完整性（默认检查全部，环节不满 8 个会拦截发布）。

**数据更新后必跑第 2.5 步**：只更新 state.js 再发布，老访客浏览器里可能仍显示旧数据（原因见「事故 F」）。`publish-online.js` 每次会打印一个新的 `buildStamp`，前端凭它自动重播种——所以**发布包必须用 `publish-online.js` 生成，不能手工拷 state.js**。

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

根因：工作台是「localStorage 优先」的离线优先设计——`load()` 只要在 localStorage 找到数据就直接用，只在两种情况重读 `data/state.js`：① `version < DATA_VERSION`；② 演示书（"财务自由之路"）缺深化卡/六维等字段。**state.js 单方面更新，这两个条件都不满足**，于是老访客的缓存永远不会刷新。

修法（构建戳机制）：

1. `publish-online.js` 生成发布包时，往 state.js 里注入 `buildStamp`——内容是 `sha1(books + profile)` 前 12 位，**纯内容哈希、不含时间**（内容没变就不打扰访客在线上做的勾选/批注）。
2. `index.html` 启动时比对：`remoteStamp && state.buildStamp !== remoteStamp` → 整体重播种，并 toast 一句「已同步为最新数据」。
3. **本地源码 state.js 不带该字段**（`remoteStamp = ''`）→ 本地行为完全不变，不会误伤本地未导出的编辑。

> **教训：离线优先的缓存策略，必须配一个"服务端内容指纹"。** 只靠版本号（人工 bump）一定会忘；只靠时间戳会误伤访客操作。内容哈希是唯一既自动又不打扰的解法。
>
> 排查手法：用**干净浏览器上下文**打开线上链接数一遍，能立刻区分"服务器数据不对"和"访客本地缓存旧"。`test-stamp.py` 也支持这种模拟——它构造"上次发布的旧缓存"注入 localStorage，验证刷新后能否拿到最新数据。

## 踩坑（test-gate.py）

- **Playwright 的 chromium 常常没下载** → `executable_path` 指本机 Chrome（`C:\Program Files\Google\Chrome\Application\chrome.exe`），不存在则回退 Edge；也可用环境变量 `CHROME_PATH`。
- **`b.new_page()` 每个页都是独立 context，localStorage 不共享** → 必须 `ctx = b.new_context(); pg = ctx.new_page()`，否则「二次访问免输口令」这条永远测不出来。
- **`__gateLock()` 会 `location.reload()`**，紧跟的 `evaluate` 会撞上导航销毁 → `evaluate` 后 `sleep(700ms)` 再 `wait_for_load_state('load')`。
- 本地起 http 服务时，源码判断 `local=true` 不设门，测不出真实行为 → 测试副本里把 local 判断替换成 `var local=false`，模拟线上。
- **版本戳测试（test-stamp.py）必须用 `ctx.add_init_script` 注入 localStorage**，注入才发生在页面脚本执行之前；用 `page.evaluate` 或 `goto` 之后再写就晚了，重播种逻辑早已跑完，测出来永远是"通过"。

## 验收清单

- [ ] `publish-online.js` 自检全绿（JSON / 口令门 / 八环节 / 版权红线），并打印出 `buildStamp`
- [ ] 发布包 `data/state.js` 里确实带 `buildStamp` 字段（手工拷 state.js 会缺，缺了老访客就看不到更新）
- [ ] `test-gate.py` 7 项全过
- [ ] `test-stamp.py` 2 项全过（数据更新场景必跑）
- [ ] 线上打开确认：口令框先出、输错有提示、输对进正文、右下有「锁定」；改动过数据时会出现「已同步为最新数据」提示
- [ ] 版权红线复检：包内无 `data/fulltext/`、state.js 无长段原文
